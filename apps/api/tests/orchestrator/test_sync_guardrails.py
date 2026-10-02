from __future__ import annotations

import json
from pathlib import Path

from app.content.validator import item_tier
from app.orchestrator.sync import apply_sync_event, fixture_dir, verified_correct
from app.orchestrator.types import CatalogItem, Event
from app.verifier.check import verify_response
from tests.orchestrator.conftest import make_learner, make_session


def _item_from_dict(raw: dict) -> CatalogItem:
    hints = tuple((int(level), text) for level, text in raw.get("hints", []))
    return CatalogItem(
        id=raw["id"],
        skill_ids=tuple(raw["skill_ids"]),
        difficulty=raw["difficulty"],
        pool=raw["pool"],
        status=raw["status"],
        type=raw.get("type", "expression"),
        answer_sympy=raw.get("answer_sympy", "0"),
        accept=tuple(raw.get("accept", [])),
        hints=hints,
        solution_steps=tuple(raw.get("solution_steps", [])),
        verify=raw.get("verify"),
    )


def _event(raw: dict) -> Event:
    return Event(
        type=raw["type"],
        response=raw.get("response"),
        client_correct=raw.get("client_correct"),
        item_id=raw.get("item_id"),
    )


def _run_fixture(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    raw_items = data.get("items") or [data["item"]]
    items = tuple(_item_from_dict(row) for row in raw_items)
    session = make_session(*items)
    learner = make_learner()
    action = apply_sync_event(learner, session, Event(type="start"))
    if action.type == "predict":
        apply_sync_event(learner, session, Event(type="predict_response", text="guess"))
        apply_sync_event(learner, session, Event(type="continue"))
    last_verified = None
    last_action = None
    for raw in data["events"]:
        event = _event(raw)
        last_verified = verified_correct(session, event)
        last_action = apply_sync_event(learner, session, event)
    return data, session, last_action, last_verified


def test_sync_guardrail_fixtures() -> None:
    paths = sorted(fixture_dir().glob("*.json"))
    assert paths, "expected sync_guardrail fixtures"
    for path in paths:
        data, session, action, verified = _run_fixture(path)
        expect = data["expect"]
        if "verified_correct" in expect:
            assert verified is expect["verified_correct"]
        if expect.get("client_correct_ignored"):
            item = session.item()
            assert item is not None
            assert (
                verify_response(
                    "19",
                    answer_sympy=item.answer_sympy,
                    accept=list(item.accept),
                    verify=item.verify,
                )
                is False
            )
        if expect.get("rejected"):
            assert action is not None and action.rejected is True
            assert action.guardrail_flag == expect.get("guardrail_flag")
        if expect.get("no_hint_level_3"):
            assert action is not None
            assert not (action.type == "hint" and action.hint_level == 3)
        if expect.get("action_type"):
            assert action is not None
            assert action.type == expect["action_type"]
            if expect.get("different_item"):
                shown = {row.id for row in session.catalog}
                assert action.item_id in shown
                assert action.skill_id == expect["same_skill"]
                picked = session.item(action.item_id)
                assert picked is not None
                assert item_tier(picked.difficulty) == expect["same_tier"]


def test_policy_ignores_client_correct_flag() -> None:
    path = fixture_dir() / "ignore_client_correct.json"
    _data, _session, action, verified = _run_fixture(path)
    assert verified is False
    assert action is not None
    assert action.type != "explain_back_prompt"
