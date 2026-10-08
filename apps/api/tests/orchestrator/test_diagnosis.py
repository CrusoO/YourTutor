"""G2: diagnosis.classify is pure and driven by a shared fixture (mirrored offline in G9)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app.learner.ladder import SkillLadder
from app.learner.types import LearnerState
from app.orchestrator.diagnosis import CLASSES, Diagnosis, classify
from app.orchestrator.types import CatalogItem, SessionState

FIXTURE = Path(__file__).resolve().parents[4] / "packages/shared/fixtures/diagnosis/classify.json"
DATA = json.loads(FIXTURE.read_text(encoding="utf-8"))


def _item(spec: dict[str, Any]) -> CatalogItem:
    return CatalogItem(
        id="ITEM.DX",
        skill_ids=(spec["skill"],),
        difficulty=0.5,
        pool="practice",
        status="draft",
        answer_sympy=spec["answer"],
        accept=(spec["answer"],),
        misconception_rules=tuple((mid, tuple(vals)) for mid, vals in spec["misconception_rules"]),
        slip_patterns=tuple(spec.get("slip_patterns", ())),
        prereq_signatures=tuple(spec.get("prereq_signatures", ())),
        intermediate_values=tuple(spec.get("intermediate_values", ())),
        min_plausible_ms=spec.get("min_plausible_ms"),
    )


def _state(item: CatalogItem, ctx: dict[str, Any]) -> tuple[LearnerState, SessionState]:
    learner = LearnerState()
    learner.ladders[item.primary_skill] = SkillLadder(
        skill_id=item.primary_skill, achieved=list(range(1, ctx["ladder_level"] + 1))
    )
    session = SessionState(
        session_type="practice",
        now=datetime(2026, 10, 8, tzinfo=UTC),
        catalog=(item,),
        overlay_skill_ids=(item.primary_skill,),
        bkt_params={},
        prerequisites={item.primary_skill: tuple(ctx["prerequisites"])},
        current_item_id=item.id,
        current_skill=item.primary_skill,
    )
    session.misconception_remedial = dict(ctx["remedial"])
    session.fast_streak = ctx["fast_streak"]
    session.help_without_attempt = ctx["help_without_attempt"]
    session.last_wrong_item_id = None if ctx["first_attempt"] else item.id
    return learner, session


@pytest.mark.parametrize("case", DATA["cases"], ids=[c["name"] for c in DATA["cases"]])
def test_classify_matches_the_shared_fixture(case: dict[str, Any]) -> None:
    item = _item(DATA["base_item"])
    ctx = {**DATA["base_context"], **case.get("context", {})}
    learner, session = _state(item, ctx)
    result = classify(item, case["response"], case.get("correct", False), learner, session)
    assert result.kind == case["expected"]["class"]
    if "detail" in case["expected"]:
        assert result.detail == case["expected"]["detail"]


def test_the_class_set_is_the_documented_one() -> None:
    assert set(CLASSES) == {
        "none",
        "misconception",
        "slip",
        "prerequisite_gap",
        "incomplete_procedure",
        "disengagement",
        "generic",
    }


def test_classify_does_not_change_its_inputs() -> None:
    item = _item(DATA["base_item"])
    learner, session = _state(item, {**DATA["base_context"], "ladder_level": 4})
    before = (session.fast_streak, session.help_without_attempt, session.last_wrong_item_id)
    classify(item, "-4", False, learner, session)
    classify(item, "-4", False, learner, session)
    assert before == (session.fast_streak, session.help_without_attempt, session.last_wrong_item_id)
    assert classify(item, "-4", False, learner, session) == classify(
        item, "-4", False, learner, session
    )


def test_diagnosis_serialises_for_the_event_payload() -> None:
    assert Diagnosis("slip", "sign_flip").as_payload() == {"class": "slip", "detail": "sign_flip"}
    assert Diagnosis("generic").as_payload() == {"class": "generic", "detail": None}


def test_an_item_with_no_authored_fields_is_generic_or_misconception_only() -> None:
    bare = CatalogItem(
        id="B", skill_ids=("S",), difficulty=0.5, pool="practice", status="draft", answer_sympy="4"
    )
    learner = LearnerState()
    learner.ladders["S"] = SkillLadder(skill_id="S", achieved=[1, 2, 3, 4])
    session = SessionState(
        session_type="practice",
        now=datetime(2026, 10, 8, tzinfo=UTC),
        catalog=(bare,),
        overlay_skill_ids=("S",),
        bkt_params={},
    )
    assert classify(bare, "-4", False, learner, session).kind == "generic"
