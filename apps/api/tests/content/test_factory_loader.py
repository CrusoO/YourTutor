"""The loader stores a tier only when a stamped record backs it; suspension survives a reload."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.content.gate import row_is_servable
from app.content.ledger import Ledger
from app.content.loader import _factory_backing, _suspend_from_ledger, _upsert
from app.content.schema import ContentBundle, Item, Skill
from app.content.signatures import item_content_hash
from app.content.validator import ValidationReport
from app.content.verification import record_hash
from app.db.models import ItemRow
from app.factory.suspend import suspend_item, unsuspend_item

from .test_factory_gate import BASE_ITEM

SKILL = Skill.model_validate(
    {
        "id": "S.1",
        "title": {"en": "s"},
        "grade_band": [9],
        "subject": "maths",
        "bkt": {"p_init": 0.2, "p_learn": 0.2, "p_slip": 0.1, "p_guess": 0.2},
    }
)


def _record(item: Item, **over) -> dict:
    rec = {
        "schema": "vrec/1", "item_hash": item_content_hash(item), "template_hash": "t",
        "certificate_hash": "cert", "label": "calculation-checked", "tier": "A",
        "stamped_at": "2026-11-16T00:00:00+00:00", **over,
    }  # fmt: skip
    rec["record_hash"] = record_hash(rec)
    return rec


def _bundle(*items: Item) -> ContentBundle:
    return ContentBundle(
        skills=[SKILL], items=list(items), misconceptions=[], overlays=[],
        glossaries=[], checkpoint_forms=[],
    )  # fmt: skip


def _load(db: Session, root: Path, *items: Item) -> ValidationReport:
    bundle = _bundle(*items)
    report = ValidationReport(bundle=bundle)
    backing, suspended = _factory_backing(root, report)
    _upsert(db, bundle, prune=False, backing=backing)
    _suspend_from_ledger(db, suspended)
    db.commit()
    return report


def _row(db: Session, item_id: str) -> ItemRow:
    row = db.get(ItemRow, item_id)
    assert row is not None
    return row


def _servable(db: Session, item_id: str) -> bool:
    row = _row(db, item_id)
    return row_is_servable(row, allow_draft=False, serve_tier_a_unreviewed=True)


def test_hand_typed_tier_a_is_dropped_and_warned(db: Session, tmp_path: Path):
    hand = Item.model_validate({**BASE_ITEM, "tier": "A"})
    report = _load(db, tmp_path, hand)
    row = _row(db, hand.id)
    assert row.tier is None and row.verification is None
    assert not _servable(db, hand.id)
    assert any("tier A ignored" in w for w in report.warnings)


def test_a_record_in_the_ledger_is_stored_and_served(db: Session, tmp_path: Path):
    bare = Item.model_validate(BASE_ITEM)
    rec = _record(bare)
    ledger = Ledger(tmp_path / "factory" / "ledger.jsonl")
    ledger.append("stamped", bare.id, rec["item_hash"], {"record_hash": rec["record_hash"]}, ts="t")
    stamped = Item.model_validate({**BASE_ITEM, "tier": "A", "verification": rec})
    report = _load(db, tmp_path, stamped)
    row = _row(db, stamped.id)
    assert report.errors == [] and report.warnings == []
    assert row.tier == "A" and row.certificate_hash == "cert"
    assert row.verification and row.verification["label"] == "calculation-checked"
    assert _servable(db, stamped.id)


def test_record_not_in_the_ledger_or_for_other_content_is_dropped(db: Session, tmp_path: Path):
    bare = Item.model_validate(BASE_ITEM)
    rec = _record(bare)
    forged = Item.model_validate({**BASE_ITEM, "tier": "A", "verification": rec})
    _load(db, tmp_path, forged)  # no ledger at all
    assert _row(db, forged.id).tier is None
    ledger = Ledger(tmp_path / "factory" / "ledger.jsonl")
    ledger.append("stamped", bare.id, rec["item_hash"], {"record_hash": rec["record_hash"]}, ts="t")
    edited = Item.model_validate(
        {**BASE_ITEM, "stem": {"en": "Edited after the stamp?"}, "tier": "A", "verification": rec}
    )
    _load(db, tmp_path, edited)
    assert _row(db, edited.id).tier is None and not _servable(db, edited.id)


def test_a_broken_ledger_is_a_load_error(db: Session, tmp_path: Path):
    ledger = Ledger(tmp_path / "factory" / "ledger.jsonl")
    ledger.append("stamped", "x", "h", {"record_hash": "r"}, ts="t")
    ledger.path.write_text(
        ledger.path.read_text().replace('"kind":"stamped"', '"kind":"suspended"')
    )
    report = ValidationReport(bundle=_bundle(Item.model_validate(BASE_ITEM)))
    _factory_backing(tmp_path, report)
    assert any(e.startswith("factory ledger:") for e in report.errors)


def test_suspension_switches_an_item_off_and_survives_reload(db: Session, tmp_path: Path):
    bare = Item.model_validate(BASE_ITEM)
    rec = _record(bare)
    ledger = Ledger(tmp_path / "factory" / "ledger.jsonl")
    ledger.append("stamped", bare.id, rec["item_hash"], {"record_hash": rec["record_hash"]}, ts="t")
    item = Item.model_validate({**BASE_ITEM, "tier": "A", "verification": rec})
    _load(db, tmp_path, item)
    assert _servable(db, item.id)
    assert suspend_item(db, item.id, "high-ability students fail it", ledger)
    db.commit()
    assert not _servable(db, item.id)
    _load(db, tmp_path, item)  # a plain reload does not clear it (upsert leaves the column alone)
    assert not _servable(db, item.id)
    assert unsuspend_item(db, item.id, "re-checked by a person", ledger)
    db.commit()
    assert _servable(db, item.id)
    assert not unsuspend_item(db, item.id, "again", ledger) and not suspend_item(db, "nope", "x")


def test_a_ledger_suspension_is_applied_on_load(db: Session, tmp_path: Path):
    bare = Item.model_validate(BASE_ITEM)
    rec = _record(bare)
    ledger = Ledger(tmp_path / "factory" / "ledger.jsonl")
    ledger.append("stamped", bare.id, rec["item_hash"], {"record_hash": rec["record_hash"]}, ts="t")
    ledger.append("suspended", bare.id, "h", {"reason": "audit found an error"}, ts="t2")
    item = Item.model_validate({**BASE_ITEM, "tier": "A", "verification": rec})
    _load(db, tmp_path, item)
    row = _row(db, item.id)
    assert row.suspended_at is not None and not _servable(db, item.id)
    ledger.append("unsuspended", bare.id, "h", {"reason": "fixed"}, ts="t3")
    assert ledger.suspended_ids() == set()


def test_legacy_item_without_tier_is_unchanged(db: Session, tmp_path: Path):
    approved = Item.model_validate({**BASE_ITEM, "status": "approved", "reviewed_by": "teacher"})
    _load(db, tmp_path, approved)
    row = _row(db, approved.id)
    assert row.tier is None and row.verification is None
    assert row_is_servable(row, allow_draft=False, serve_tier_a_unreviewed=False)
