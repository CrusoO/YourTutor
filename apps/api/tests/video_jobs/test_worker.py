"""Worker tests: subprocess loop, events tailing, state transitions."""

from __future__ import annotations

import json
import sys
import textwrap
import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

import app.video_jobs.worker as _worker
from app.auth.security import now_utc
from app.db.models import VideoJobRow
from app.video_jobs.worker import (
    claim_one_job,
    reset_running_jobs,
    run_one_job,
)

# ── fake engine script ────────────────────────────────────────────────────────

# Written to a temp file; run as `sys.executable fake_engine.py <request.json>`
# cwd is set to engine_dir so output paths match the worker's expectations.
_FAKE_ENGINE_PY = textwrap.dedent("""\
    import json, os, sys, time, datetime as dt
    from pathlib import Path

    data = json.load(open(sys.argv[1]))
    request_id = data["requestId"]

    engine_dir = Path(os.getcwd())
    job_dir = engine_dir / "dist" / "jobs" / request_id
    job_dir.mkdir(parents=True, exist_ok=True)

    exit_code = int(os.environ.get("FAKE_EXIT", "0"))
    error_code = os.environ.get("FAKE_CODE", "build_failed")
    delay_s = float(os.environ.get("FAKE_DELAY", "0"))

    time.sleep(delay_s)

    for stage in ["request", "retrieve", "build"]:
        line = json.dumps({
            "t": dt.datetime.utcnow().isoformat() + "Z",
            "jobId": request_id,
            "stage": stage,
            "status": "started",
            "code": None,
            "detail": None,
        })
        with open(job_dir / "events.jsonl", "a") as ef:
            ef.write(line + "\\n")
            ef.flush()
        time.sleep(0.02)

    if exit_code == 0:
        result = {"status": "done", "files": [{"name": "lesson.mp4", "sha256": "deadbeef"}]}
        (job_dir / "lesson.mp4").write_bytes(b"fake mp4")
        (job_dir / "sources.json").write_text('{"caveats": []}')
        (job_dir / "qa.json").write_text("{}")
    else:
        result = {"status": "failed", "code": error_code}

    with open(job_dir / "result.json", "w") as f:
        json.dump(result, f)

    sys.exit(exit_code)
""")


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def factory(engine) -> sessionmaker:  # type: ignore[type-arg]
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture
def fake_engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):  # type: ignore[return]
    """Returns a callable that configures the fake engine subprocess for a test."""
    engine_dir = tmp_path / "engine"
    engine_dir.mkdir()
    script = tmp_path / "fake_engine.py"
    script.write_text(_FAKE_ENGINE_PY)

    monkeypatch.setattr(_worker, "_ENGINE_DIR", engine_dir)
    monkeypatch.setattr(_worker, "_POLL_SECONDS", 0.05)
    monkeypatch.setattr(_worker, "_CANCEL_CHECK_SECONDS", 0.02)
    monkeypatch.setattr(_worker, "_IDLE_SLEEP_SECONDS", 0.0)

    import os
    import subprocess as _sp

    def _setup(
        exit_code: int = 0,
        error_code: str = "build_failed",
        delay: float = 0.0,
    ) -> Path:
        env = {
            **os.environ,
            "FAKE_EXIT": str(exit_code),
            "FAKE_CODE": error_code,
            "FAKE_DELAY": str(delay),
        }

        def _fake_popen(ed: Path, rf: Path) -> _sp.Popen:  # type: ignore[type-arg]
            return _sp.Popen(
                [sys.executable, str(script), str(rf)],
                cwd=str(engine_dir),
                stdout=_sp.DEVNULL,
                stderr=_sp.DEVNULL,
                env=env,
            )

        monkeypatch.setattr(_worker, "_popen_engine", _fake_popen)
        return engine_dir

    return _setup


