"""Source register rules, serving tiers and labels. Pure functions, no database."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.content.gate import tier_is_servable
from app.content.labels import (
    FOOTER_DISCLAIMER,
    PATTERN_TAG_TEMPLATE,
    QUESTION_LABEL,
    VERIFICATION_BADGE,
    item_labels,
    pattern_tag,
)
from app.content.schema import Item
from app.content.sources import SourceRow, load_register, register_errors, rights_errors
from tests.content.conftest import minimal_item, write_yaml


def row(**over: object) -> SourceRow:
    base: dict[str, object] = {
        "id": "src-open",
        "name": "Invented open source",
        "licence_id": "CC-BY",
        "commercial_ok": True,
        "derivatives_ok": True,
        "share_alike": False,
        "attribution_text": "Invented attribution.",
        "checked_on": "2026-11-11",
        "derived_item_ids": [],
    }
    base.update(over)
    return SourceRow.model_validate(base)


def item(item_id: str = "ITEM.1", **prov: object) -> Item:
    data = minimal_item(item_id)
    data["provenance"] = prov
    return Item.model_validate(data)


def test_item_referencing_unknown_source_fails() -> None:
    errors = register_errors([row()], [item(source_id="nope")])
    assert any("not in the source register" in e for e in errors)


def test_valid_reference_passes_when_listed() -> None:
    errors = register_errors([row(derived_item_ids=["ITEM.1"])], [item(source_id="src-open")])
    assert errors == []


def test_reference_missing_from_derived_list_fails() -> None:
    errors = register_errors([row()], [item(source_id="src-open")])
    assert any("missing from its derived_item_ids" in e for e in errors)


def test_register_lists_item_that_does_not_cite_it() -> None:
    errors = register_errors([row(derived_item_ids=["ITEM.1"])], [item(original=True)])
    assert any("does not cite it" in e for e in errors)


def test_disallowed_source_cannot_be_referenced() -> None:
    banned = row(
        id="banned",
        allowed=False,
        pool="excluded",
        commercial_ok=False,
        reason="invented reason",
        derived_item_ids=["ITEM.1"],
    )
    errors = register_errors([banned], [item(source_id="banned")])
    assert any("is not allowed" in e for e in errors)
    assert any("commercial" in e for e in errors)


def test_retired_item_may_still_name_a_banned_source() -> None:
    banned = row(id="banned", allowed=False, pool="excluded", commercial_ok=False, reason="x")
    data = minimal_item("ITEM.1")
    data["status"] = "retired"
    data["provenance"] = {"source_id": "banned"}
    assert register_errors([banned], [Item.model_validate(data)]) == []


def test_referenced_source_needs_checked_on() -> None:
    errors = register_errors(
        [row(checked_on=None, derived_item_ids=["ITEM.1"])], [item(source_id="src-open")]
    )
    assert any("no checked_on" in e for e in errors)


def test_share_alike_item_cannot_be_original() -> None:
    sa = row(id="sa", share_alike=True, pool="share_alike", derived_item_ids=["ITEM.1"])
    errors = register_errors([sa], [item(source_id="sa", original=True)])
    assert any("cannot be original" in e for e in errors)
    assert register_errors([sa], [item(source_id="sa", original=False)]) == []


def test_pool_and_share_alike_flag_must_agree() -> None:
    errors = register_errors([row(share_alike=True, pool="main")], [])
    assert any("must go together" in e for e in errors)


def test_disallowed_row_needs_reason() -> None:
    errors = register_errors([row(allowed=False, pool="excluded", commercial_ok=False)], [])
    assert any("no reason" in e for e in errors)


def test_duplicate_ids() -> None:
    assert any("duplicate" in e for e in register_errors([row(), row()], []))


def test_unknown_register_field_is_rejected() -> None:
    with pytest.raises(ValueError):
        SourceRow.model_validate({"id": "x", "name": "n", "stem": "no"})


def test_shipped_register_loads_and_every_row_is_unverified() -> None:
    root = Path(__file__).resolve().parents[4] / "content"
    rows = load_register(root)
    ids = {r.id for r in rows}
    assert {"oak-collection-2", "gsm8k", "ncert", "openstax", "cbse-papers"} <= ids
    assert all(r.unverified for r in rows)
    assert register_errors(rows, []) == []
    for banned in ("ncert", "diksha", "openstax", "khan-academy", "ck-12", "cbse-papers"):
        assert next(r for r in rows if r.id == banned).allowed is False


def test_rights_errors_reads_the_file(tmp_path: Path) -> None:
    write_yaml(
        tmp_path / "rights" / "register.yaml",
        {
            "sources": [
                {
                    "id": "s",
                    "name": "n",
                    "licence_id": "L",
                    "commercial_ok": True,
                    "derivatives_ok": True,
                    "share_alike": False,
                }
            ]
        },
    )
    assert rights_errors(tmp_path, [item(source_id="s")]) != []
    (tmp_path / "rights" / "register.yaml").write_text("sources: 3", encoding="utf-8")
    assert rights_errors(tmp_path, [])[0].startswith("source register:")
    assert rights_errors(tmp_path / "empty", []) == []


# --- serving tiers -------------------------------------------------------------------------


def serve(**over: object) -> bool:
    base: dict[str, object] = {
        "status": "draft",
        "tier": "A",
        "reviewed_by": None,
        "original": True,
        "allow_draft": False,
        "serve_tier_a_unreviewed": False,
    }
    base.update(over)
    return tier_is_servable(**base)  # type: ignore[arg-type]


def test_tier_a_draft_needs_the_switch() -> None:
    assert serve() is False
    assert serve(serve_tier_a_unreviewed=True) is True


def test_tier_a_unreviewed_must_be_original() -> None:
    assert serve(serve_tier_a_unreviewed=True, original=False) is False


def test_tier_c_is_never_served_except_in_dev() -> None:
    assert serve(tier="C", status="approved", serve_tier_a_unreviewed=True) is False
    assert serve(tier="C", allow_draft=True) is True


def test_tier_b_needs_a_recorded_reviewer() -> None:
    assert serve(tier="B", status="approved") is False
    assert serve(tier="B", status="approved", reviewed_by="teacher") is True
    assert serve(tier="B", status="draft", reviewed_by="teacher") is True
    assert serve(tier="B", status="draft") is False


def test_legacy_items_keep_the_status_rule() -> None:
    assert serve(tier=None, status="approved", reviewed_by="x") is True
    assert serve(tier=None, status="draft", serve_tier_a_unreviewed=True) is False


def test_retired_never_served() -> None:
    assert serve(status="retired", allow_draft=True) is False


# --- labels --------------------------------------------------------------------------------


def test_label_strings_are_exact() -> None:
    assert QUESTION_LABEL == (
        "Original Brownie practice question. Aligned to the CBSE Class 10 syllabus (2026-27). "
        "Not an official CBSE or NCERT question."
    )
    assert VERIFICATION_BADGE == "Answer checked by calculation"
    assert PATTERN_TAG_TEMPLATE == (
        "Question type seen in CBSE Class 10 board papers: {marks}-mark {type} ({years})."
    )
    assert FOOTER_DISCLAIMER.endswith("Official papers: cbseacademic.nic.in.")
    assert "Nepal's CDC or NEB" in FOOTER_DISCLAIMER


def test_pattern_tag() -> None:
    assert pattern_tag(3, "short", [2024, 2023, 2024]) == (
        "Question type seen in CBSE Class 10 board papers: 3-mark short (2023, 2024)."
    )
    assert "assertion reason" in pattern_tag(1, "assertion_reason", [2025])


def test_labels_only_for_original_tier_a_practice() -> None:
    ok = item_labels(pool="practice", tier="A", original=True, reviewed=False, pattern=None)
    assert ok == {"question": QUESTION_LABEL, "badge": VERIFICATION_BADGE}
    assert (
        item_labels(pool="practice", tier="B", original=True, reviewed=True, pattern=None) is None
    )
    assert (
        item_labels(pool="practice", tier="A", original=False, reviewed=True, pattern=None) is None
    )
    assert (
        item_labels(pool="diagnostic", tier="A", original=True, reviewed=True, pattern=None) is None
    )
    full = item_labels(pool="practice", tier="A", original=True, reviewed=True, pattern="tag")
    assert full is not None and full["pattern"] == "tag" and "reviewed" in full


def test_content_validate_fails_on_a_bad_source_reference(content_root: Path) -> None:
    from app.content.validator import validate_path

    assert validate_path(content_root).errors == []
    data = minimal_item("ITEM.P0", stem="Solve for x: x + 7 = 12")
    data["provenance"] = {"source_id": "ncert"}
    write_yaml(content_root / "items" / "p0.yaml", data)
    errors = validate_path(content_root).errors
    assert any("ITEM.P0" in e and "source register" in e for e in errors)
