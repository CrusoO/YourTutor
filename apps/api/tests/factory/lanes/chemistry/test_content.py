"""The emitted content folder and the stamped items on disk."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest
import yaml

from app.content import validator
from app.content.ledger import Ledger, ledger_path
from app.content.schema import ContentBundle, Item, Misconception, Overlay, Skill
from app.content.signatures import item_content_hash
from app.content.verification import record_errors
from app.factory.lanes.chemistry import catalog
from app.factory.lanes.chemistry.emit import render_files
from app.factory.lanes.chemistry.lane import LANE
from app.factory.runner import template_hash

CONTENT = Path(__file__).resolve().parents[6] / "content" / "cbse" / "10" / "chemistry"
CURRICULUM = (
    Path(__file__).resolve().parents[6] / "content" / "curricula" / "cbse" / "curriculum.yaml"
)
ITEM_FILES = sorted((CONTENT / "items" / "factory" / "chemistry").glob("*.yaml"))


def test_emitted_files_validate_in_a_clean_folder(tmp_path):
    for rel, text in render_files().items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    report = validator.validate_path(tmp_path)
    assert not report.errors, report.errors[:3]
    for path in (tmp_path / "overlays").glob("*.yaml"):
        assert yaml.safe_load(path.read_text(encoding="utf-8"))["live"] is False


def test_the_curriculum_entry_lists_every_overlay_chapter():
    data = yaml.safe_load(CURRICULUM.read_text(encoding="utf-8"))
    book = next(b for b in data["books"] if b["id"] == "cbse.10.chemistry")
    assert book["subject"] == "chemistry" and book["grade"] == 10
    chapters = {c["id"] for c in book["chapters"]}
    assert chapters == {o["id"] for o in catalog.overlay_records()}


def test_committed_templates_match_the_catalog():
    for tpl in catalog.template_records():
        path = CONTENT / "templates" / f"{tpl['id'].lower().replace('.', '_')}.yaml"
        assert yaml.safe_load(path.read_text(encoding="utf-8")) == tpl


pytestmark_items = pytest.mark.skipif(not ITEM_FILES, reason="no stamped items generated yet")


def load(folder, model):
    return [
        model.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))
        for p in sorted((CONTENT / folder).rglob("*.yaml"))
    ]


@pytestmark_items
def test_every_stamped_item_is_backed_by_the_ledger():
    items = [Item.model_validate(yaml.safe_load(p.read_text(encoding="utf-8"))) for p in ITEM_FILES]
    ledger = Ledger(ledger_path(CONTENT))
    assert ledger.verify() == []
    hashes = ledger.stamped_record_hashes()
    templates = {t["id"]: t for t in catalog.template_records()}
    for item in items:
        assert item.tier.value == "A" and item.status.value == "draft"
        assert item.verification.label == "calculation-checked" and item.provenance.original
        assert "human" not in item.verification.label
        assert not record_errors(
            item.verification.as_record(),
            item_hash=item_content_hash(item),
            stamped_hashes=hashes,
        )
        assert item.template_hash == template_hash(LANE, templates[item.template_id])


@pytestmark_items
def test_validator_item_rules_pass_and_every_skill_has_items():
    items = [Item.model_validate(yaml.safe_load(p.read_text(encoding="utf-8"))) for p in ITEM_FILES]
    bundle = ContentBundle(
        skills=load("skills", Skill),
        items=items,
        misconceptions=load("misconceptions", Misconception),
        overlays=load("overlays", Overlay),
        glossaries=[],
        checkpoint_forms=[],
    )
    report = validator.ValidationReport(bundle=None)  # type: ignore[arg-type]
    for check in (
        validator._refs_and_cycles,
        validator._items,
        validator._stem_uniqueness,
        validator._hint_language,
        validator._language_quality,
        validator._bkt_params,
    ):
        check(bundle, report)
    errors = [e for e in report.errors if "distinct stems" not in e]
    assert errors == [], errors[:3]
    per = Counter(i.skill_ids[0] for i in items)
    assert {s for s, _, _ in catalog.SKILLS} <= set(per)
    assert len(items) >= 400
