"""Tests for the video-jobs API (POST, GET, cancel, retry, topics, file serving)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.security import now_utc
from app.db.models import VideoJobRow
from tests.conftest import World, auth_header

# ── helpers ──────────────────────────────────────────────────────────────────

_NODE = "cbse.10.maths.ch02.s2_3"


def _idem() -> str:
    return str(uuid.uuid4())


def _create_job(
    client: TestClient,
    token: str,
    node_id: str = _NODE,
    idem: str | None = None,
) -> tuple[Any, str]:
    key = idem or _idem()
    r = client.post(
        "/video-jobs",
        json={"node_id": node_id, "idempotency_key": key},
        headers=auth_header(token),
    )
    return r, key


def _insert_job(
    db: Session,
    student_id: uuid.UUID,
    status: str = "queued",
    error_code: str | None = None,
) -> VideoJobRow:
    """Insert a VideoJobRow directly, bypassing the API, for status-transition tests."""
    row = VideoJobRow(
        id=uuid.uuid4(),
        student_id=student_id,
        node_id=_NODE,
        request_json={"requestId": str(uuid.uuid4())},
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


# ── POST /video-jobs ──────────────────────────────────────────────────────────


def test_create_returns_202(client: TestClient, world: World) -> None:
    r, _ = _create_job(client, world.student_token)
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["status"] == "queued"
    assert body["node_id"] == _NODE


def test_create_idempotent_same_key_returns_existing(client: TestClient, world: World) -> None:
    key = _idem()
    r1, _ = _create_job(client, world.student_token, idem=key)
    assert r1.status_code == 202
    r2, _ = _create_job(client, world.student_token, idem=key)
    # second call: idempotent, returns the same job with 200
    assert r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]


def test_create_requires_student_token(client: TestClient, world: World) -> None:
    r = client.post(
        "/video-jobs",
        json={"node_id": _NODE, "idempotency_key": _idem()},
        headers=auth_header(world.parent_token),
    )
    assert r.status_code == 403


def test_create_requires_tutoring_consent(client: TestClient, world: World) -> None:
    # Create a student with NO consent.
    no_consent = client.post(
        "/students",
        json={"display_name": "NoConsent", "grade": 9, "board": "bhutan"},
        headers=auth_header(world.parent_token),
    )
    assert no_consent.status_code == 200, no_consent.text
    nc_id = no_consent.json()["id"]
    # Give them a PIN so they can get a student token.
    client.post(
        f"/students/{nc_id}/pin", json={"pin": "5678"}, headers=auth_header(world.parent_token)
    )
    token_r = client.post(f"/students/{nc_id}/pin/verify", json={"pin": "5678"})
    assert token_r.status_code == 200, token_r.text
    nc_token = token_r.json()["access_token"]

    r = client.post(
        "/video-jobs",
        json={"node_id": _NODE, "idempotency_key": _idem()},
        headers=auth_header(nc_token),
    )
    assert r.status_code == 403


def test_create_rejects_unauthenticated(client: TestClient) -> None:
    r = client.post("/video-jobs", json={"node_id": _NODE, "idempotency_key": _idem()})
    assert r.status_code == 401


def test_create_extra_fields_rejected(client: TestClient, world: World) -> None:
    r = client.post(
        "/video-jobs",
        json={"node_id": _NODE, "idempotency_key": _idem(), "student_id": str(uuid.uuid4())},
        headers=auth_header(world.student_token),
    )
    assert r.status_code == 422


# ── GET /video-jobs/{id} ──────────────────────────────────────────────────────


def test_get_returns_job_for_owner(client: TestClient, world: World) -> None:
    r, _ = _create_job(client, world.student_token)
    job_id = r.json()["id"]
    g = client.get(f"/video-jobs/{job_id}", headers=auth_header(world.student_token))
    assert g.status_code == 200
    assert g.json()["id"] == job_id


def test_get_returns_404_for_unknown_id(client: TestClient, world: World) -> None:
    g = client.get(f"/video-jobs/{uuid.uuid4()}", headers=auth_header(world.student_token))
    assert g.status_code == 404


def test_get_returns_403_for_wrong_student(client: TestClient, world: World) -> None:
    r, _ = _create_job(client, world.student_token)
    job_id = r.json()["id"]
    # parent token is not the owning student
    g = client.get(f"/video-jobs/{job_id}", headers=auth_header(world.parent_token))
    assert g.status_code == 403


def test_get_allowed_for_admin(client: TestClient, world: World) -> None:
    r, _ = _create_job(client, world.student_token)
    job_id = r.json()["id"]
    g = client.get(f"/video-jobs/{job_id}", headers=auth_header(world.admin_token))
    assert g.status_code == 200


def test_get_response_has_stage_label(client: TestClient, world: World, db: Session) -> None:
    """A job with a stage set returns a human-readable stage_label."""
    r, _ = _create_job(client, world.student_token)
    job_id = uuid.UUID(r.json()["id"])

    # Simulate worker updating the stage
    row = db.get(VideoJobRow, job_id)
    assert row is not None
    row.stage = "render"
    row.status = "running"
    db.commit()

    g = client.get(f"/video-jobs/{job_id}", headers=auth_header(world.student_token))
    assert g.status_code == 200
    body = g.json()
    assert body["stage"] == "render"
    assert body["stage_label"] == "Rendering video…"


# ── POST /video-jobs/{id}/cancel ──────────────────────────────────────────────


def test_cancel_queued_job(client: TestClient, world: World) -> None:
    r, _ = _create_job(client, world.student_token)
    job_id = r.json()["id"]
    c = client.post(f"/video-jobs/{job_id}/cancel", headers=auth_header(world.student_token))
    assert c.status_code == 200
    assert c.json()["status"] == "cancelled"
    assert c.json()["error_code"] == "cancelled"
    assert c.json()["error_message"] == "Request was cancelled."


def test_cancel_running_job(client: TestClient, world: World, db: Session) -> None:
    row = _insert_job(db, uuid.UUID(world.student_share_id), status="running")
    c = client.post(f"/video-jobs/{row.id}/cancel", headers=auth_header(world.student_token))
    assert c.status_code == 200
    assert c.json()["status"] == "cancelled"


def test_cancel_done_job_returns_409(client: TestClient, world: World, db: Session) -> None:
    row = _insert_job(db, uuid.UUID(world.student_share_id), status="done")
    c = client.post(f"/video-jobs/{row.id}/cancel", headers=auth_header(world.student_token))
    assert c.status_code == 409


def test_cancel_already_cancelled_returns_409(
    client: TestClient, world: World, db: Session
) -> None:
    row = _insert_job(db, uuid.UUID(world.student_share_id), status="cancelled")
    c = client.post(f"/video-jobs/{row.id}/cancel", headers=auth_header(world.student_token))
    assert c.status_code == 409


def test_cancel_wrong_owner_returns_403(client: TestClient, world: World, db: Session) -> None:
    row = _insert_job(db, uuid.UUID(world.student_share_id), status="queued")
    c = client.post(f"/video-jobs/{row.id}/cancel", headers=auth_header(world.parent_token))
    assert c.status_code == 403


# ── POST /video-jobs/{id}/retry ───────────────────────────────────────────────


def test_retry_failed_job_returns_201(client: TestClient, world: World, db: Session) -> None:
    row = _insert_job(
        db, uuid.UUID(world.student_share_id), status="failed", error_code="build_failed"
    )
    r = client.post(f"/video-jobs/{row.id}/retry", headers=auth_header(world.student_token))
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "queued"
    assert body["node_id"] == _NODE
    assert body["id"] != str(row.id)


def test_retry_queued_job_returns_409(client: TestClient, world: World, db: Session) -> None:
    row = _insert_job(db, uuid.UUID(world.student_share_id), status="queued")
    r = client.post(f"/video-jobs/{row.id}/retry", headers=auth_header(world.student_token))
    assert r.status_code == 409


def test_retry_done_job_returns_409(client: TestClient, world: World, db: Session) -> None:
    row = _insert_job(db, uuid.UUID(world.student_share_id), status="done")
    r = client.post(f"/video-jobs/{row.id}/retry", headers=auth_header(world.student_token))
    assert r.status_code == 409


def test_retry_wrong_owner_returns_403(client: TestClient, world: World, db: Session) -> None:
    row = _insert_job(
        db, uuid.UUID(world.student_share_id), status="failed", error_code="build_failed"
    )
    r = client.post(f"/video-jobs/{row.id}/retry", headers=auth_header(world.parent_token))
    assert r.status_code == 403


# ── error-code message mapping ────────────────────────────────────────────────


# ── GET /video-jobs/topics ────────────────────────────────────────────────────


def test_topics_returns_sections_for_prefix(client: TestClient, world: World, db: Session) -> None:
    from app.db.models import BookRow, ChapterRow, CurriculumRow, SectionRow

    # Postgres enforces the foreign keys, so each parent row is written before its children.
    db.merge(CurriculumRow(id="tvj", default_timezone="UTC", jurisdiction_profile="default_strict"))
    db.flush()
    db.merge(
        BookRow(
            id="tvj.10.maths",
            curriculum_id="tvj",
            grade=10,
            default_chapter_id="tvj.10.maths.ch01",
        )
    )
    db.flush()
    db.merge(
        ChapterRow(
            id="tvj.10.maths.ch01",
            book_id="tvj.10.maths",
            overlay_id="tvj-ch01",
            chapter_key="ch01",
            titles={"en": "Algebra"},
            position=1,
        )
    )
    db.flush()
    db.merge(
        SectionRow(
            id="tvj.10.maths.ch01.s1",
            chapter_id="tvj.10.maths.ch01",
            order=1,
            titles={"en": "Variables"},
            page_start=5,
            page_end=10,
        )
    )
    db.commit()

    r = client.get("/video-jobs/topics?node_prefix=tvj", headers=auth_header(world.student_token))
    assert r.status_code == 200, r.text
    topics = r.json()["topics"]
    assert len(topics) == 1
    t = topics[0]
    assert t["node_id"] == "tvj.10.maths.ch01.s1"
    assert t["chapter_title"] == "Algebra"
    assert t["section_title"] == "Variables"
    assert t["page_start"] == 5
    assert t["page_end"] == 10


def test_topics_unknown_prefix_returns_empty(client: TestClient, world: World) -> None:
    r = client.get(
        "/video-jobs/topics?node_prefix=zzz_none", headers=auth_header(world.student_token)
    )
    assert r.status_code == 200
    assert r.json()["topics"] == []


def test_topics_requires_auth(client: TestClient) -> None:
    r = client.get("/video-jobs/topics")
    assert r.status_code == 401


# ── file serving helpers ──────────────────────────────────────────────────────


def _insert_done_job(db: Session, student_id: uuid.UUID, result_dir: Path) -> VideoJobRow:
    job_id = uuid.uuid4()
    (result_dir / "lesson.mp4").write_bytes(b"FAKE-MP4-DATA")
    sources_data = {
        "caveats": ["Engine caveat."],
        "book": {"path": "/internal/secret/book.pdf", "title": "NCERT Mathematics"},
    }
    (result_dir / "sources.json").write_text(json.dumps(sources_data))
    row = VideoJobRow(
        id=job_id,
        student_id=student_id,
        node_id=_NODE,
        request_json={"requestId": str(job_id)},
        idempotency_key=str(uuid.uuid4()),
        status="done",
        events=[],
        created_at=now_utc(),
        result_path=str(result_dir),
        sources_json_path=str(result_dir / "sources.json"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ── GET /video-jobs/{id}/lesson.mp4 ──────────────────────────────────────────


def test_lesson_mp4_serves_file(
    client: TestClient, world: World, db: Session, tmp_path: Path
) -> None:
    row = _insert_done_job(db, uuid.UUID(world.student_share_id), tmp_path)
    r = client.get(f"/video-jobs/{row.id}/lesson.mp4", headers=auth_header(world.student_token))
    assert r.status_code == 200
    assert "video/mp4" in r.headers["content-type"]
    assert r.content == b"FAKE-MP4-DATA"


def test_lesson_mp4_404_when_not_done(client: TestClient, world: World, db: Session) -> None:
    row = _insert_job(db, uuid.UUID(world.student_share_id), status="running")
    r = client.get(f"/video-jobs/{row.id}/lesson.mp4", headers=auth_header(world.student_token))
    assert r.status_code == 404


def test_lesson_mp4_403_wrong_owner(
    client: TestClient, world: World, db: Session, tmp_path: Path
) -> None:
    row = _insert_done_job(db, uuid.UUID(world.student_share_id), tmp_path)
    r = client.get(f"/video-jobs/{row.id}/lesson.mp4", headers=auth_header(world.parent_token))
    assert r.status_code == 403


def test_lesson_mp4_admin_can_access(
    client: TestClient, world: World, db: Session, tmp_path: Path
) -> None:
    row = _insert_done_job(db, uuid.UUID(world.student_share_id), tmp_path)
    r = client.get(f"/video-jobs/{row.id}/lesson.mp4", headers=auth_header(world.admin_token))
    assert r.status_code == 200


# ── GET /video-jobs/{id}/sources.json ────────────────────────────────────────


def test_sources_json_strips_path_keys(
    client: TestClient, world: World, db: Session, tmp_path: Path
) -> None:
    row = _insert_done_job(db, uuid.UUID(world.student_share_id), tmp_path)
    r = client.get(f"/video-jobs/{row.id}/sources.json", headers=auth_header(world.student_token))
    assert r.status_code == 200
    body = r.json()
    assert body["caveats"] == ["Engine caveat."]
    # 'path' key must be stripped; 'title' must survive
    book = body.get("book", {})
    assert "path" not in book
    assert book["title"] == "NCERT Mathematics"


def test_sources_json_404_when_not_done(client: TestClient, world: World, db: Session) -> None:
    row = _insert_job(db, uuid.UUID(world.student_share_id), status="queued")
    r = client.get(f"/video-jobs/{row.id}/sources.json", headers=auth_header(world.student_token))
    assert r.status_code == 404


def test_sources_json_403_wrong_owner(
    client: TestClient, world: World, db: Session, tmp_path: Path
) -> None:
    row = _insert_done_job(db, uuid.UUID(world.student_share_id), tmp_path)
    r = client.get(f"/video-jobs/{row.id}/sources.json", headers=auth_header(world.parent_token))
    assert r.status_code == 403


# ── error-code message mapping ────────────────────────────────────────────────


@pytest.mark.parametrize(
    "code,expected_msg",
    [
        ("no_curriculum_data", "This topic isn't available yet."),
        ("no_lesson_for_topic", "This topic isn't available yet."),
        ("build_failed", "Something went wrong — please try again."),
        ("render_failed", "Something went wrong — please try again."),
        ("qa_failed", "Something went wrong — please try again."),
        ("cancelled", "Request was cancelled."),
    ],
)
def test_error_message_for_code(
    client: TestClient, world: World, db: Session, code: str, expected_msg: str
) -> None:
    row = _insert_job(db, uuid.UUID(world.student_share_id), status="failed", error_code=code)
    r = client.get(f"/video-jobs/{row.id}", headers=auth_header(world.student_token))
    assert r.status_code == 200
    assert r.json()["error_message"] == expected_msg


# ── captions sidecar ─────────────────────────────────────────────────────────

_VTT = "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nHello, everyone.\n"


def _add_captions(result_dir: Path, vtt: bytes | None = None, info: dict | None = None) -> None:
    (result_dir / "captions.vtt").write_bytes(_VTT.encode() if vtt is None else vtt)
    body = {"captions": info or {"file": "captions.vtt", "language": "en-IN", "format": "webvtt"}}
    (result_dir / "result.json").write_text(json.dumps(body), encoding="utf-8")


def _queued_options(db: Session, job_id: str) -> dict[str, Any]:
    row = db.get(VideoJobRow, uuid.UUID(job_id))
    assert row is not None
    return row.request_json["options"]


def test_captions_option_absent_by_default(client: TestClient, world: World, db: Session) -> None:
    r, _ = _create_job(client, world.student_token)
    assert r.status_code == 202
    assert "captions" not in _queued_options(db, r.json()["id"])


def test_captions_option_sent_when_setting_on(
    client: TestClient, world: World, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "video_captions_sidecar", True)
    r, key = _create_job(client, world.student_token)
    assert r.status_code == 202
    options = _queued_options(db, r.json()["id"])
    assert options["captions"] == "sidecar"
    assert options["locale"] == "en-IN"
    # the same key still returns the same job (idempotency is unchanged)
    again, _ = _create_job(client, world.student_token, idem=key)
    assert again.status_code == 200 and again.json()["id"] == r.json()["id"]


def test_job_view_has_no_captions_without_sidecar(
    client: TestClient, world: World, db: Session, tmp_path: Path
) -> None:
    row = _insert_done_job(db, uuid.UUID(world.student_share_id), tmp_path)
    r = client.get(f"/video-jobs/{row.id}", headers=auth_header(world.student_token))
    assert r.json()["captions"] is None
    r = client.get(f"/video-jobs/{row.id}/captions.vtt", headers=auth_header(world.student_token))
    assert r.status_code == 404


def test_job_view_lists_captions_and_serves_vtt(
    client: TestClient, world: World, db: Session, tmp_path: Path
) -> None:
    row = _insert_done_job(db, uuid.UUID(world.student_share_id), tmp_path)
    _add_captions(tmp_path)
    r = client.get(f"/video-jobs/{row.id}", headers=auth_header(world.student_token))
    assert r.json()["captions"] == {
        "url": f"/video-jobs/{row.id}/captions.vtt",
        "language": "en-IN",
        "format": "webvtt",
    }
    f = client.get(f"/video-jobs/{row.id}/captions.vtt", headers=auth_header(world.student_token))
    assert f.status_code == 200
    assert f.headers["content-type"] == "text/vtt; charset=utf-8"
    assert f.headers["x-content-type-options"] == "nosniff"
    assert f.text == _VTT


def test_captions_descriptor_ignores_unknown_fields_and_bad_language(
    client: TestClient, world: World, db: Session, tmp_path: Path
) -> None:
    row = _insert_done_job(db, uuid.UUID(world.student_share_id), tmp_path)
    info = {"file": "captions.vtt", "language": "<script>", "format": "webvtt", "extra": 1}
    _add_captions(tmp_path, info=info)
    r = client.get(f"/video-jobs/{row.id}", headers=auth_header(world.student_token))
    assert r.json()["captions"]["language"] == "en"


@pytest.mark.parametrize(
    "info",
    [
        {"file": "../../etc/passwd", "language": "en", "format": "webvtt"},
        {"file": "other.vtt", "language": "en", "format": "webvtt"},
        {"file": "captions.vtt", "language": "en", "format": "srt"},
        "not a dict",
    ],
)
def test_captions_descriptor_refuses_other_files(
    client: TestClient, world: World, db: Session, tmp_path: Path, info: Any
) -> None:
    row = _insert_done_job(db, uuid.UUID(world.student_share_id), tmp_path)
    _add_captions(tmp_path, info=info)
    r = client.get(f"/video-jobs/{row.id}", headers=auth_header(world.student_token))
    assert r.json()["captions"] is None


@pytest.mark.parametrize(
    "vtt",
    [b"not webvtt at all", b"WEBVTT\n\n\xff\xfe broken", b"WEBVTT\n" + b"a" * (512 * 1024 + 1)],
    ids=["no-header", "bad-utf8", "too-big"],
)
def test_captions_bad_file_is_404(
    client: TestClient, world: World, db: Session, tmp_path: Path, vtt: bytes
) -> None:
    row = _insert_done_job(db, uuid.UUID(world.student_share_id), tmp_path)
    _add_captions(tmp_path, vtt=vtt)
    h = auth_header(world.student_token)
    assert client.get(f"/video-jobs/{row.id}/captions.vtt", headers=h).status_code == 404
    assert client.get(f"/video-jobs/{row.id}", headers=h).json()["captions"] is None


@pytest.mark.parametrize(
    "tail",
    ["..%2Fsources.json", "..%2F..%2Fcaptions.vtt", "captions.VTT"],
)
def test_captions_route_traversal_attempts_fail(
    client: TestClient, world: World, db: Session, tmp_path: Path, tail: str
) -> None:
    row = _insert_done_job(db, uuid.UUID(world.student_share_id), tmp_path)
    _add_captions(tmp_path)
    r = client.get(f"/video-jobs/{row.id}/{tail}", headers=auth_header(world.student_token))
    assert r.status_code in (404, 422)
    assert "WEBVTT" not in r.text


def test_captions_not_served_for_another_student(
    client: TestClient, world: World, db: Session, tmp_path: Path
) -> None:
    row = _insert_done_job(db, uuid.UUID(world.student_share_id), tmp_path)
    _add_captions(tmp_path)
    r = client.get(f"/video-jobs/{row.id}/captions.vtt", headers=auth_header(world.parent_token))
    assert r.status_code == 403
    assert client.get(f"/video-jobs/{row.id}/captions.vtt").status_code in (401, 403)


def test_captions_symlink_is_not_followed(
    client: TestClient, world: World, db: Session, tmp_path: Path
) -> None:
    row = _insert_done_job(db, uuid.UUID(world.student_share_id), tmp_path)
    outside = tmp_path.parent / f"outside-{uuid.uuid4().hex}.vtt"
    outside.write_text(_VTT, encoding="utf-8")
    try:
        (tmp_path / "captions.vtt").symlink_to(outside)
    except OSError:
        pytest.skip("symlinks not permitted here")
    (tmp_path / "result.json").write_text(
        json.dumps({"captions": {"file": "captions.vtt", "language": "en", "format": "webvtt"}})
    )
    r = client.get(f"/video-jobs/{row.id}/captions.vtt", headers=auth_header(world.student_token))
    assert r.status_code == 404


def test_captions_404_while_not_done(client: TestClient, world: World, db: Session) -> None:
    row = _insert_job(db, uuid.UUID(world.student_share_id), status="running")
    r = client.get(f"/video-jobs/{row.id}/captions.vtt", headers=auth_header(world.student_token))
    assert r.status_code == 404
