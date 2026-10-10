"""G8 step 4: template coverage for the apply and transfer roles."""

from __future__ import annotations

import pytest

from app.content.coverage import coverage_gaps, format_coverage, role_coverage
from app.content.generate import sample_instances
from app.content.leak import hint_leaks_answer
from app.content.schema import Item, ItemTemplate
from app.content.stem_solve import check_item_stem_answer
from app.content.templates import load_templates
from app.registries.paths import content_root
from app.verifier.check import verify_response

NEW = {
    "TPL.ONE.APPLY.MARBLES": ("MATH.ALG.LIN1.SOLVE_ONE_STEP", "apply"),
    "TPL.ONE.TRANSFER.REVERSED": ("MATH.ALG.LIN1.SOLVE_ONE_STEP", "transfer"),
    "TPL.TWO.APPLY.BOOKS": ("MATH.ALG.LIN1.SOLVE_TWO_STEP", "apply"),
    "TPL.TWO.TRANSFER.REVERSED": ("MATH.ALG.LIN1.SOLVE_TWO_STEP", "transfer"),
}


@pytest.fixture(scope="module")
def templates() -> list[ItemTemplate]:
    return load_templates(content_root())


def _template(skill: str, role: str) -> ItemTemplate:
    return ItemTemplate.model_validate(
        {
            "id": f"TPL.T.{role}",
            "skill_id": skill,
            "role": role,
            "structure": "x",
            "parameters": {"x": {"min": 2, "max": 9}},
            "derived": {},
            "answer_expr": "x",
            "stem": "Solve for x: x + 1 = {x}",
            "verify": "x + 1 = {x}",
            "type": "expression",
            "options": [],
            "prediction": "p",
            "steps": ["s"],
            "hints": {"1": "a", "2": "b", "3": "c"},
            "tier_rules": [{"tier": "hard", "difficulty": 0.9}],
        }
    )


def test_a_skill_with_templates_but_no_apply_or_transfer_is_reported() -> None:
    gaps = coverage_gaps([_template("S.ONE", "procedure")], [])
    assert gaps == ["S.ONE has no apply or transfer template"]


def test_each_missing_role_is_named_and_a_full_skill_is_clean() -> None:
    only_apply = [_template("S.ONE", "procedure"), _template("S.ONE", "apply")]
    assert coverage_gaps(only_apply, []) == ["S.ONE has no transfer template"]
    full = [*only_apply, _template("S.ONE", "transfer")]
    assert coverage_gaps(full, []) == []
    assert coverage_gaps([], []) == []  # a skill with no templates at all is not a template gap


def test_role_coverage_counts_templates_and_items_by_role(templates: list[ItemTemplate]) -> None:
    table = role_coverage(templates, [])
    assert table["MATH.ALG.LIN1.SOLVE_ONE_STEP"]["apply"].templates == 1
    assert table["MATH.ALG.LIN1.SOLVE_ONE_STEP"]["transfer"].templates == 1
    assert "gaps" not in format_coverage(templates, []).lower().split("\n")[0]


def test_the_shipped_one_and_two_step_skills_now_cover_both_roles(
    templates: list[ItemTemplate],
) -> None:
    gaps = coverage_gaps(templates, [])
    assert not any("SOLVE_ONE_STEP" in g or "SOLVE_TWO_STEP" in g for g in gaps)
    by_id = {t.id: t for t in templates}
    for tid, (skill, role) in NEW.items():
        assert by_id[tid].skill_id == skill and by_id[tid].role.value == role
        assert by_id[tid].status.value == "draft"  # new content is draft until a teacher approves


@pytest.mark.parametrize("tid", sorted(NEW))
def test_every_new_template_generates_solvable_leak_free_items(
    templates: list[ItemTemplate], tid: str
) -> None:
    template = next(t for t in templates if t.id == tid)
    samples: list[Item] = sample_instances(template, seed=7, n=8)
    assert len(samples) == 8, "template should produce plenty of distinct items"
    for item in samples:
        assert check_item_stem_answer(item) in (None, "manual", "teacher")
        assert verify_response(
            item.answer.sympy, answer_sympy=item.answer.sympy, accept=item.answer.accept
        )
        for hint in item.hints[:2]:
            assert not hint_leaks_answer(hint.en, item.answer.sympy)
