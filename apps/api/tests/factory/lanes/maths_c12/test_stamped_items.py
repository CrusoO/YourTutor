# ruff: noqa: E501
"""The stamped items on disk: schema, record, ledger and the content validator item rules."""

from collections import Counter

import pytest
import yaml

from app.content import validator
from app.content.ledger import Ledger, ledger_path
from app.content.schema import ContentBundle, Item, Misconception, Overlay, Skill
from app.content.signatures import item_content_hash
from app.content.verification import record_errors

from .support import CONTENT, TEMPLATES

ITEM_FILES = sorted((CONTENT / "items" / "factory" / "maths_c12").glob("*.yaml"))
pytestmark = pytest.mark.skipif(not ITEM_FILES, reason="no stamped items generated yet")


def load(folder, model):
    return [
        model.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))
        for p in sorted((CONTENT / folder).rglob("*.yaml"))
    ]


ITEMS = [Item.model_validate(yaml.safe_load(p.read_text(encoding="utf-8"))) for p in ITEM_FILES]


def test_every_item_is_backed_by_the_ledger():
    ledger = Ledger(ledger_path(CONTENT))
    assert ledger.verify() == []
    hashes = ledger.stamped_record_hashes()
    for item in ITEMS:
        assert item.tier.value == "A" and item.status.value == "draft"
        assert item.verification.label == "calculation-checked" and item.provenance.original
        assert item.type.value == "mcq" and len(item.options) == 4
        assert (
            record_errors(
                item.verification.as_record(),
                item_hash=item_content_hash(item),
                stamped_hashes=hashes,
            )
            == []
        )


def test_validator_item_rules_pass():
    bundle = ContentBundle(
        skills=load("skills", Skill),
        items=ITEMS,
        misconceptions=load("misconceptions", Misconception),
        overlays=load("overlays", Overlay),
        glossaries=[],
        checkpoint_forms=[],
    )
    errors = [
        e
        for e in validator.validate_bundle(bundle).errors
        if "references unknown template" not in e
    ]
    assert errors == []


def test_every_model_has_items():
    per = Counter(i.skill_ids[0] for i in ITEMS)
    assert {t["skill_id"] for t in TEMPLATES} <= set(per)
    assert all(n >= 8 for n in per.values())
