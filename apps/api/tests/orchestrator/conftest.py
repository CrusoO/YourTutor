from __future__ import annotations

from datetime import UTC, datetime

from app.learner.ladder import SkillLadder
from app.learner.types import LearnerState, Mastery, ReviewCard
from app.orchestrator.types import CatalogItem, SessionState, default_params

NOW = datetime(2026, 10, 2, 12, 0, tzinfo=UTC)


def catalog_item(
    item_id: str = "ITEM.A",
    *,
    skill: str = "MATH.S1",
    difficulty: float = 0.3,
    pool: str = "practice",
    status: str = "approved",
    answer: str = "5",
    extra_skill: str | None = None,
    last_shown_at: datetime | None = None,
    rules: tuple[tuple[str, tuple[str, ...]], ...] = (),
) -> CatalogItem:
    skills = (skill,) if extra_skill is None else (skill, extra_skill)
    return CatalogItem(
        id=item_id,
        skill_ids=skills,
        difficulty=difficulty,
        pool=pool,
        status=status,
        type="expression",
        answer_sympy=answer,
        accept=(answer, f"x={answer}"),
        hints=(
            (1, "What undoes the operation?"),
            (2, "Do the same to both sides."),
            (3, "Subtract 7 from both sides."),
        ),
        solution_steps=(f"x = {answer}",),
        misconception_rules=rules,
        prediction_prompt="Will x be smaller than 12?",
        authored_explanation="Subtract the same number from both sides.",
        verify="x + 7 = 12" if answer == "5" else None,
        last_shown_at=last_shown_at,
    )


def make_session(
    *items: CatalogItem,
    session_type: str = "practice",
    overlay: tuple[str, ...] = ("MATH.S1",),
    prereqs: dict[str, tuple[str, ...]] | None = None,
    introduced: set[str] | None = None,
    allow_draft: bool = False,
) -> SessionState:
    catalog = items or (catalog_item(),)
    return SessionState(
        session_type=session_type,
        now=NOW,
        catalog=catalog,
        overlay_skill_ids=overlay,
        bkt_params={sid: default_params() for sid in overlay},
        prerequisites=prereqs or {},
        introduced_skills=set(introduced or ()),
        last_active_at=NOW,
        allow_draft=allow_draft,
        diagnostic_ids=[i.id for i in catalog if i.pool == "diagnostic"],
        checkpoint_ids=[i.id for i in catalog if i.pool == "checkpoint"],
    )


def make_learner(*, p_known: dict[str, float] | None = None) -> LearnerState:
    """v2: T follows the ladder, so a skill fixture with p_known >= 0.95 stands for a skill that
    already reached level 4 (the v1 mastery threshold)."""
    state = LearnerState()
    for skill_id, value in (p_known or {}).items():
        state.mastery[skill_id] = Mastery(skill_id=skill_id, p_known=value)
        if value >= 0.95:
            state.ladders[skill_id] = SkillLadder(skill_id=skill_id, achieved=[3, 4])
    return state


def due_card(skill_id: str, *, due: datetime | None = None) -> ReviewCard:
    return ReviewCard(skill_id=skill_id, due_at=due or NOW)
