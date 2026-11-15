"""Tier A can no longer be typed by hand: it needs an intact, ledger-backed verification record."""

from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.content.gate import row_is_servable, row_tier_backed, tier_is_servable
from app.content.labels import FACTORY_LABEL_TEXT, item_labels
from app.content.ledger import Ledger
from app.content.schema import Item, VerificationRecord
from app.content.signatures import item_content_hash
from app.content.verification import (
    FORBIDDEN_LABELS,
    HONEST_LABELS,
    effective_tier,
    record_errors,
    record_hash,
    tier_backed,
)

BASE_ITEM = {
    "id": "ITEM.F.1",
    "skill_ids": ["S.1"],
    "difficulty": 0.5,
    "type": "mcq",
    "pool": "practice",
    "role": "apply",
    "stem": {"en": "Which is right?"},
    "options": [{"id": "a", "en": "x"}, {"id": "b", "en": "y"}],
    "answer": {"sympy": "a"},
    "solution_steps": [{"en": "Think."}, {"en": "The correct option is a."}],
    "hints": [{"level": i, "en": f"hint {i}"} for i in (1, 2, 3)],
    "prediction_prompt": {"en": "Guess?"},
    "status": "draft",
    "provenance": {"original": True},
}


def make_record(item_hash: str, **over) -> dict:
    record = {
        "schema": "vrec/1", "item_hash": item_hash, "template_hash": "t", "certificate_hash": "c",
        "label": "calculation-checked", "tier": "A", "stamped_at": "2026-11-16T00:00:00+00:00",
        **over,
    }  # fmt: skip
    record["record_hash"] = record_hash(record)
    return record


@pytest.fixture
def stamped(tmp_path: Path):
    """An item with a record that really is in an intact ledger."""
    item = Item.model_validate(BASE_ITEM)
    record = make_record(item_content_hash(item))
    ledger = Ledger(tmp_path / "ledger.jsonl")
    ledger.append(
        "stamped", item.id, record["item_hash"], {"record_hash": record["record_hash"]}, ts="t"
    )
    return item, record, ledger.stamped_record_hashes()


def serve(**kw) -> bool:
    base = {
        "status": "draft", "tier": "A", "reviewed_by": None, "original": True,
        "allow_draft": False, "serve_tier_a_unreviewed": True,
    }  # fmt: skip
    return tier_is_servable(**{**base, **kw})


# ---- the gate ---------------------------------------------------------------------------


def test_legacy_calls_keep_todays_rule():
    assert serve() is True  # tier_backed not given: the old behaviour, unchanged
    assert serve(serve_tier_a_unreviewed=False) is False
    assert serve(tier=None, status="approved") is True


def test_hand_typed_tier_a_is_not_served():
    assert serve(tier_backed=False) is False
    assert serve(tier_backed=False, status="approved") is True  # a person approved it: status rule
    assert serve(tier_backed=False, allow_draft=True) is True  # development shows everything


def test_stamped_tier_a_needs_the_switch_and_original_provenance():
    assert serve(tier_backed=True) is True
    assert serve(tier_backed=True, serve_tier_a_unreviewed=False) is False
    assert serve(tier_backed=True, original=False) is False


def test_suspended_is_never_served():
    for status in ("draft", "approved"):
        assert serve(tier_backed=True, status=status, suspended=True) is False
    assert serve(tier_backed=True, suspended=True, allow_draft=True) is False
    assert serve(tier=None, status="approved", suspended=True) is False
    assert serve(tier="C", suspended=True, allow_draft=True) is False


def test_tier_b_stands_on_a_recorded_reviewer_or_a_record():
    assert serve(tier="B", reviewed_by="teacher", tier_backed=False) is True
    assert serve(tier="B", tier_backed=False) is False
    assert serve(tier="B", tier_backed=True, reviewed_by="teacher") is True


def test_tier_c_still_blocks():
    assert serve(tier="C", tier_backed=None, status="approved") is False


# ---- rows -------------------------------------------------------------------------------


def row(**over):
    base = {
        "status": "draft", "tier": "A", "reviewed_by": None, "provenance": {"original": True},
        "verification": None, "suspended_at": None,
    }  # fmt: skip
    return SimpleNamespace(**{**base, **over})


def test_row_without_record_is_not_served_but_with_one_it_is(stamped):
    _, record, _ = stamped
    assert row_is_servable(row(), allow_draft=False, serve_tier_a_unreviewed=True) is False
    good = row(verification=record)
    assert row_tier_backed(good) is True
    assert row_is_servable(good, allow_draft=False, serve_tier_a_unreviewed=True) is True
    assert row_is_servable(good, allow_draft=False, serve_tier_a_unreviewed=False) is False


