from __future__ import annotations

from pathlib import Path

from app.content.signatures import structure_signature
from app.content.validator import load_bundle
from app.learner.bkt import BktParams
from app.orchestrator.types import CatalogItem, SessionState, default_params
from tests.orchestrator.conftest import NOW

CONTENT = Path(__file__).resolve().parents[4] / "content"


def seed_catalog() -> tuple[CatalogItem, ...]:
    bundle = load_bundle(CONTENT)
    rows = []
    for item in bundle.items:
        rows.append(
            CatalogItem(
                id=item.id,
                skill_ids=tuple(item.skill_ids),
                difficulty=item.difficulty,
                pool=item.pool.value,
                status=item.status.value,
                role=item.role.value,
                structure=structure_signature(item.stem.en),
                type=item.type.value,
                answer_sympy=item.answer.sympy,
                accept=tuple(item.answer.accept),
                hints=tuple((h.level, h.en) for h in item.hints),
                solution_steps=tuple(s.en for s in item.solution_steps),
                misconception_rules=tuple(
                    (r.id, tuple(r.when_answer_equals)) for r in item.misconception_rules
                ),
                prediction_prompt=item.prediction_prompt.en,
                authored_explanation=item.solution_steps[0].en if item.solution_steps else "",
                verify=item.verify
                if isinstance(item.verify, str)
                else (item.verify.model_dump() if item.verify else None),
                options=tuple(o.model_dump(by_alias=True) for o in item.options),
            )
        )
    return tuple(rows)


def seed_session(catalog: tuple[CatalogItem, ...]) -> SessionState:
    bundle = load_bundle(CONTENT)
    overlay = tuple(skill.id for skill in bundle.skills)
    params = {sid: default_params() for sid in overlay}
    prereqs: dict[str, tuple[str, ...]] = {}
    for skill in bundle.skills:
        params[skill.id] = BktParams(**skill.bkt.model_dump())
        prereqs[skill.id] = tuple(skill.prerequisites)
    return SessionState(
        session_type="practice",
        now=NOW,
        catalog=catalog,
        overlay_skill_ids=overlay,
        bkt_params=params,
        prerequisites=prereqs,
        allow_draft=True,
        last_active_at=NOW,
    )
