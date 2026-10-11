"""G9: packs and sync. An offline session synced equals the server's recompute, exactly."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import EventRow, MasteryRow, SessionRow, StudentRow
from app.offline.pack import build_pack, canonical, learner_json
from app.offline.sync import offline_session_id, state_hash
from app.player.runtime import load_learner
from app.registries.paths import repo_root
from tests.conftest import World, auth_header
from tests.offline.sim import NS, T0, play, seed_content

FIXTURE = repo_root() / "packages" / "shared" / "fixtures" / "offline_sync" / "session_1.json"


@pytest.fixture
def content(db: Session) -> None:
    seed_content(db)


def _student(db: Session, world: World) -> StudentRow:
    student = db.get(StudentRow, uuid.UUID(world.student_share_id))
    assert student is not None
    return student


def _sync(client: TestClient, world: World, played: dict[str, Any], **over: Any):
    body = {
        "client_session_id": str(uuid.uuid5(NS, "session-1")),
        "started_at": played["started_at"],
        "events": played["events"],
        **over,
    }
    return client.post("/sync/events", json=body, headers=auth_header(world.student_token))


def _core(learner: dict[str, Any]) -> dict[str, Any]:
    return {"mastery": learner["mastery"], "ladders": learner["ladders"]}


# ---- the pack -------------------------------------------------------------------------------


def test_the_pack_holds_the_chapters_offline_items_and_the_students_state(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    res = client.get("/students/me/pack", headers=auth_header(world.student_token))
    assert res.status_code == 200, res.text
    pack = res.json()
    assert pack["overlay"] == ["OFF.S1", "OFF.S2"] and len(pack["catalog"]) == 20
    assert {i["pool"] for i in pack["catalog"]} == {"practice"}
    assert pack["prerequisites"]["OFF.S2"] == ["OFF.S1"]
    assert pack["learner"] == {"mastery": {}, "ladders": {}, "cards": {}}
    assert len(pack["hash"]) == 64 and pack["limits"]["soft_item_cap"] >= 8
    assert "idk" in pack["dont_know"] and pack["notation"]["decimal_separator"] == "."
    assert (
        client.get("/students/me/pack", headers=auth_header(world.parent_token)).status_code == 403
    )


def test_symbolic_and_unmarkable_items_stay_out_of_the_pack(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    from app.db.models import ItemRow

    row = db.get(ItemRow, "OFF.S1.00")
    assert row is not None
    row.answer = {"sympy": "2*x + 2", "accept": []}
    db.commit()
    pack = client.get("/students/me/pack", headers=auth_header(world.student_token)).json()
    assert "OFF.S1.00" not in {i["id"] for i in pack["catalog"]}
    assert len(pack["catalog"]) == 19


def test_the_pack_hash_changes_when_an_item_changes(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    before = build_pack(db, _student(db, world))["hash"]
    from app.db.models import ItemRow

    row = db.get(ItemRow, "OFF.S1.01")
    assert row is not None
    row.difficulty = 0.99
    db.commit()
    assert build_pack(db, _student(db, world))["hash"] != before


# ---- sync -----------------------------------------------------------------------------------


def test_a_synced_offline_session_equals_what_the_browser_computed_byte_for_byte(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    student = _student(db, world)
    played = play(db, student)
    assert len(played["events"]) >= 15
    res = _sync(client, world, played)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["rejected"] == 0 and body["applied"] == len(played["events"])
    assert all(r["diverged"] is False for r in body["results"] if r["diverged"] is not None)
    db.expire_all()
    server = learner_json(load_learner(db, student.id))
    assert canonical(_core(server)) == canonical(_core(played["learner"]))
    assert body["state_hash"] == state_hash(played["learner"])
    assert body["state_hash"] == hashlib.sha256(canonical(_core(server)).encode()).hexdigest()
    assert server["mastery"] and server["ladders"]


def test_syncing_the_same_batch_twice_applies_each_event_once(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    student = _student(db, world)
    played = play(db, student)
    first = _sync(client, world, played).json()
    count = db.scalar(select(func.count()).select_from(EventRow))
    again = _sync(client, world, played).json()
    assert again["applied"] == 0 and again["duplicates"] == len(played["events"])
    assert again["state_hash"] == first["state_hash"]
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(EventRow)) == count


def test_two_batches_give_the_same_state_as_one(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    student = _student(db, world)
    played = play(db, student)
    half = len(played["events"]) // 2
    first = {**played, "events": played["events"][:half]}
    assert _sync(client, world, first).json()["applied"] == half
    final = _sync(client, world, played).json()
    assert final["duplicates"] == half and final["applied"] == len(played["events"]) - half
    assert final["state_hash"] == state_hash(played["learner"])


def test_a_forged_client_correct_is_ignored_and_the_answer_is_marked_here(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    student = _student(db, world)
    played = play(db, student, steps=16, wrong_every=2)
    for event in played["events"]:
        if event["event_type"] == "answer":
            event["payload"]["correct"] = True  # a browser claiming every answer is right
    body = _sync(client, world, played).json()
    assert body["state_hash"] == state_hash(played["learner"])
    db.expire_all()
    rows = db.scalars(select(EventRow).where(EventRow.event_type == "answer")).all()
    assert any(r.correct is False for r in rows)
    assert all(r.payload.get("client_correct") is True for r in rows)


def test_an_illegal_sequence_is_rejected_flagged_and_changes_nothing(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    student = _student(db, world)
    played = play(db, student, steps=4)
    bad = {
        "client_event_id": str(uuid.uuid5(NS, "illegal")),
        "event_type": "show_solution",
        "at": (T0 + timedelta(minutes=3)).isoformat(),
        "item_id": None,
        "payload": {},
    }
    base = _sync(client, world, played).json()
    res = _sync(client, world, {**played, "events": [*played["events"], bad]}).json()
    last = res["results"][-1]
    assert last["status"] == "rejected" and last["guardrail_flag"] == "illegal_reveal"
    assert res["state_hash"] == base["state_hash"]


def test_a_lesson_event_cannot_be_replayed_offline(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    student = _student(db, world)
    played = play(db, student, steps=3)
    event = {
        "client_event_id": str(uuid.uuid5(NS, "lesson")),
        "event_type": "interactive_result",
        "at": (T0 + timedelta(minutes=2)).isoformat(),
        "payload": {"widget_id": "w", "final_state": {}},
    }
    res = _sync(client, world, {**played, "events": [*played["events"], event]}).json()
    assert res["results"][-1]["guardrail_flag"] == "unsupported_offline_event"


def test_times_from_the_future_or_the_past_are_clamped_and_flagged(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    student = _student(db, world)
    played = play(db, student, steps=6)
    events = [dict(e) for e in played["events"]]
    events[2]["at"] = (T0 + timedelta(days=3650)).isoformat()  # the browser clock was wrong
    res = _sync(client, world, {**played, "events": events}).json()
    assert res["applied"] == len(events)
    db.expire_all()
    flagged = db.scalars(select(EventRow)).all()
    assert any("clock_skew" in (r.payload or {}).get("flags", []) for r in flagged)


def test_a_stale_pack_is_reported_but_the_session_is_still_replayed(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    student = _student(db, world)
    played = play(db, student, steps=4)
    res = _sync(client, world, played, pack_hash="0" * 64).json()
    assert res["pack_hash_ok"] is False and res["applied"] == len(played["events"])
    good = _sync(client, world, played, pack_hash=res["server_pack_hash"]).json()
    assert good["pack_hash_ok"] is True


def test_an_event_id_already_used_by_another_session_is_refused(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    student = _student(db, world)
    played = play(db, student, steps=3)
    _sync(client, world, played)
    other = {
        "client_session_id": str(uuid.uuid5(NS, "session-2")),
        "started_at": played["started_at"],
        "events": played["events"][:1],
    }
    res = client.post("/sync/events", json=other, headers=auth_header(world.student_token)).json()
    assert res["results"][0]["guardrail_flag"] == "event_id_conflict"


def test_only_the_student_can_sync_and_only_with_tutoring_consent(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    student = _student(db, world)
    played = play(db, student, steps=2)
    body = {
        "client_session_id": str(uuid.uuid4()),
        "started_at": played["started_at"],
        "events": [],
    }
    assert client.post("/sync/events", json=body).status_code == 401
    parent = client.post("/sync/events", json=body, headers=auth_header(world.parent_token))
    assert parent.status_code == 403
    client.post(
        f"/students/{world.student_share_id}/consent/revoke",
        headers=auth_header(world.parent_token),
    )
    revoked = client.post("/sync/events", json=body, headers=auth_header(world.student_token))
    assert revoked.status_code in (401, 403)


def test_a_batch_is_capped(client: TestClient, world: World, content: None) -> None:
    event = {
        "client_event_id": str(uuid.uuid4()),
        "event_type": "idle_nudge",
        "at": T0.isoformat(),
        "payload": {},
    }
    body = {
        "client_session_id": str(uuid.uuid4()),
        "started_at": T0.isoformat(),
        "events": [event] * 501,
    }
    res = client.post("/sync/events", json=body, headers=auth_header(world.student_token))
    assert res.status_code == 422


def test_the_session_row_is_derived_from_the_client_session_id(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    student = _student(db, world)
    played = play(db, student, steps=3)
    res = _sync(client, world, played).json()
    expected = offline_session_id(student.id, uuid.uuid5(NS, "session-1"))
    assert res["session_id"] == str(expected)
    db.expire_all()
    row = db.get(SessionRow, expected)
    assert row is not None and row.plan["offline"] is True
    assert db.scalar(select(func.count()).select_from(MasteryRow)) >= 1


# ---- the shared fixture the TypeScript mirror replays ------------------------------------------


def test_the_shared_offline_session_fixture_is_what_the_server_computes(
    client: TestClient, world: World, db: Session, content: None
) -> None:
    student = _student(db, world)
    pack = build_pack(db, student)
    played = play(db, student)
    body = _sync(client, world, played).json()
    produced = {
        "note": "Recorded by apps/api/tests/offline/test_sync.py: a session the offline player "
        "plays, and the state the server reaches by replaying it. The TypeScript policy must "
        "reach exactly this state.",
        "pack": {
            k: v for k, v in pack.items() if k not in {"generated_at", "student_id", "lessons"}
        },
        "started_at": played["started_at"],
        "events": played["events"],
        "expected": _core(body["state"]),
        "state_hash": body["state_hash"],
    }
    produced["pack"]["learner"] = {"mastery": {}, "ladders": {}, "cards": {}}
    text = json.dumps(produced, indent=1, ensure_ascii=False) + "\n"
    if os.environ.get("UPDATE_FIXTURES"):
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_text(text, encoding="utf-8")
    assert json.loads(FIXTURE.read_text(encoding="utf-8")) == json.loads(text), (
        "run the test with UPDATE_FIXTURES=1 to re-record"
    )
