"""Placement diagnostic planner. Pure: no I/O."""

from __future__ import annotations

from app.content.math_parse import normalize
from app.learner.bkt import BktParams
from app.learner.mastery_service import apply_event
from app.learner.types import LearnerEvent, LearnerState, Mastery
from app.orchestrator.types import CatalogItem, SessionState

DIAG_ITEM_CAP = 16
DIAG_ACTIVE_MS = 15 * 60 * 1000
LOW_PRIOR = 0.05
DONT_KNOW = frozenset(
    {
        "i don't know",
        "i dont know",
        "don't know",
        "dont know",
        "idk",
        "i do not know",
    }
)


def is_dont_know(response: str | None) -> bool:
    if not response:
        return False
    return normalize(response).lower() in DONT_KNOW


def dependents_of(skill_id: str, prerequisites: dict[str, tuple[str, ...]]) -> set[str]:
    found = {skill_id}
    changed = True
    while changed:
        changed = False
        for sid, prereqs in prerequisites.items():
            if sid in found:
                continue
            if any(p in found for p in prereqs):
                found.add(sid)
                changed = True
    found.discard(skill_id)
    return found


def first_result(session: SessionState, skill_id: str) -> dict | None:
    for row in session.diagnostic_results:
        if row["skill_id"] == skill_id:
            return row
    return None


def skill_attempts(session: SessionState, skill_id: str) -> list[dict]:
    return [row for row in session.diagnostic_results if row["skill_id"] == skill_id]


def prereqs_answered_correctly(session: SessionState, skill_id: str) -> bool:
    prereqs = session.prerequisites.get(skill_id, ())
    if not prereqs:
        return True
    for prereq in prereqs:
        first = first_result(session, prereq)
        if first is None or not first["correct"]:
            return False
    return True


def should_offer_second(session: SessionState, skill_id: str, first_correct: bool) -> bool:
    return (not first_correct) and prereqs_answered_correctly(session, skill_id)


def diagnostic_pool(session: SessionState, skill_id: str) -> list[CatalogItem]:
    return [
        row
        for row in session.catalog
        if row.pool == "diagnostic"
        and row.primary_skill == skill_id
        and (row.status == "approved" or session.allow_draft)
    ]


def pick_unused(session: SessionState, skill_id: str) -> CatalogItem | None:
    seen = {row["item_id"] for row in session.diagnostic_results}
    seen.update(session.shown_item_ids)
    for row in diagnostic_pool(session, skill_id):
        if row.id not in seen:
            return row
    return None


def next_diagnostic_item(session: SessionState) -> CatalogItem | None:
    if session.items_completed >= DIAG_ITEM_CAP or session.active_ms >= DIAG_ACTIVE_MS:
        return None
    current = session.current_skill
    if current and current not in session.skipped_skills:
        attempts = skill_attempts(session, current)
        if len(attempts) == 1 and should_offer_second(session, current, attempts[0]["correct"]):
            nxt = pick_unused(session, current)
            if nxt is not None:
                return nxt
    for skill_id in session.overlay_skill_ids:
        if skill_id in session.skipped_skills:
            continue
        if first_result(session, skill_id) is not None:
            continue
        nxt = pick_unused(session, skill_id)
        if nxt is not None:
            return nxt
    return None


def record_answer(
    session: SessionState, item: CatalogItem, *, correct: bool, dont_know: bool
) -> None:
    session.diagnostic_results.append(
        {
            "item_id": item.id,
            "skill_id": item.primary_skill,
            "correct": correct,
            "dont_know": dont_know,
        }
    )
    session.items_completed += 1
    attempts = skill_attempts(session, item.primary_skill)
    if len(attempts) >= 2 and not any(row["correct"] for row in attempts):
        for dep in dependents_of(item.primary_skill, session.prerequisites):
            session.skipped_skills.add(dep)


def seed_placement(learner: LearnerState, session: SessionState) -> None:
    tested: dict[str, list[dict]] = {}
    for row in session.diagnostic_results:
        tested.setdefault(row["skill_id"], []).append(row)
    session.skills_not_tested = [
        sid
        for sid in session.overlay_skill_ids
        if sid not in tested
    ]
    params_all = {
        sid: session.bkt_params.get(sid, BktParams(0.2, 0.15, 0.1, 0.2))
        for sid in session.overlay_skill_ids
    }
    memory: dict = {
        "bkt_done": set(),
        "hinted": set(),
        "first_wrong": set(),
        "session_unhinted": {},
        "warmup_skills": set(),
    }
    for skill_id, rows in tested.items():
        first = rows[0]
        params = params_all[skill_id]
        if first["dont_know"]:
            params = BktParams(
                p_init=params.p_init,
                p_learn=params.p_learn,
                p_slip=params.p_slip,
                p_guess=0.0,
            )
        apply_event(
            learner,
            LearnerEvent(
                item_id=first["item_id"],
                skill_id=skill_id,
                event_type="answer",
                correct=first["correct"],
                pool="diagnostic",
                session_id=str(id(session)),
            ),
            {skill_id: params},
            memory=memory,
        )
    for skill_id in session.skipped_skills:
        if skill_id in tested:
            continue
        params = params_all.get(skill_id, BktParams(0.2, 0.15, 0.1, 0.2))
        learner.mastery[skill_id] = Mastery(skill_id=skill_id, p_known=LOW_PRIOR)
        _ = params
