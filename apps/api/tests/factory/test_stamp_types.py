"""The stamp step: misconception rules, numeric and expression items, option text in the hash."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml
from sqlalchemy.orm import Session

from app.content.gate import row_is_servable, row_tier_backed
from app.content.ledger import Ledger
from app.content.loader import _factory_backing, _upsert
from app.content.math_parse import parse_math
from app.content.originality import ReferenceIndex
from app.content.schema import ContentBundle, Item, Skill
from app.content.signatures import hash_covers_option_text, item_content_hash
from app.content.validator import ValidationReport, last_step_matches_answer, validate_bundle
from app.content.verification import record_errors, tier_backed
from app.db.models import ItemRow
from app.factory.lanes.maths_quadratic import LANE, TEMPLATE
from app.factory.runner import run_item, template_hash
from app.factory.stamp import StampRefused, build_item, stamp
from tests.content.factory_fixture import SKILL, build_factory_root, item_files

PARAMS = {"a": 1, "r1": 2, "r2": 5}


def _stamped(tmp_path: Path, mutate=None) -> tuple[Item, Ledger]:
    ctx, result = run_item(LANE, TEMPLATE, PARAMS, reference_index=ReferenceIndex())
    assert result.stampable
    if mutate:
        mutate(ctx)
    ledger = Ledger(tmp_path / "factory" / "ledger.jsonl")
    data = stamp(
        ctx,
        result,
        template_id=TEMPLATE["id"],
        template_hash=template_hash(LANE, TEMPLATE),
        ledger=ledger,
        ts="2026-11-16T00:00:00+00:00",
    )
    return Item.model_validate(data), ledger


def _to_numeric(kind: str):
    def mutate(ctx) -> None:
        ctx.options, ctx.key_option = [], None
        ctx.item_type = kind
        ctx.answer_text = "x = 2" if kind == "expression" else "7"
        ctx.answer_text = "2*5" if kind == "expression" else "7"
        ctx.accept = ["10"] if kind == "expression" else []
        ctx.wrong_answers = [
            {"text": "-7", "procedure": "sign_error"},
            {"text": "2", "procedure": "one_root_only"},
            {"text": "10", "procedure": "sum_product_confusion"},
        ]

    return mutate


def test_mcq_distractor_procedures_become_misconception_rules(tmp_path: Path):
    item, _ = _stamped(tmp_path)
    assert item.type.value == "mcq"
    rules = {r.id: r.when_answer_equals for r in item.misconception_rules}
    assert set(rules) == {"sign_error", "one_root_only", "sum_product_confusion"}  # not "correct"
    options = {o.id for o in item.options}
    wrong = [a for answers in rules.values() for a in answers]
    assert sorted(wrong) == sorted(options - {item.answer.sympy})  # every wrong letter, once


def test_two_options_with_one_procedure_share_one_rule(tmp_path: Path):
    def mutate(ctx) -> None:
        ctx.options[2]["procedure"] = ctx.options[1]["procedure"]

    item, _ = _stamped(tmp_path, mutate)
    rules = [r for r in item.misconception_rules if r.id == "sign_error"]
    assert len(rules) == 1 and len(rules[0].when_answer_equals) == 2


@pytest.mark.parametrize("kind", ["numeric", "expression"])
def test_numeric_and_expression_items_stamp_with_the_schema_fields(tmp_path: Path, kind: str):
    item, ledger = _stamped(tmp_path, _to_numeric(kind))
    assert item.type.value == kind and item.tier.value == "A" and item.options == []
    parse_math(item.answer.sympy)  # the allowlist parser accepts it, as the validator requires
    assert last_step_matches_answer(
        item.solution_steps[-1].en, item.answer.sympy, item_type=item.type
    )
    assert item.answer.accept == (["10"] if kind == "expression" else [])
    assert {r.id: r.when_answer_equals for r in item.misconception_rules} == {
        "sign_error": ["-7"],
        "one_root_only": ["2"],
        "sum_product_confusion": ["10"],
    }
    assert (
        record_errors(
            item.verification.as_record(),
            item_hash=item_content_hash(item),
            stamped_hashes=ledger.stamped_record_hashes(),
        )
        == []
    )
    # the whole-bundle validator accepts it: no stem-solve needed, no legacy template needed
    skill = Skill.model_validate(
        {
            "id": SKILL,
            "title": {"en": "s"},
            "grade_band": [10],
            "subject": "maths",
            "misconceptions": [],
            "bkt": {"p_init": 0.3, "p_learn": 0.15, "p_slip": 0.1, "p_guess": 0.25},
        }
    )
    bundle = ContentBundle(
        skills=[skill], items=[item], misconceptions=[], overlays=[], glossaries=[],
        checkpoint_forms=[],
    )  # fmt: skip
    report = validate_bundle(bundle, stamped_hashes=ledger.stamped_record_hashes())
    # only the bank-size minimum (one item) and the lane-less misconception ids may complain
    assert [
        e for e in report.errors if "unknown misconception" not in e and "distinct stems" not in e
    ] == []
    assert report.needs_teacher_check == []


def test_a_numeric_item_can_carry_a_verify_spec(tmp_path: Path):
    def mutate(ctx) -> None:
        _to_numeric("numeric")(ctx)
        ctx.verify = {"kind": "equation", "expr": "x - 2 = 5", "unknown": "x"}

    item, _ = _stamped(tmp_path, mutate)
    assert item.verify.kind == "equation" and item.verify.unknown == "x"


def test_a_wrong_answer_equal_to_the_key_is_refused(tmp_path: Path):
    def mutate(ctx) -> None:
        _to_numeric("numeric")(ctx)
        ctx.wrong_answers[0]["text"] = "7"

    with pytest.raises(StampRefused):
        _stamped(tmp_path, mutate)


def test_nothing_to_stamp_is_refused():
    ctx, _ = run_item(LANE, TEMPLATE, PARAMS, reference_index=ReferenceIndex())
    ctx.options, ctx.key_option = [], None
    with pytest.raises(StampRefused):
        build_item(ctx, "T", "h")


def test_item_hash_covers_option_text_for_factory_items(tmp_path: Path):
    item, _ = _stamped(tmp_path)
    assert item.generator_version == "factory-2" and hash_covers_option_text(item)
    edited = item.model_copy(deep=True)
    edited.options[0].en = edited.options[0].en + " (edited)"
    assert item_content_hash(edited) != item_content_hash(item)
    edited_type = item.model_copy(update={"type": Item.model_fields["type"].annotation("numeric")})
    assert item_content_hash(edited_type) != item_content_hash(item)


def test_legacy_and_factory_1_hashes_keep_their_old_value(tmp_path: Path):
    item, _ = _stamped(tmp_path)
    old_style = item.model_copy(update={"generator_version": "factory-1"})
    assert not hash_covers_option_text(old_style)
    edited = old_style.model_copy(deep=True)
    edited.options[0].en = "something else"
    assert item_content_hash(edited) == item_content_hash(old_style)  # option ids only, as before
    legacy = old_style.model_copy(update={"generator_version": None})
    assert item_content_hash(legacy) == item_content_hash(old_style)
    # and the hash of a legacy item equals the pre-factory-2 formula
    import hashlib

    payload = {
        "id": legacy.id, "skill_ids": legacy.skill_ids, "stem": legacy.stem.en,
        "answer": legacy.answer.sympy, "hints": [(h.level, h.en) for h in legacy.hints],
        "steps": [s.en for s in legacy.solution_steps], "verify": None,
        "options": [o.id for o in legacy.options],
    }  # fmt: skip
    blob = json.dumps(payload, sort_keys=True, default=str)
    assert item_content_hash(legacy) == hashlib.sha256(blob.encode("utf-8")).hexdigest()


def test_editing_an_option_text_after_stamping_stops_it_being_served(db: Session, tmp_path: Path):
    root, subject = build_factory_root(tmp_path, count=1)
    path = item_files(subject)[0]
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    bundle_item = Item.model_validate(data)
    ledger_root = subject  # the lane's own ledger sits in the subject folder

    def load(item: Item) -> ItemRow:
        report = ValidationReport(bundle=None)
        bundle = ContentBundle(
            skills=[], items=[item], misconceptions=[], overlays=[], glossaries=[],
            checkpoint_forms=[],
        )  # fmt: skip
        report.bundle = bundle
        backing, _ = _factory_backing(root, report)
        assert report.errors == []
        _upsert(db, bundle, prune=False, backing=backing)
        db.commit()
        row = db.get(ItemRow, item.id)
        assert row is not None
        return row

    row = load(bundle_item)
    assert ledger_root.is_dir() and row.tier == "A" and tier_backed(row.verification, "A")
    assert row_is_servable(row, allow_draft=False, serve_tier_a_unreviewed=True)

    # (1) edited in the YAML: the loader drops the tier (record names other content)
    data2 = copy.deepcopy(data)
    data2["options"][0]["en"] = data2["options"][0]["en"] + " changed"
    row = load(Item.model_validate(data2))
    assert row.tier is None and not row_is_servable(
        row, allow_draft=False, serve_tier_a_unreviewed=True
    )

    # (2) edited in the database after loading: the serve-time check recomputes the hash
    row = load(bundle_item)
    assert row_tier_backed(row) is True
    row.options = [{**row.options[0], "en": "tampered"}, *row.options[1:]]
    db.commit()
    assert row_tier_backed(row) is False
    assert not row_is_servable(row, allow_draft=False, serve_tier_a_unreviewed=True)
