"""A factory-stamped tier A item, loaded from the lane's content layout, reaches a student only when
the owner's switches allow it. The overlay is made live in this fixture only; no default changes.
"""

from __future__ import annotations

import copy
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.content.gate import row_is_servable
from app.content.loader import _factory_backing, _suspend_from_ledger, _upsert
from app.content.validator import ValidationReport, load_bundle
from app.db.models import ItemRow, OverlayRow, StudentRow
from app.factory.suspend import suspend_item
from app.player.runtime import load_catalog
from tests.conftest import MemoryOtpSender, auth_header, signup
from tests.content.factory_fixture import OVERLAY, build_factory_root


@pytest.fixture(scope="module")
def factory_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build_factory_root(tmp_path_factory.mktemp("serving"), count=6)[0]


def _load(db: Session, root: Path) -> list[str]:
    bundle = load_bundle(root)
    report = ValidationReport(bundle=bundle)
    backing, suspended = _factory_backing(root, report)
    assert report.errors == []
    _upsert(db, bundle, prune=False, backing=backing)
    _suspend_from_ledger(db, suspended)
    live = db.get(OverlayRow, OVERLAY)
    assert live is not None and live.live is False  # the content ships not live
    live.live = True  # test fixture only: no production default or content file changes
    db.commit()
    return [i.id for i in bundle.items]


def _served(db: Session) -> set[str]:
    return {item.id for item in load_catalog(db, allow_draft=settings.allow_draft_content)}


def test_the_serving_rule_for_a_stamped_tier_a_item(db: Session, factory_root: Path):
    ids = _load(db, factory_root)
    rows = db.scalars(select(ItemRow)).all()
    assert {r.id for r in rows} == set(ids) and all(r.tier == "A" for r in rows)

    # production defaults: a stamped item is NOT served
    assert settings.serve_tier_a_unreviewed is False and settings.allow_draft_content is False
    assert _served(db) == set()

    # the owner's switch on: stamped, original, not suspended, record intact => served
    settings.serve_tier_a_unreviewed = True
    assert _served(db) == set(ids)

    # a hand-edited tier on a copy is not served: the record names other content
    original = db.get(ItemRow, ids[0])
    assert original is not None
    forged_record = ItemRow(
        **{
            c.name: copy.deepcopy(getattr(original, c.name))
            for c in ItemRow.__table__.columns
            if c.name != "id"
        },
        id=ids[0] + ".copy",
    )
    no_record = ItemRow(
        **{
            c.name: copy.deepcopy(getattr(original, c.name))
            for c in ItemRow.__table__.columns
            if c.name not in ("id", "verification", "certificate_hash")
        },
        id=ids[0] + ".bare",
    )
    db.add_all([forged_record, no_record])
    db.commit()
    assert _served(db) == set(ids)  # neither copy is served
    assert not row_is_servable(forged_record, allow_draft=False, serve_tier_a_unreviewed=True)
    assert not row_is_servable(no_record, allow_draft=False, serve_tier_a_unreviewed=True)

    # a suspended item is never served, with or without the switch
    assert suspend_item(db, ids[1], "audit finding")
    db.commit()
    assert _served(db) == set(ids) - {ids[1]}
    settings.allow_draft_content = True  # even development serving respects suspension
    assert ids[1] not in _served(db)
    settings.allow_draft_content = False
    settings.serve_tier_a_unreviewed = False
    assert _served(db) == set()


def _student_token(client: TestClient, sender: MemoryOtpSender, db: Session) -> tuple[str, str]:
    parent = signup(client, sender, "factory-parent@example.com")
    created = client.post(
        "/students",
        json={"display_name": "Factory Kid", "grade": 10, "board": "cbse"},
        headers=auth_header(parent),
    )
    assert created.status_code == 200, created.text
    sid = created.json()["id"]
    consent = client.post(
        f"/students/{sid}/consent",
        json={"version": "v1", "scopes": ["tutoring"]},
        headers=auth_header(parent),
    )
    assert consent.status_code == 200, consent.text
    pin = client.post(f"/students/{sid}/pin", json={"pin": "1234"}, headers=auth_header(parent))
    assert pin.status_code == 200, pin.text
    student = db.get(StudentRow, uuid.UUID(sid))
    assert student is not None and student.book_id == "cbse.10.maths"
    login = client.post(
        "/auth/student-login", json={"family_code": student.family_code, "pin": "1234"}
    )
    assert login.status_code == 200, login.text
    return sid, login.json()["access_token"]


def _first_item(client: TestClient, session_id: str, started: dict, headers: dict) -> str | None:
    action = started["action"]
    for _ in range(6):
        if action["type"] in {"show_item", "warmup_item"}:
            return str(action["item_id"])
        if action["type"] == "predict":
            body = {"event_type": "predict_response", "payload": {"response": "2"}}
        else:
            body = {"event_type": "continue", "payload": {}}
        step = client.post(
            f"/sessions/{session_id}/events",
            json={"client_event_id": str(uuid.uuid4()), **body},
            headers=headers,
        )
        assert step.status_code == 200, step.text
        action = step.json()["action"]
    return None


def test_a_live_overlay_with_stamped_items_starts_a_practice_session(
    client: TestClient, sender: MemoryOtpSender, db: Session, factory_root: Path
):
    ids = set(_load(db, factory_root))
    sid, token = _student_token(client, sender, db)
    headers = auth_header(token)
    chapter = "cbse.10.maths.quadratic"  # a chapter of the student's book, added in curriculum.yaml

    # switches off (production defaults): the session starts but offers none of the stamped items
    started = client.post(
        "/sessions",
        json={"student_id": sid, "type": "practice", "chapter_id": chapter},
        headers=headers,
    )
    assert started.status_code == 200, started.text
    assert _first_item(client, started.json()["id"], started.json(), headers) not in ids

    # owner's switch on: a stamped item is selected and served to the student
    settings.serve_tier_a_unreviewed = True
    client.post(f"/sessions/{started.json()['id']}/events", json={
        "client_event_id": str(uuid.uuid4()), "event_type": "end", "payload": {}
    }, headers=headers)  # fmt: skip
    db.expire_all()
    from app.db.models import SessionRow

    for row in db.scalars(select(SessionRow)).all():
        row.ended_at = row.ended_at or row.started_at
        row.resumable = False
    db.commit()
    started = client.post(
        "/sessions",
        json={"student_id": sid, "type": "practice", "chapter_id": chapter},
        headers=headers,
    )
    assert started.status_code == 200, started.text
    served = _first_item(client, started.json()["id"], started.json(), headers)
    assert served in ids