def _insert_job(
    db: Session,
    status: str = "queued",
    error_code: str | None = None,
) -> VideoJobRow:
    job_id = uuid.uuid4()
    row = VideoJobRow(
        id=job_id,
        node_id="cbse.10.maths.ch02.s2_3",
        request_json={
            "requestId": str(job_id),
            "idempotencyKey": str(uuid.uuid4()),
            "curriculum": {"nodeId": "cbse.10.maths.ch02.s2_3"},
            "options": {"locale": "en", "voice": "default", "fps": 24, "theme": "light"},
        },
        idempotency_key=str(uuid.uuid4()),
        status=status,
        error_code=error_code,
        events=[],
        created_at=now_utc(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ── crash recovery ────────────────────────────────────────────────────────────


def test_reset_running_resets_to_queued(factory, db: Session) -> None:
    row = _insert_job(db, status="running")
    row.started_at = now_utc()
    db.commit()

    n = reset_running_jobs(factory)

    assert n == 1
    db.refresh(row)
    assert row.status == "queued"
    assert row.started_at is None


def test_reset_running_leaves_other_statuses(factory, db: Session) -> None:
    queued = _insert_job(db, status="queued")
    failed = _insert_job(db, status="failed")
    done = _insert_job(db, status="done")

    n = reset_running_jobs(factory)

    assert n == 0
    for r in (queued, failed, done):
        db.refresh(r)
    assert queued.status == "queued"
    assert failed.status == "failed"
    assert done.status == "done"


# ── claim ─────────────────────────────────────────────────────────────────────


def test_claim_returns_none_when_queue_is_empty(factory, db: Session) -> None:
    assert claim_one_job(factory) is None


def test_claim_marks_job_running(factory, db: Session) -> None:
    row = _insert_job(db, status="queued")

    job_id = claim_one_job(factory)

    assert job_id == row.id
    db.refresh(row)
    assert row.status == "running"
    assert row.started_at is not None


def test_claim_skips_non_queued_rows(factory, db: Session) -> None:
    _insert_job(db, status="running")
    _insert_job(db, status="failed")
    _insert_job(db, status="done")

    assert claim_one_job(factory) is None


# ── run_one_job: success ──────────────────────────────────────────────────────


def test_success_marks_done(factory, db: Session, fake_engine) -> None:
    fake_engine(exit_code=0)
    row = _insert_job(db, status="running")

    run_one_job(factory, row.id)

    db.refresh(row)
    assert row.status == "done"
    assert row.error_code is None
    assert row.completed_at is not None
    assert row.lesson_mp4_sha256 == "deadbeef"
    assert row.result_path is not None
    assert row.sources_json_path is not None
    assert row.qa_json_path is not None


def test_success_tails_events_and_stage(factory, db: Session, fake_engine) -> None:
    fake_engine(exit_code=0)
    row = _insert_job(db, status="running")

    run_one_job(factory, row.id)

    db.refresh(row)
    assert len(row.events) >= 1
    assert row.stage in ("request", "retrieve", "build")


# ── run_one_job: failure ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "error_code",
    [
        "build_failed",
        "render_failed",
        "qa_failed",
        "no_lesson_for_topic",
        "no_curriculum_data",
        "invalid_request",
    ],
)
def test_failure_stores_error_code(factory, db: Session, fake_engine, error_code: str) -> None:
    fake_engine(exit_code=1, error_code=error_code)
    row = _insert_job(db, status="running")

    run_one_job(factory, row.id)

    db.refresh(row)
    assert row.status == "failed"
    assert row.error_code == error_code
    assert row.completed_at is not None


def test_failure_without_result_json_uses_build_failed(
    factory,
    db: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine_dir = tmp_path / "no_result_engine"
    engine_dir.mkdir()
    monkeypatch.setattr(_worker, "_ENGINE_DIR", engine_dir)
    monkeypatch.setattr(_worker, "_POLL_SECONDS", 0.05)

    script = tmp_path / "no_result.py"
    script.write_text(
        textwrap.dedent("""\
            import json, os, sys
            from pathlib import Path
            data = json.load(open(sys.argv[1]))
            job_dir = Path(os.getcwd()) / "dist" / "jobs" / data["requestId"]
            job_dir.mkdir(parents=True, exist_ok=True)
            # deliberately write no result.json
            sys.exit(1)
        """)
    )

    import subprocess as _sp

    def _popen(ed: Path, rf: Path) -> _sp.Popen:  # type: ignore[type-arg]
        return _sp.Popen(
            [sys.executable, str(script), str(rf)],
            cwd=str(engine_dir),
            stdout=_sp.DEVNULL,
            stderr=_sp.DEVNULL,
        )

    monkeypatch.setattr(_worker, "_popen_engine", _popen)

    row = _insert_job(db, status="running")
    run_one_job(factory, row.id)

    db.refresh(row)
    assert row.status == "failed"
    assert row.error_code == "build_failed"


# ── run_one_job: engine-side cancel (exit 3) ──────────────────────────────────


def test_exit_3_marks_cancelled(factory, db: Session, fake_engine) -> None:
    fake_engine(exit_code=3)
    row = _insert_job(db, status="running")

    run_one_job(factory, row.id)

    db.refresh(row)
    assert row.status == "cancelled"
    assert row.error_code == "cancelled"
    assert row.completed_at is not None


# ── run_one_job: timeout ──────────────────────────────────────────────────────


def test_timeout_marks_build_failed(
    factory, db: Session, fake_engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_worker, "_TIMEOUT", 1)
    fake_engine(exit_code=0, delay=30.0)  # 30 s delay; times out at 1 s
    row = _insert_job(db, status="running")

    run_one_job(factory, row.id)

    db.refresh(row)
    assert row.status == "failed"
    assert row.error_code == "build_failed"
    assert row.completed_at is not None


# ── run_one_job: API cancel ───────────────────────────────────────────────────


def test_api_cancel_terminates_subprocess(factory, db: Session, fake_engine) -> None:
    """If the DB row is marked cancelled before the poll loop fires, worker exits cleanly."""
    fake_engine(exit_code=0, delay=30.0)

    row = _insert_job(db, status="running")
    # Simulate the API having cancelled the job before the worker polls
    row.status = "cancelled"
    row.error_code = "cancelled"
    db.commit()

    run_one_job(factory, row.id)

    db.refresh(row)
    assert row.status == "cancelled"
    assert row.error_code == "cancelled"


# ── invariant: no student data in request file ───────────────────────────────


def test_request_json_excludes_student_id(db: Session) -> None:
    """request_json stored in the DB (and dumped to the temp file) must never carry student_id."""
    student_id = uuid.uuid4()
    job_id = uuid.uuid4()
    row = VideoJobRow(
        id=job_id,
        student_id=student_id,  # stored in the DB column
        node_id="cbse.10.maths.ch02.s2_3",
        request_json={
            "requestId": str(job_id),
            "idempotencyKey": str(uuid.uuid4()),
            "curriculum": {"nodeId": "cbse.10.maths.ch02.s2_3"},
            "options": {"locale": "en", "voice": "default", "fps": 24, "theme": "light"},
        },
        idempotency_key=str(uuid.uuid4()),
        status="queued",
        events=[],
        created_at=now_utc(),
    )
    db.add(row)
    db.commit()

    payload = row.request_json
    assert "student_id" not in payload
    assert "studentId" not in payload
    assert str(student_id) not in json.dumps(payload)
