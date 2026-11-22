"""Mistake notebook slice 1: the write on a wrong first answer, and the three routes.

Time is pinned by patching the clock the router and the store are given; nothing here reads the
real clock. Rows hold ids and times only.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.notebook.router as router_mod
from app.config import settings
from app.db.models import (
    ConsentRow,
    EventRow,
    ItemRow,
    NotebookEntryRow,
    SessionRow,
    SkillRow,
)
from app.learner.notebook_store import record_miss
from app.orchestrator.types import SessionState
from tests.conftest import World, auth_header

SKILL = "MATH.ALG.LIN1.SOLVE_ONE_STEP"
T0 = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)


def day(n: float) -> datetime:
    return T0 + timedelta(days=n)


@pytest.fixture(autouse=True)
def _on(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(settings, "mistake_notebook_enabled", True)
    monkeypatch.setattr(settings, "allow_draft_content", True)
    monkeypatch.setattr(router_mod, "now_utc", lambda: T0)
    yield


def at(monkeypatch: pytest.MonkeyPatch, when: datetime) -> None:
    monkeypatch.setattr(router_mod, "now_utc", lambda: when)


def seed_items(db: Session, ids: tuple[str, ...] = ("ITEM.A", "ITEM.B", "ITEM.C")) -> None:
    if db.get(SkillRow, SKILL) is None:
        db.add(
            SkillRow(
                id=SKILL,
                title={"en": "One step"},
                grade_band=[9],
                subject="math",
                prerequisites=[],
                related=[],
                misconceptions=[],
                bkt={"p_init": 0.2, "p_learn": 0.15, "p_slip": 0.1, "p_guess": 0.2},
                status="approved",
            )
        )
    for n, item_id in enumerate(ids):
        db.add(
            ItemRow(
                id=item_id,
                skill_ids=[SKILL],
                primary_skill=SKILL,
                difficulty=0.25 + n / 100,
                type="expression",
                pool="practice",
                stem={"en": f"Solve for x: x + {n + 4} = 10"},
                verify=f"x + {n + 4} = 10",
                options=[],
                answer={"sympy": str(6 - n), "accept": [str(6 - n)]},
                solution_steps=[],
                hints=[],
                prediction_prompt={"en": "?"},
                misconception_rules=[],
                status="draft",
            )
        )
    db.commit()


def entry(db: Session, world: World, item_id: str = "ITEM.A", **over: Any) -> NotebookEntryRow:
    fields: dict[str, Any] = {
        "id": uuid.uuid4(),
        "student_id": uuid.UUID(world.student_share_id),
        "item_id": item_id,
        "skill_id": SKILL,
        "misconception_id": None,
        "stage": 0,
        "state": "open",
        "anchor_at": T0,
        "due_at": day(2),
        "created_at": T0,
        "updated_at": T0,
    }
    fields.update(over)
    row = NotebookEntryRow(**fields)
    db.add(row)
    db.commit()
    return row


def state(correct: bool | None, diagnosis: dict[str, Any] | None = None) -> SessionState:
    s = SessionState("practice", T0, (), (), {})
    s.last_correct = correct
    s.last_diagnosis = diagnosis
    return s


def head(world: World) -> dict[str, str]:
    return auth_header(world.student_token)


# ---- the write ----------------------------------------------------------------------------------


def miss(db: Session, world: World, **over: Any) -> bool:
    args: dict[str, Any] = {
        "event_type": "answer",
        "state": state(False),
        "misconception_id": None,
        "item_id": "ITEM.A",
    }
    args.update(over)
    return record_miss(
        db,
        uuid.UUID(world.student_share_id),
        args["event_type"],
        args["state"],
        args["misconception_id"],
        args["item_id"],
        T0,
    )


def rows(db: Session) -> list[NotebookEntryRow]:
    return list(db.scalars(select(NotebookEntryRow)))


def test_wrong_first_answer_makes_one_entry_due_in_two_days(db: Session, world: World) -> None:
    seed_items(db)
    assert miss(db, world)
    db.commit()
    (row,) = rows(db)
    assert (row.item_id, row.skill_id, row.stage, row.state) == ("ITEM.A", SKILL, 0, "open")
    assert row.due_at is not None and row.due_at.replace(tzinfo=UTC) == day(2)


def test_entry_holds_ids_and_times_only(db: Session) -> None:
    kinds = {c.name: str(c.type) for c in NotebookEntryRow.__table__.columns}
    assert not [n for n in kinds if "text" in n or "answer" in n or "response" in n]
    assert not [t for t in kinds.values() if "JSON" in t.upper() or "TEXT" in t.upper()]


def test_misconception_kept_only_when_diagnosed(db: Session, world: World) -> None:
    seed_items(db)
    diag = {"class": "misconception"}
    assert miss(db, world, state=state(False, diag), misconception_id="MC.QUAD.FACTOR_SIGN_READ")
    assert miss(db, world, item_id="ITEM.B", state=state(False, {"class": "slip"}),
                misconception_id="MC.X")  # fmt: skip
    db.commit()
    by_item = {r.item_id: r.misconception_id for r in rows(db)}
    assert by_item == {"ITEM.A": "MC.QUAD.FACTOR_SIGN_READ", "ITEM.B": None}


@pytest.mark.parametrize(
    "over",
    [
        {"state": state(True)},  # right
        {"state": state(None)},  # no verdict (skipped, unreadable)
        {"event_type": "request_hint"},
        {"event_type": "skip"},
        {"item_id": None},
        {"item_id": "ITEM.MISSING"},
    ],
)
def test_no_entry_unless_a_wrong_answer(db: Session, world: World, over: dict[str, Any]) -> None:
    seed_items(db)
    assert not miss(db, world, **over)
    assert rows(db) == []


def test_only_the_first_answer_counts(db: Session, world: World) -> None:
    seed_items(db)
    session_id = uuid.uuid4()
    db.add(
        SessionRow(
            id=session_id,
            student_id=uuid.UUID(world.student_share_id),
            started_at=T0,
            type="practice",
            last_active_at=T0,
        )
    )
    db.add(
        EventRow(
            id=uuid.uuid4(),
            session_id=session_id,
            item_id="ITEM.A",
            event_type="answer",
            payload={},
            correct=True,
            created_at=T0,
        )
    )
    db.commit()
    assert not miss(db, world)  # answered before (right): a later slip is not a first miss
    assert miss(db, world, item_id="ITEM.B")
    db.commit()
    assert not miss(db, world, item_id="ITEM.B")  # already in the notebook
    assert len(rows(db)) == 1


def test_flag_off_writes_nothing(
    db: Session, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_items(db)
    monkeypatch.setattr(settings, "mistake_notebook_enabled", False)
    assert not miss(db, world)
    assert rows(db) == []


def test_no_tutoring_consent_writes_nothing(db: Session, world: World) -> None:
    seed_items(db)
    for c in db.scalars(select(ConsentRow)):
        c.revoked_at = T0
    db.commit()
    assert not miss(db, world)


# ---- the routes ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    [("get", "/notebook/due"), ("get", "/notebook"), ("post", f"/notebook/{uuid.uuid4()}/result")],
)
def test_flag_off_is_404(
    client: TestClient, world: World, monkeypatch: pytest.MonkeyPatch, method: str, path: str
) -> None:
    monkeypatch.setattr(settings, "mistake_notebook_enabled", False)
    kwargs: dict[str, Any] = {"json": {"outcome": "right"}} if method == "post" else {}
    response = getattr(client, method)(path, headers=head(world), **kwargs)
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "notebook_disabled"


def test_students_only_and_consent(client: TestClient, world: World, db: Session) -> None:
    parent = client.get("/notebook", headers=auth_header(world.parent_token))
    assert parent.status_code == 403
    assert parent.json()["detail"]["code"] == "notebook_students_only"
    assert client.get("/notebook").status_code in (401, 403)
    for c in db.scalars(select(ConsentRow)):
        c.revoked_at = T0
    db.commit()
    revoked = client.get("/notebook", headers=head(world))
    assert revoked.status_code == 403
    assert revoked.json()["detail"]["code"] == "notebook_consent_required"


def test_due_lists_only_due_entries_with_a_new_form(
    client: TestClient, world: World, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_items(db)
    row = entry(db, world, "ITEM.A")
    entry(db, world, "ITEM.B", due_at=day(5))
    assert client.get("/notebook/due", headers=head(world)).json()["entries"] == []
    at(monkeypatch, day(2))
    (found,) = client.get("/notebook/due", headers=head(world)).json()["entries"]
    assert found["entry_id"] == str(row.id)
    assert found["skill_title"] == "One step"
    assert found["return_number"] == 1 and found["return_after_days"] == 2
    assert found["item_id"] != "ITEM.A" and found["same_item"] is False
    assert set(found) == {
        "entry_id",
        "skill_id",
        "skill_title",
        "misconception_id",
        "return_number",
        "return_after_days",
        "item_id",
        "same_item",
    }


def test_due_falls_back_to_the_same_item_when_there_is_no_other(
    client: TestClient, world: World, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_items(db, ("ITEM.A",))
    entry(db, world, "ITEM.A")
    at(monkeypatch, day(3))
    (found,) = client.get("/notebook/due", headers=head(world)).json()["entries"]
    assert (found["item_id"], found["same_item"]) == ("ITEM.A", True)


def test_due_is_capped(
    client: TestClient, world: World, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    ids = tuple(f"ITEM.{n}" for n in range(8))
    seed_items(db, ids)
    for n, item_id in enumerate(ids):
        entry(db, world, item_id, due_at=day(2) + timedelta(minutes=n))
    at(monkeypatch, day(4))
    got = client.get("/notebook/due", headers=head(world)).json()["entries"]
    assert len(got) == 5  # due_limit in config/notebook.yaml
    assert got[0]["entry_id"] != got[-1]["entry_id"]


def test_right_moves_to_the_next_return_and_wrong_goes_back(
    client: TestClient, world: World, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_items(db)
    row = entry(db, world)
    at(monkeypatch, day(2))
    ok = client.post(f"/notebook/{row.id}/result", json={"outcome": "right"}, headers=head(world))
    assert ok.status_code == 200, ok.text
    assert (ok.json()["state"], ok.json()["return_number"]) == ("open", 2)
    assert ok.json()["due_at"].startswith(day(6).isoformat()[:19])
    at(monkeypatch, day(6))
    bad = client.post(f"/notebook/{row.id}/result", json={"outcome": "wrong"}, headers=head(world))
    assert (bad.json()["state"], bad.json()["return_number"]) == ("open", 1)
    assert bad.json()["due_at"].startswith(day(8).isoformat()[:19])


def test_three_rights_settle_the_entry(
    client: TestClient, world: World, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_items(db)
    row = entry(db, world)
    last: dict[str, Any] = {}
    for d in (2, 6, 15):
        at(monkeypatch, day(d))
        last = client.post(
            f"/notebook/{row.id}/result", json={"outcome": "right"}, headers=head(world)
        ).json()
    assert last["state"] == "settled" and last["due_at"] is None
    at(monkeypatch, day(40))
    assert client.get("/notebook/due", headers=head(world)).json()["entries"] == []


def test_result_refusals(
    client: TestClient, world: World, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_items(db)
    row = entry(db, world)
    url = f"/notebook/{row.id}/result"
    early = client.post(url, json={"outcome": "right"}, headers=head(world))
    assert (early.status_code, early.json()["detail"]["code"]) == (409, "notebook_entry_not_due")
    at(monkeypatch, day(2))
    for body in ({"outcome": "skipped"}, {"outcome": "right", "response": "x=3"}, {}):
        assert client.post(url, json=body, headers=head(world)).status_code == 422
    missing = client.post(
        f"/notebook/{uuid.uuid4()}/result", json={"outcome": "right"}, headers=head(world)
    )
    assert missing.status_code == 404
    other = entry(db, world, "ITEM.B", student_id=uuid.UUID(world.student_noshare_id))
    foreign = client.post(
        f"/notebook/{other.id}/result", json={"outcome": "right"}, headers=head(world)
    )
    assert foreign.status_code == 404  # another learner's entry looks the same as a missing one


def test_summary_counts_and_no_score(
    client: TestClient, world: World, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_items(db)
    entry(db, world, "ITEM.A")
    entry(db, world, "ITEM.B", stage=2, due_at=day(15))
    entry(db, world, "ITEM.C", stage=2, state="settled", due_at=None)
    at(monkeypatch, day(3))
    body = client.get("/notebook", headers=head(world)).json()
    assert body == {
        "total": 3,
        "due_now": 1,
        "waiting_for_return": {"1": 1, "2": 0, "3": 1},
        "settled": 1,
        "return_days": [2, 6, 15],
    }
    assert not [v for v in body.values() if isinstance(v, float)]
