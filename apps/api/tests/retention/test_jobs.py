"""The retention jobs: old rows go, recent stay, a dry run changes nothing, paths stay inside."""

from __future__ import annotations

import os
import uuid
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import retention
from app.auth.security import now_utc
from app.config import review_sample_rate, settings
from app.db.models import (
    AuthSessionRow,
    LlmCallRow,
    OtpChallengeRow,
    RateEventRow,
    StudentRow,
    VideoJobRow,
)
from app.retention import run_job
from tests.retention.seed import count, days_ago


@pytest.fixture
def jobs(tmp_path: Path) -> Path:
    folder = tmp_path / "jobs"
    folder.mkdir()
    settings.engine_jobs_dir = str(folder)
    return folder


def _otp(db: Session, age_hours: float) -> None:
    created = now_utc() - timedelta(hours=age_hours)
    db.add(
        OtpChallengeRow(
            id=uuid.uuid4(),
            email="x@example.com",
            code_hash="h",
            ip="1.1.1.1",
            created_at=created,
            expires_at=created + timedelta(minutes=10),
        )
    )


def test_otp_rows_older_than_a_day_go_and_recent_ones_stay(db: Session) -> None:
    _otp(db, 25)
    _otp(db, 23)
    db.commit()
    assert "would delete 1" in run_job(db, "otp", dry_run=True)
    assert count(db, OtpChallengeRow) == 2
    assert "deleted 1" in run_job(db, "otp")
    assert count(db, OtpChallengeRow) == 1
    assert "deleted 0" in run_job(db, "otp")  # idempotent


def test_rate_events_older_than_seven_days(db: Session) -> None:
    for age in (8, 6):
        db.add(RateEventRow(id=uuid.uuid4(), bucket="b", created_at=days_ago(age)))
    db.commit()
    run_job(db, "rate_events", dry_run=True)
    assert count(db, RateEventRow) == 2
    run_job(db, "rate_events")
    assert count(db, RateEventRow) == 1


def test_auth_sessions_expired_more_than_thirty_days_ago(db: Session) -> None:
    for expired_days_ago in (31, 5, -1):  # -1: still valid tomorrow
        db.add(
            AuthSessionRow(
                id=uuid.uuid4(),
                token_hash=uuid.uuid4().hex,
                role="parent",
                expires_at=days_ago(expired_days_ago),
                created_at=days_ago(expired_days_ago + 1),
            )
        )
    db.commit()
    run_job(db, "auth_sessions", dry_run=True)
    assert count(db, AuthSessionRow) == 3
    run_job(db, "auth_sessions")
    assert count(db, AuthSessionRow) == 2


def _llm(db: Session, age_days: float, text: str | None) -> uuid.UUID:
    row = LlmCallRow(
        id=uuid.uuid4(),
        created_at=days_ago(age_days),
        purpose="hint",
        prompt_version="v1",
        band_id="b",
        language="en",
        outcome="llm",
        sampled=text is not None,
        output_text=text,
    )
    db.add(row)
    return row.id


def test_llm_reply_text_is_cleared_after_the_review_window_and_rows_after_ninety_days(
    db: Session,
) -> None:
    fresh = _llm(db, 2, "fresh reply")
    middle = _llm(db, 20, "old reply")
    ancient = _llm(db, 100, "ancient reply")
    db.commit()
    assert "would clear 2" in run_job(db, "llm_calls", dry_run=True)
    assert db.get(LlmCallRow, middle).output_text == "old reply"  # type: ignore[union-attr]
    summary = run_job(db, "llm_calls")
    assert "cleared 2" in summary and "deleted 1" in summary
    db.expire_all()
    assert db.get(LlmCallRow, fresh).output_text == "fresh reply"  # type: ignore[union-attr]
    kept = db.get(LlmCallRow, middle)
    assert kept is not None and kept.output_text is None and kept.purpose == "hint"
    assert db.get(LlmCallRow, ancient) is None


def test_reply_text_is_not_sampled_in_production_unless_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "llm_review_sample_rate", None)
    monkeypatch.setattr(settings, "app_env", "production")
    assert review_sample_rate(settings) == 0.0
    monkeypatch.setattr(settings, "llm_review_sample_rate", 0.25)
    assert review_sample_rate(settings) == 0.25
    monkeypatch.setattr(settings, "llm_review_sample_rate", None)
    monkeypatch.setattr(settings, "app_env", "development")
    assert review_sample_rate(settings) == 1.0


def _job(
    db: Session, status: str, age_days: float, folder: str | None = None, result_path: str = ""
) -> uuid.UUID:
    job_id = uuid.uuid4()
    db.add(
        VideoJobRow(
            id=job_id,
            node_id="n",
            request_json={"requestId": folder} if folder else {},
            idempotency_key=uuid.uuid4().hex,
            status=status,
            result_path=result_path or None,
            created_at=days_ago(age_days + 0.1),
            completed_at=days_ago(age_days) if status in ("done", "failed", "cancelled") else None,
        )
    )
    return job_id


