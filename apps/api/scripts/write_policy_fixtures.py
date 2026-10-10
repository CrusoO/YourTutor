# ruff: noqa: E501
"""Record golden policy sessions from the Python policy for the offline TypeScript mirror.

Each scenario fixes a catalog, a learner and a session, then plays a list of events through
`app.orchestrator.policy.policy`. After every step the fixture stores the action and the session
and learner state the Python policy produced. The TypeScript policy must reproduce every step.
Answers written as "right" or "wrong" are resolved here against the item on screen, so the
fixture holds concrete responses.

    PYTHONPATH=. python scripts/write_policy_fixtures.py
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

from app.learner.bkt import BktParams
from app.learner.ladder import SkillLadder
from app.learner.types import LearnerState, Mastery, ReviewCard
from app.orchestrator.policy import policy
from app.orchestrator.types import CatalogItem, Event, SessionState
from app.player.runtime import dump_state
from app.registries.paths import repo_root

OUT = repo_root() / "packages" / "shared" / "fixtures" / "policy"
NOW0 = datetime(2026, 10, 12, 9, 0, tzinfo=UTC)

SESSION_KEYS = [
    "phase", "current_skill", "current_item_id", "hint_level_shown", "attempt_after_hint2",
    "explain_back_done", "introduced_skills", "shown_item_ids", "items_completed", "active_ms",
    "last_active_at", "warmup_done", "warmup_left", "ended_reason", "similar_from_item_id",
    "last_wrong_response", "last_wrong_item_id", "fast_streak", "help_without_attempt",
    "stuck_item_id", "stretch_served", "wheel_skills", "wrong_first_streak", "skill_items",
    "seen_items", "answered_items", "probe_for", "lesson_prereq_levels", "probe_skill",
    "probe_done", "scheduled_prereq", "scheduled_left", "reveals", "wrong_run", "tier_down_items",
    "tier_up_next", "unhinted_run", "last_failure", "win_served", "skill_failed",
    "last_praise_at", "praise_count", "stretch_skills", "blocked_skills", "content_gaps",
    "stored_explain_text",
]  # fmt: skip
SET_KEYS = {
    "explain_back_done", "introduced_skills", "wheel_skills", "seen_items", "answered_items",
    "probe_done", "skill_failed", "stretch_skills", "blocked_skills",
}  # fmt: skip


def item(
    item_id: str,
    skill: str,
    difficulty: float,
    answer: str,
    *,
    role: str = "procedure",
    structure: str = "s",
    wrong: str = "99",
    **over: Any,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": item_id,
        "skill_ids": [skill],
        "difficulty": difficulty,
        "pool": "practice",
        "status": "approved",
        "role": role,
        "structure": structure,
        "type": "expression",
        "answer_sympy": answer,
        "accept": [answer],
        "hints": [
            [1, f"Hint one for {item_id}. What undoes the operation?"],
            [2, f"Hint two for {item_id}. Do the same to both sides."],
            [3, f"Hint three for {item_id}. Take the number away, then read x."],
        ],
        "solution_steps": [f"Solve {item_id} step by step.", f"x = {answer}"],
        "misconception_rules": [],
        "prediction_prompt": f"What is the first step for {skill}?",
        "authored_explanation": f"{skill} explained.",
        "options": [],
        "last_shown_at": None,
        "slip_patterns": [],
        "prereq_signatures": [],
        "intermediate_values": [],
        "min_plausible_ms": None,
        "step_hints": [],
        "hint_restate": "",
        "_wrong": wrong,
    }
    base.update(over)
    return base


def catalog() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    plan = {
        "S1": [("a", 0.2, "5", "procedure"), ("b", 0.3, "7", "procedure"),
               ("c", 0.5, "9", "procedure"), ("d", 0.6, "11", "procedure"),
               ("e", 0.9, "13", "procedure"), ("f", 0.3, "4", "recall"),
               ("g", 0.5, "6", "explain"), ("h", 0.5, "8", "apply"),
               ("i", 0.9, "10", "transfer"), ("j", 0.9, "12", "transfer")],
        "S2": [("a", 0.2, "3", "procedure"), ("b", 0.3, "2", "procedure"),
               ("c", 0.5, "4", "procedure"), ("d", 0.6, "6", "procedure"),
               ("e", 0.9, "8", "procedure"), ("f", 0.5, "5", "apply"),
               ("g", 0.9, "7", "transfer")],
        "S3": [("a", 0.2, "14", "procedure"), ("b", 0.5, "15", "procedure"),
               ("c", 0.9, "16", "procedure")],
        "SW": [("a", 0.5, "20", "apply"), ("b", 0.5, "21", "apply")],
    }  # fmt: skip
    for skill, entries in plan.items():
        for index, (suffix, difficulty, answer, role) in enumerate(entries):
            rows.append(
                item(
                    f"{skill}.{suffix}",
                    skill,
                    difficulty,
                    answer,
                    role=role,
                    structure=f"{skill}-st{index % 3}",
                    wrong=str(int(answer) + 40),
                )
            )
    # richer items used by particular scenarios
    for row in rows:
        if row["id"] == "S2.c":
            row["misconception_rules"] = [["MC.WRONG_SIDE", ["70"]], ["MC.PREREQ", ["71"]]]
            row["slip_patterns"] = [{"kind": "off_by", "max_distance": 1}, {"kind": "sign_flip"}]
            row["prereq_signatures"] = [{"skill_id": "S1", "values": ["72"]}]
            row["intermediate_values"] = ["73"]
            row["step_hints"] = ["First look at the left side.", "Now undo the addition."]
            row["hint_restate"] = "Find x so the equation is true."
            row["min_plausible_ms"] = 3000
        if row["id"] == "S1.g":
            row["type"] = "mcq"
            row["answer_sympy"] = "b"
            row["accept"] = []
            row["options"] = [{"id": "a", "en": "Add"}, {"id": "b", "en": "Subtract"}]
            row["_wrong"] = "a"
        if row["id"] in {"S1.a", "S2.a"}:
            row["min_plausible_ms"] = 3000
    return rows


def to_item(row: dict[str, Any]) -> CatalogItem:
    data = {k: v for k, v in row.items() if not k.startswith("_")}
    return CatalogItem(
        id=data["id"],
        skill_ids=tuple(data["skill_ids"]),
        difficulty=data["difficulty"],
        pool=data["pool"],
        status=data["status"],
        role=data["role"],
        structure=data["structure"],
        type=data["type"],
        answer_sympy=data["answer_sympy"],
        accept=tuple(data["accept"]),
        hints=tuple((lvl, text) for lvl, text in data["hints"]),
        solution_steps=tuple(data["solution_steps"]),
        misconception_rules=tuple((m, tuple(v)) for m, v in data["misconception_rules"]),
        prediction_prompt=data["prediction_prompt"],
        authored_explanation=data["authored_explanation"],
        options=tuple(data["options"]),
        last_shown_at=None,
        slip_patterns=tuple(data["slip_patterns"]),
        prereq_signatures=tuple(data["prereq_signatures"]),
        intermediate_values=tuple(data["intermediate_values"]),
        min_plausible_ms=data["min_plausible_ms"],
        step_hints=tuple(data["step_hints"]),
        hint_restate=data["hint_restate"],
    )


PARAMS = {
    "S1": {"p_init": 0.2, "p_learn": 0.3, "p_slip": 0.1, "p_guess": 0.2},
    "S2": {"p_init": 0.2, "p_learn": 0.3, "p_slip": 0.1, "p_guess": 0.2},
    "S3": {"p_init": 0.2, "p_learn": 0.3, "p_slip": 0.1, "p_guess": 0.2},
    "SW": {"p_init": 0.2, "p_learn": 0.3, "p_slip": 0.1, "p_guess": 0.2},
}
PREREQS = {"S2": ["S1"], "S3": ["S2"], "SW": ["S2"]}
OVERLAY = ["S1", "S2", "S3", "SW"]


def ladder(skill: str, achieved: list[int], **flags: Any) -> dict[str, Any]:
    row = SkillLadder(skill_id=skill, achieved=achieved, flags=dict(flags))
    for lvl in achieved:
        row.evidence[lvl] = [f"seed-{lvl}"]
    row.lesson_done = bool(achieved)
    return row.to_json()


def build_learner(spec: dict[str, Any]) -> LearnerState:
    learner = LearnerState()
    for skill, row in (spec.get("mastery") or {}).items():
        learner.mastery[skill] = Mastery(skill_id=skill, **row)
    for skill, row in (spec.get("ladders") or {}).items():
        learner.ladders[skill] = SkillLadder.from_json(row)
    for skill, due in (spec.get("cards") or {}).items():
        learner.cards[skill] = ReviewCard(skill_id=skill, due_at=datetime.fromisoformat(due))
    return learner


def build_session(rows: list[dict[str, Any]], spec: dict[str, Any]) -> SessionState:
    session = SessionState(
        session_type="practice",
        now=NOW0,
        catalog=tuple(to_item(r) for r in rows),
        overlay_skill_ids=tuple(spec.get("overlay", OVERLAY)),
        bkt_params={k: BktParams(**v) for k, v in PARAMS.items()},
        prerequisites={k: tuple(v) for k, v in PREREQS.items()},
        allow_draft=False,
    )
    session.session_key = "fixture-session"
    session.misconception_remedial = {"MC.PREREQ": "S1"}
    session.misconception_text = {"MC.WRONG_SIDE": "You may have changed only one side."}
    session.teacher_share = bool(spec.get("teacher_share", False))
    for key, value in (spec.get("session") or {}).items():
        setattr(session, key, set(value) if key in SET_KEYS else value)
    return session


def dump_session(session: SessionState) -> dict[str, Any]:
    dumped = dump_state(session)
    out: dict[str, Any] = {}
    for key in SESSION_KEYS:
        value = dumped[key]
        out[key] = sorted(value) if key in SET_KEYS else value
    out["alerts"] = list(session.alerts)
    return deepcopy(out)  # dump_state hands out live dicts that later steps would change


def dump_learner(learner: LearnerState) -> dict[str, Any]:
    return {
        "mastery": {
            sid: {
                "p_known": m.p_known,
                "attempts": m.attempts,
                "unhinted_correct": m.unhinted_correct,
                "hinted_correct": m.hinted_correct,
            }
            for sid, m in sorted(learner.mastery.items())
        },
        "ladders": {sid: row.to_json() for sid, row in sorted(learner.ladders.items())},
        "cards": {
            sid: card.due_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M")
            for sid, card in sorted(learner.cards.items())
        },
    }


def dump_action(action: Any) -> dict[str, Any]:
    keys = [
        "type", "item_id", "skill_id", "hint_level", "misconception_id", "text", "source",
        "correct", "grade", "store_text", "llm_called", "ended_reason", "resumable",
        "guardrail_flag", "rejected", "state_before", "state_after", "rule_id", "extras",
    ]  # fmt: skip
    return deepcopy({k: getattr(action, k) for k in keys})


def resolve(event: dict[str, Any], session: SessionState) -> dict[str, Any]:
    out = dict(event)
    response = out.get("response")
    item_row = session.item(out.get("item_id")) or session.item()
    if response in ("right", "wrong") and item_row is not None:
        rows = {r["id"]: r for r in catalog()}
        row = rows[item_row.id]
        out["response"] = row["answer_sympy"] if response == "right" else row["_wrong"]
    return out


def play(name: str, steps: list[dict[str, Any]], **spec: Any) -> dict[str, Any]:
    rows = [r for r in catalog() if r["id"] not in set(spec.get("drop", ()))]
    session = build_session(rows, spec)
    learner = build_learner(spec.get("learner") or {})
    out_steps: list[dict[str, Any]] = []
    clock = NOW0
    for step in steps:
        clock = clock + timedelta(milliseconds=int(step.get("advance_ms", 0)))
        session.now = clock
        event_spec = step.get("event")
        event = None
        recorded: dict[str, Any] | None = None
        if event_spec is not None:
            recorded = resolve(event_spec, session)
            event = Event(**deepcopy(recorded))
        action = policy(learner, session, event)
        out_steps.append(
            {
                "now": clock.isoformat(),
                "event": recorded,
                "expect": {
                    "action": dump_action(action),
                    "session": dump_session(session),
                    "learner": dump_learner(learner),
                },
            }
        )
    setup_session = {k: v for k, v in (spec.get("session") or {}).items()}
    return {
        "name": name,
        "now": NOW0.isoformat(),
        "catalog": [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows],
        "overlay": list(spec.get("overlay", OVERLAY)),
        "prerequisites": PREREQS,
        "bkt_params": PARAMS,
        "misconception_remedial": {"MC.PREREQ": "S1"},
        "misconception_text": {"MC.WRONG_SIDE": "You may have changed only one side."},
        "teacher_share": bool(spec.get("teacher_share", False)),
        "session_setup": setup_session,
        "learner": spec.get("learner") or {},
        "steps": out_steps,
    }


def ev(kind: str, response: str | None = None, **extra: Any) -> dict[str, Any]:
    return {
        "event": {"type": kind, **({"response": response} if response is not None else {}), **extra}
    }


def answer(response: str, **extra: Any) -> dict[str, Any]:
    return {
        "advance_ms": 8000,
        "event": {"type": "answer", "response": response, "latency_ms": 8000, **extra},
    }


START: dict[str, Any] = {"event": None}
LEARNED = {"S1": ladder("S1", [1, 3]), "S2": ladder("S2", [1, 3]), "S3": ladder("S3", [1, 3])}
MASTERY_OK = {
    s: {"p_known": 0.5, "attempts": 3, "unhinted_correct": 2, "hinted_correct": 0}
    for s in ("S1", "S2", "S3")
}


def scenarios() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    out.append(
        play(
            "new_skill_lesson_flow",
            [START, ev("predict_response", "subtract"), ev("continue"), answer("right"),
             ev("continue"), answer("right"), ev("continue")],
        )
    )  # fmt: skip
    out.append(
        play(
            "wrong_answers_climb_to_the_reveal_and_a_similar_item",
            [START, ev("predict_response", "x"), ev("continue"), answer("wrong"), answer("wrong"),
             answer("wrong"), ev("continue"), answer("right"), ev("continue")],
        )
    )  # fmt: skip
    out.append(
        play(
            "help_asks_before_telling",
            [START, ev("predict_response", "x"), ev("continue"),
             ev("request_help"), ev("stuck_choice", "start"), ev("request_help"),
             ev("show_solution"), ev("continue"), answer("right")],
        )
    )  # fmt: skip
    out.append(
        play(
            "stuck_picker_choices",
            [START, ev("predict_response", "x"), ev("continue"),
             ev("request_help"), ev("stuck_choice", "restate"),
             ev("request_help"), ev("stuck_choice", "step"), ev("stuck_step", "1"),
             ev("request_hint"), ev("stuck_choice", "might_be_right"), answer("right")],
            learner={"mastery": MASTERY_OK, "ladders": LEARNED},
            session={"introduced_skills": ["S1", "S2", "S3"], "current_skill": "S2"},
        )
    )  # fmt: skip
    out.append(
        play(
            "picker_guardrails",
            [START, ev("stuck_choice", "start"), ev("stuck_step", "0"), ev("break_choice", "break"),
             ev("show_solution"), ev("request_help"), ev("stuck_choice", "nope"),
             ev("stuck_choice", "start"), ev("stuck_step", "x"), ev("stuck_step", "9")],
            learner={"mastery": MASTERY_OK, "ladders": LEARNED},
            session={"introduced_skills": ["S1", "S2", "S3"]},
        )
    )  # fmt: skip
    out.append(
        play(
            "misconception_hint_and_diagnosis",
            [answer("70"), answer("70"), answer("73"), answer("71"), answer("right")],
            learner={
                "mastery": {**MASTERY_OK, "S1": {"p_known": 0.9, "attempts": 4,
                                                  "unhinted_correct": 3, "hinted_correct": 0}},
                "ladders": {"S1": ladder("S1", [1, 3, 4]), "S2": ladder("S2", [1, 3]),
                            "S3": ladder("S3", [1, 3])},
            },
            session={"introduced_skills": ["S1", "S2", "S3"], "current_skill": "S2",
                     "current_item_id": "S2.c", "phase": "practice"},
        )
    )  # fmt: skip
    out.append(
        play(
            "slip_gets_check_your_work",
            [answer("5"), answer("right")],
            learner={"mastery": MASTERY_OK,
                     "ladders": {"S1": ladder("S1", [1, 3, 4]), "S2": ladder("S2", [1, 3, 4]),
                                 "S3": ladder("S3", [1, 3])}},
            session={"introduced_skills": ["S1", "S2", "S3"], "current_skill": "S2",
                     "current_item_id": "S2.c", "phase": "practice"},
        )
    )  # fmt: skip
    out.append(
        play(
            "fast_answers_offer_a_break",
            [START, ev("predict_response", "x"), ev("continue"),
             {"advance_ms": 500, "event": {"type": "answer", "response": "wrong", "latency_ms": 500}},
             {"advance_ms": 500, "event": {"type": "answer", "response": "wrong", "latency_ms": 500}},
             {"advance_ms": 500, "event": {"type": "answer", "response": "wrong", "latency_ms": 500}},
             ev("break_choice", "continue")],
        )
    )  # fmt: skip
    out.append(
        play(
            "break_choice_switch_and_break",
            [START, ev("predict_response", "x"), ev("continue"),
             {"advance_ms": 500, "event": {"type": "answer", "response": "wrong", "latency_ms": 500}},
             {"advance_ms": 500, "event": {"type": "answer", "response": "wrong", "latency_ms": 500}},
             {"advance_ms": 500, "event": {"type": "answer", "response": "wrong", "latency_ms": 500}},
             ev("break_choice", "switch")],
        )
    )  # fmt: skip
    out.append(
        play(
            "help_three_times_without_trying",
            [START, ev("predict_response", "x"), ev("continue"),
             ev("request_help"), ev("stuck_choice", "might_be_right"),
             ev("request_help"), ev("request_help")],
            learner={"mastery": MASTERY_OK, "ladders": LEARNED},
            session={"introduced_skills": ["S1", "S2", "S3"]},
        )
    )  # fmt: skip
    out.append(
        play(
            "wheel_spinning_starts_a_prerequisite_probe",
            [answer("wrong"), answer("wrong"), answer("wrong"), ev("continue"),
             answer("wrong"), answer("wrong"), answer("wrong"), ev("continue"),
             answer("wrong"), answer("wrong"), answer("wrong"), answer("right"), ev("continue")],
            teacher_share=True,
            learner={"mastery": {"S1": {"p_known": 0.5, "attempts": 3, "unhinted_correct": 2,
                                        "hinted_correct": 0}},
                     "ladders": {"S1": ladder("S1", [1, 3])}},
            session={"introduced_skills": ["S1", "S2", "S3", "SW"], "current_skill": "S2",
                     "current_item_id": "S2.b", "phase": "practice"},
        )
    )  # fmt: skip
    out.append(
        play(
            "prerequisite_gap_probe_then_scheduled_prerequisite",
            [answer("71"), answer("wrong"), answer("right"), answer("right")],
            learner={"mastery": MASTERY_OK,
                     "ladders": {"S1": ladder("S1", [1, 3]), "S2": ladder("S2", [1, 3]),
                                 "S3": ladder("S3", [1, 3])}},
            session={"introduced_skills": ["S1", "S2", "S3"], "current_skill": "S2",
                     "current_item_id": "S2.c", "phase": "practice"},
        )
    )  # fmt: skip
    out.append(
        play(
            "frustration_steps_the_tier_down",
            [START, ev("predict_response", "x"), ev("continue"),
             answer("wrong"), answer("wrong"), answer("wrong"), ev("continue"),
             answer("wrong"), answer("wrong"), answer("wrong"), ev("continue"), answer("right")],
        )
    )  # fmt: skip
    out.append(
        play(
            "three_unhinted_correct_steps_the_tier_up_then_a_challenge",
            [START, answer("right"), answer("right"), answer("right"), answer("right"),
             answer("right"), answer("right"), answer("right"), answer("right")],
            learner={"mastery": MASTERY_OK, "ladders": LEARNED},
            session={"introduced_skills": ["S1", "S2", "S3", "SW"], "explain_back_done": ["S1", "S2", "S3"]},
        )
    )  # fmt: skip
    out.append(
        play(
            "praise_after_a_hard_success_and_session_end",
            [START, answer("right"), ev("continue"), answer("right"), answer("right")],
            learner={"mastery": MASTERY_OK, "ladders": LEARNED},
            session={"introduced_skills": ["S1", "S2", "S3"], "items_completed": 9,
                     "soft_item_cap": 12, "last_praise_at": -99,
                     "explain_back_done": ["S1", "S2", "S3"]},
        )
    )  # fmt: skip
    out.append(
        play(
            "soft_cap_after_a_failure_serves_one_win",
            [START, answer("wrong"), answer("wrong"), answer("wrong"), ev("continue"), answer("right"),
             ev("continue")],
            learner={"mastery": MASTERY_OK, "ladders": LEARNED},
            session={"introduced_skills": ["S1", "S2", "S3"], "soft_active_ms": 20000},
        )
    )  # fmt: skip
    out.append(
        play(
            "explain_back_then_next_skill",
            [START, ev("predict_response", "x"), ev("continue"), answer("right"),
             ev("explain_back", text="I took the number away from both sides."), ev("continue")],
        )
    )  # fmt: skip
    out.append(
        play(
            "warmup_review_comes_first",
            [START, answer("right"), answer("wrong"), answer("right"), ev("continue")],
            learner={"mastery": MASTERY_OK, "ladders": LEARNED,
                     "cards": {"S1": "2026-10-10T09:00:00+00:00", "S2": "2026-10-11T09:00:00+00:00"}},
            session={"introduced_skills": ["S1", "S2", "S3"]},
        )
    )  # fmt: skip
    out.append(
        play(
            "stretch_item_is_served_when_due",
            [START, answer("right"), ev("continue")],
            learner={"mastery": MASTERY_OK,
                     "ladders": {"S1": ladder("S1", [1, 3, 4], stretch_after_4="2026-10-11T09:00:00+00:00"),
                                 "S2": ladder("S2", [1, 3]), "S3": ladder("S3", [1, 3])}},
            session={"introduced_skills": ["S1", "S2", "S3"], "explain_back_done": ["S1", "S2", "S3"]},
        )
    )  # fmt: skip
    out.append(
        play(
            "extension_practice_when_every_skill_is_at_level_4",
            [START, answer("right"), ev("continue"), answer("right")],
            learner={"mastery": {s: {"p_known": 0.97, "attempts": 5, "unhinted_correct": 4,
                                     "hinted_correct": 0} for s in ("S1", "S2", "S3", "SW")},
                     "ladders": {s: ladder(s, [1, 3, 4]) for s in ("S1", "S2", "S3", "SW")}},
            session={"introduced_skills": ["S1", "S2", "S3", "SW"],
                     "explain_back_done": ["S1", "S2", "S3", "SW"]},
        )
    )  # fmt: skip
    out.append(
        play(
            "a_missing_item_is_a_content_gap",
            [START, ev("predict_response", "x"), ev("continue")],
            drop=[f"SW.{x}" for x in "ab"] + [f"S3.{x}" for x in "abc"],
            overlay=["S3", "S1", "S2"],
            learner={},
        )
    )  # fmt: skip
    out.append(
        play(
            "resume_idle_nudge_and_consent",
            [START, ev("predict_response", "x"), ev("continue"),
             {"event": {"type": "idle_nudge"}},
             {"advance_ms": 61000, "event": {"type": "resume"}},
             {"advance_ms": 700000, "event": {"type": "answer", "response": "right", "latency_ms": 100}},
             {"event": {"type": "resume"}}],
        )
    )  # fmt: skip
    out.append(
        play(
            "consent_revoked_ends_the_session",
            [START, ev("predict_response", "x"), ev("consent_revoked"), ev("continue")],
        )
    )  # fmt: skip
    out.append(
        play(
            "hard_cap_ends_the_session",
            [START, ev("predict_response", "x"), ev("continue"),
             {"advance_ms": 1, "event": {"type": "answer", "response": "right", "latency_ms": 200000}},
             {"advance_ms": 1, "event": {"type": "request_help", "latency_ms": 200000}},
             {"advance_ms": 1, "event": {"type": "request_help", "latency_ms": 200000}},
             {"advance_ms": 1, "event": {"type": "request_help", "latency_ms": 200000}},
             {"advance_ms": 1, "event": {"type": "request_help", "latency_ms": 200000}}],
            session={"hard_active_ms": 700000, "soft_active_ms": 650000},
        )
    )  # fmt: skip
    out.append(
        play(
            "mcq_item_and_unknown_response",
            [answer("a"), answer("b"), answer("I don't know")],
            learner={"mastery": MASTERY_OK, "ladders": LEARNED},
            session={"introduced_skills": ["S1", "S2", "S3"], "current_skill": "S1",
                     "current_item_id": "S1.g", "phase": "practice"},
        )
    )  # fmt: skip
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.json"):
        old.unlink()
    for index, scenario in enumerate(scenarios(), start=1):
        path = OUT / f"{index:02d}_{scenario['name']}.json"
        path.write_text(json.dumps(scenario, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {index} scenarios to {OUT}")


if __name__ == "__main__":
    main()
