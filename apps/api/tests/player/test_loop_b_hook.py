"""Loop B at the end of a session, through the real event endpoint."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import LoopBRecordRow, LoopBSnapshotRow, SessionRow
from app.learner.loop_b import HELP_SEEKING
from app.player import loop_b_hook
from app.player.loop_b_hook import POLICY_VERSION
from tests.conftest import World
from tests.learner.test_chapters import chapters_world  # noqa: F401  (fixture)
from tests.player.test_g2b_api import _three_fast_answers
from tests.player.test_stuck_picker_api import Play, _full_item


@pytest.fixture
def g2b_world(db: Session, chapters_world: World) -> World:  # noqa: F811
    for n in range(1, 7):
        db.add(_full_item(f"G2.{n}", str(5 + n)))
    db.commit()
    return chapters_world


def _end_session(client: TestClient, world: World) -> Play:
    play = Play(client, world)
    _three_fast_answers(play)
    ended = play.send("break_choice", choice="break")
    assert ended["type"] == "end_session"
    return play


def _count(db: Session, model) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def test_it_is_off_by_default(client: TestClient, db: Session, g2b_world: World) -> None:
    assert settings.loop_b_enabled is False
    _end_session(client, g2b_world)
    assert _count(db, LoopBRecordRow) == 0 and _count(db, LoopBSnapshotRow) == 0


def test_when_enabled_ending_a_session_writes_one_versioned_snapshot(
    client: TestClient, db: Session, g2b_world: World
) -> None:
    settings.loop_b_enabled = True
    play = _end_session(client, g2b_world)

    record = db.scalars(select(LoopBRecordRow)).one()
    snapshot = db.scalars(select(LoopBSnapshotRow)).one()
    assert str(record.student_id) == g2b_world.student_share_id
    assert record.version == 1 and set(record.data["processed"]) == {play.session_id}
    assert snapshot.session_id == play.session_id and snapshot.record_version == 1
    assert snapshot.versions["policy_version"] == POLICY_VERSION
    assert (
        len(snapshot.versions["graph_version"]) == 12
        and len(snapshot.versions["param_version"]) == 12
    )
    # three unhinted answers: help-seeking observed as 0, so the estimate sits below its prior mean
    assert (
        snapshot.payload["traits"][HELP_SEEKING]["mean"]
        < loop_b_hook.TRAIT_PRIORS[HELP_SEEKING].mu0
    )
    assert snapshot.payload["mastery"]


def test_a_failure_in_loop_b_never_breaks_ending_the_session(
    client: TestClient, db: Session, g2b_world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings.loop_b_enabled = True

    def boom(*args, **kwargs):
        raise RuntimeError("shadow job exploded")

    monkeypatch.setattr(loop_b_hook, "run_loop_b", boom)
    play = _end_session(client, g2b_world)  # asserts the session still ended cleanly

    assert _count(db, LoopBRecordRow) == 0
    row = db.get(SessionRow, uuid.UUID(play.session_id))
    assert row is not None and row.ended_at is not None


def test_it_runs_once_when_the_session_ends_not_on_every_event(
    client: TestClient, db: Session, g2b_world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings.loop_b_enabled = True
    calls: list[str] = []
    original = loop_b_hook.run_loop_b

    def counting(*args, **kwargs):
        calls.append(kwargs["session_id"])
        return original(*args, **kwargs)

    monkeypatch.setattr(loop_b_hook, "run_loop_b", counting)
    play = Play(client, g2b_world)
    _three_fast_answers(play)
    assert calls == []  # answers alone do not trigger it
    play.send("break_choice", choice="break")
    assert calls == [play.session_id]