def test_row_with_edited_record_or_wrong_tier_is_ignored(stamped):
    _, record, _ = stamped
    edited = {**record, "methods_agreeing": ["x"]}  # contents no longer match record_hash
    assert row_tier_backed(row(verification=edited)) is False
    assert row_tier_backed(row(tier="B", verification=record)) is False  # record says A
    assert row_tier_backed(row(tier=None)) is None


def test_suspended_row_is_not_served(stamped):
    _, record, _ = stamped
    from datetime import UTC, datetime

    gone = row(verification=record, suspended_at=datetime.now(UTC))
    assert row_is_servable(gone, allow_draft=False, serve_tier_a_unreviewed=True) is False
    assert row_is_servable(gone, allow_draft=True, serve_tier_a_unreviewed=True) is False


# ---- the loader's rule ------------------------------------------------------------------


def test_hand_written_tier_a_is_ignored_with_a_reason():
    item = Item.model_validate({**BASE_ITEM, "tier": "A"})
    tier, why = effective_tier("A", None, item_hash=item_content_hash(item),
                               stamped_hashes=set(), reviewed_by=None)  # fmt: skip
    assert tier is None and "without a verification record" in why


def test_a_self_made_record_that_is_not_in_the_ledger_is_ignored(stamped):
    item, _, _ = stamped
    forged = make_record(item_content_hash(item), certificate_hash="forged")
    tier, why = effective_tier("A", forged, item_hash=item_content_hash(item),
                               stamped_hashes=set(), reviewed_by=None)  # fmt: skip
    assert tier is None and "not in the stamp ledger" in why


def test_record_backs_the_tier_only_for_unchanged_content(stamped):
    item, record, hashes = stamped
    args = {"stamped_hashes": hashes, "reviewed_by": None}
    assert effective_tier("A", record, item_hash=item_content_hash(item), **args) == ("A", None)
    changed = Item.model_validate({**BASE_ITEM, "stem": {"en": "A different question?"}})
    tier, why = effective_tier("A", record, item_hash=item_content_hash(changed), **args)
    assert tier is None and "different item content" in why
    tier, why = effective_tier("B", record, item_hash=item_content_hash(item), **args)
    assert tier is None  # the record says A, not B


def test_tier_c_and_none_pass_through():
    for tier in (None, "C"):
        assert effective_tier(
            tier, None, item_hash="h", stamped_hashes=set(), reviewed_by=None
        ) == (tier, None)


# ---- records and labels -----------------------------------------------------------------


def test_the_factory_cannot_emit_human_or_teacher_labels():
    for label in FORBIDDEN_LABELS:
        with pytest.raises(ValidationError):
            VerificationRecord.model_validate(make_record("h", label=label))
        assert any(
            "only be granted by a person" in e for e in record_errors(make_record("h", label=label))
        )
    assert set(HONEST_LABELS) == set(FACTORY_LABEL_TEXT)
    assert not any(
        w in text.lower()
        for text in FACTORY_LABEL_TEXT.values()
        for w in ("teacher", "human", "reviewed")
    )


def test_record_schema_is_strict():
    ok = make_record("h")
    VerificationRecord.model_validate(ok)
    with pytest.raises(ValidationError):
        VerificationRecord.model_validate({**ok, "reviewer": "ms sharma"})  # no invented reviewer
    with pytest.raises(ValidationError):
        VerificationRecord.model_validate({**ok, "tier": "B"})  # tier follows the label
    assert record_errors(None) == ["no verification record"]
    assert record_errors({**ok, "schema": "vrec/9"})


def test_tier_backed_helper(stamped):
    _, record, _ = stamped
    assert tier_backed(record, "A") and not tier_backed(record, "B") and not tier_backed(None, "A")
    bad = copy.deepcopy(record)
    bad["lane"] = "x"
    assert not tier_backed(bad, "A")


def test_labels_carry_the_honest_sentence_only_for_stamped_items():
    plain = item_labels(pool="practice", tier="A", original=True, reviewed=False, pattern=None)
    assert plain is not None and "verification" not in plain
    full = item_labels(
        pool="practice", tier="A", original=True, reviewed=False, pattern=None,
        verification_label="calculation-checked",
    )  # fmt: skip
    assert full["verification"] == FACTORY_LABEL_TEXT["calculation-checked"]
    odd = item_labels(
        pool="practice", tier="A", original=True, reviewed=True, pattern=None,
        verification_label="teacher-approved",
    )  # fmt: skip
    assert "verification" not in odd  # an unknown label is never shown