def _folder(jobs: Path, name: str) -> Path:
    path = jobs / name
    path.mkdir()
    (path / "lesson.mp4").write_bytes(b"mp4")
    return path


def test_old_finished_and_failed_jobs_and_their_files_go_and_recent_ones_stay(
    db: Session, jobs: Path
) -> None:
    old_done = _folder(jobs, "olddone")
    old_failed = _folder(jobs, "oldfailed")
    recent = _folder(jobs, "recent")
    queued = _folder(jobs, "queuedrecent")
    a = _job(db, "done", 31, result_path=str(old_done))
    b = _job(db, "failed", 40, folder="oldfailed")
    c = _job(db, "done", 5, result_path=str(recent))
    d = _job(db, "queued", 1, folder="queuedrecent")
    abandoned = _job(db, "queued", 45)
    db.commit()

    assert "would delete 3" in run_job(db, "video_jobs", dry_run=True)
    assert count(db, VideoJobRow) == 5 and old_done.exists()

    summary = run_job(db, "video_jobs")
    assert "deleted 3 job(s), 2 folder(s)" in summary
    db.expire_all()
    assert all(db.get(VideoJobRow, gone) is None for gone in (a, b, abandoned))
    assert all(db.get(VideoJobRow, kept) is not None for kept in (c, d))
    assert not old_done.exists() and not old_failed.exists()
    assert recent.exists() and queued.exists()
    assert "deleted 0 job(s), 0 folder(s)" in run_job(db, "video_jobs")


def test_a_stored_path_outside_the_jobs_directory_is_never_deleted(
    db: Session, jobs: Path, tmp_path: Path
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "precious.txt").write_text("keep")
    sibling = tmp_path / "jobs-sibling"
    sibling.mkdir()
    (sibling / "precious.txt").write_text("keep")
    _job(db, "done", 60, result_path=str(outside))  # name "outside" is not under jobs/
    _job(db, "done", 60, result_path=str(tmp_path / ".."))  # a parent directory
    _job(db, "done", 60, result_path="C:\\data\\..")  # a Windows path ending in ..
    _job(db, "done", 60, result_path=str(jobs.parent))  # the directory above jobs/
    _job(db, "done", 60, folder="../outside")  # request id with a separator
    _job(db, "done", 60, folder="..")
    # a link inside jobs/ pointing out: the link is not followed and the target stays
    link = jobs / "linked"
    try:
        os.symlink(outside, link, target_is_directory=True)
        _job(db, "done", 60, folder="linked")
    except (OSError, NotImplementedError):
        pass
    db.commit()
    run_job(db, "video_jobs")
    assert (outside / "precious.txt").read_text() == "keep"
    assert (sibling / "precious.txt").read_text() == "keep"
    assert jobs.exists() and tmp_path.exists()
    assert count(db, VideoJobRow) == 0  # the rows go; only files under jobs/ are ever touched


def test_purge_guests_is_part_of_all_and_a_dry_run_keeps_the_guest(
    client: TestClient, db: Session, jobs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client.post("/guest/start", json={"curriculum_id": "bhutan", "grade": 9})
    _otp(db, 30)
    db.commit()
    later = now_utc() + timedelta(days=91)
    lines = [run_job(db, name, dry_run=True, now=later) for name in retention.JOBS]
    assert lines[0] == "purge_guests: would delete 1 guest(s)"
    assert count(db, StudentRow) == 1 and count(db, OtpChallengeRow) == 1
    assert [line.split(":")[0] for line in lines] == list(retention.JOBS)
    assert "purge_guests" in retention.JOBS
    lines = [run_job(db, name, now=later) for name in retention.JOBS]
    assert lines[0] == "purge_guests: deleted 1 guest(s)"
    assert count(db, StudentRow) == 0 and count(db, OtpChallengeRow) == 0


class _Keep:
    """A `with` target that hands back the test's session and leaves it open."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def __enter__(self) -> Session:
        return self.db

    def __exit__(self, *_: object) -> None:
        return None


def test_the_command_prints_one_line_per_job_and_exits_zero(
    db: Session, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _otp(db, 30)
    db.commit()

    monkeypatch.setattr(retention, "session_factory", lambda: lambda: _Keep(db))
    assert retention.main(["all", "--dry-run"]) == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == len(retention.JOBS)
    assert "x@example.com" not in "\n".join(out) and "1.1.1.1" not in "\n".join(out)
    assert count(db, OtpChallengeRow) == 1
    assert retention.main(["otp"]) == 0
    assert count(db, OtpChallengeRow) == 0


def test_a_failing_job_does_not_stop_the_others_and_exits_one(
    db: Session, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def boom(*_: object, **__: object) -> int:
        raise RuntimeError("secret detail must not be printed")

    monkeypatch.setattr(retention, "purge_otp", boom)
    monkeypatch.setattr(retention, "session_factory", lambda: lambda: _Keep(db))
    assert retention.main(["all"]) == 1
    out = capsys.readouterr().out
    assert "otp: FAILED" in out and "secret detail" not in out
    assert "video_jobs:" in out  # later jobs still ran
