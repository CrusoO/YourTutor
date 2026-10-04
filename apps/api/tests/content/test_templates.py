from __future__ import annotations

from pathlib import Path

import yaml

from app.content.generate import eval_formula, generate_instances, instantiate, sample_instances
from app.content.signatures import structure_signature
from app.content.template_catalog import builtin_templates
from app.content.templates import GENERATOR_VERSION, template_hash, write_template
from app.content.validator import validate_path
from tests.content.conftest import loc, minimal_item, minimal_skill, write_yaml


def test_generation_is_deterministic() -> None:
    templates = builtin_templates()
    first = generate_instances(templates, seed=42, existing_stems=set(), per_skill=20)
    second = generate_instances(templates, seed=42, existing_stems=set(), per_skill=20)
    assert [item.id for item in first] == [item.id for item in second]
    assert [item.stem.en for item in first] == [item.stem.en for item in second]
    other = generate_instances(templates, seed=43, existing_stems=set(), per_skill=20)
    assert [item.stem.en for item in first] != [item.stem.en for item in other]


def test_constraints_and_misconception_formulas() -> None:
    add = next(tpl for tpl in builtin_templates() if tpl.id == "TPL.ONE.ADD")
    item = instantiate(add, {"b": 5, "x": 4}, seed=1, index=0)
    assert item.answer.sympy == "4"
    assert "1x" not in item.stem.en
    assert item.stem.en == "Solve for x: x + 5 = 9"
    wrong = eval_formula("c + b", {"b": 5, "c": 9, "x": 4})
    assert str(wrong) == item.misconception_rules[0].when_answer_equals[0]
    assert wrong != 4
    try:
        instantiate(add, {"b": 0, "x": 4}, seed=1, index=1)
    except ValueError:
        pass


def test_checkpoint_stems_do_not_collide_with_generated(tmp_path: Path) -> None:
    write_yaml(tmp_path / "skills" / "s1.yaml", minimal_skill("MATH.ALG.LIN1.SOLVE_ONE_STEP"))
    write_yaml(
        tmp_path / "misconceptions" / "m1.yaml",
        {
            "id": "MC.ALG.INVERSE_OP_WRONG_SIDE",
            "title": loc("Wrong inverse"),
            "explanation": loc("Undo by doing the opposite."),
            "remedial_skill": "MATH.ALG.LIN1.SOLVE_ONE_STEP",
            "status": "draft",
        },
    )
    add = next(tpl for tpl in builtin_templates() if tpl.id == "TPL.ONE.ADD")
    write_template(tmp_path, add)
    generated = generate_instances([add], seed=7, existing_stems=set(), per_skill=20)
    for item in generated:
        write_yaml(
            tmp_path / "items" / f"{item.id}.yaml",
            item.model_dump(mode="json", by_alias=True, exclude_none=True),
        )
    practice_structs = {structure_signature(item.stem.en) for item in generated}
    transfer = "Find x given that 11 equals 2x plus 3."
    assert structure_signature(transfer) not in practice_structs
    write_yaml(
        tmp_path / "items" / "cp.yaml",
        minimal_item(
            "ITEM.CP.TRANSFER",
            skill="MATH.ALG.LIN1.SOLVE_ONE_STEP",
            pool="checkpoint",
            stem=transfer,
            answer="4",
        ),
    )
    report = validate_path(tmp_path)
    assert not any("collides with a practice stem" in err for err in report.errors)


def test_approval_inheritance_and_reset(tmp_path: Path) -> None:
    write_yaml(tmp_path / "skills" / "s1.yaml", minimal_skill("MATH.ALG.LIN1.SOLVE_ONE_STEP"))
    write_yaml(
        tmp_path / "misconceptions" / "m1.yaml",
        {
            "id": "MC.ALG.INVERSE_OP_WRONG_SIDE",
            "title": loc("Wrong inverse"),
            "explanation": loc("Undo by doing the opposite."),
            "remedial_skill": "MATH.ALG.LIN1.SOLVE_ONE_STEP",
            "status": "draft",
        },
    )
    add = next(tpl for tpl in builtin_templates() if tpl.id == "TPL.ONE.ADD")
    add.status = type(add.status)("approved")
    add.reviewed_by = "teacher.demo"
    add.content_hash = template_hash(add)
    write_template(tmp_path, add)
    item = instantiate(add, {"b": 5, "x": 4}, seed=1, index=0)
    item.status = type(item.status)("approved")
    item.reviewed_by = "teacher.demo"
    write_yaml(
        tmp_path / "items" / f"{item.id}.yaml",
        item.model_dump(mode="json", by_alias=True, exclude_none=True),
    )
    report = validate_path(tmp_path)
    inherited = next(row for row in report.bundle.items if row.id == item.id)
    assert inherited.status.value == "approved"
    assert inherited.generator_version == GENERATOR_VERSION

    path = next((tmp_path / "templates").rglob("*.yaml"))
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["stem"] = "Solve for x: x + {b} = {c} now"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    reset = validate_path(tmp_path)
    changed = next(row for row in reset.bundle.items if row.id == item.id)
    assert changed.status.value == "draft"
    assert any("reset to draft" in warning for warning in reset.warnings)


def test_sample_sheet_has_ten_instances() -> None:
    add = next(tpl for tpl in builtin_templates() if tpl.id == "TPL.ONE.ADD")
    samples = sample_instances(add, seed=9, n=10)
    assert len(samples) == 10
    assert len({row.stem.en for row in samples}) == 10
