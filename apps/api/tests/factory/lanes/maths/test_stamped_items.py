# ruff: noqa: E501
"""The stamped items on disk: schema, record, ledger and the content validator's item rules."""

from collections import Counter

import pytest
import yaml

from app.content import validator
from app.content.ledger import Ledger, ledger_path
from app.content.schema import ContentBundle, Item, Misconception, Overlay, Skill
from app.content.signatures import item_content_hash
from app.content.verification import record_errors

from .support import CONTENT

ITEM_FILES = sorted((CONTENT / "items" / "factory" / "maths_c10").glob("*.yaml"))
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
        assert "human" not in item.verification.label


def test_validator_item_rules_pass():
    bundle = ContentBundle(
        skills=load("skills", Skill),
        items=ITEMS,
        misconceptions=load("misconceptions", Misconception),
        overlays=load("overlays", Overlay),
        glossaries=[],
        checkpoint_forms=[],
    )
    report = validator.validate_bundle(bundle)
    errors = [e for e in report.errors if "references unknown template" not in e]
    assert errors == []


def test_counts_by_skill_cover_every_class10_skill():
    per = Counter(i.skill_ids[0] for i in ITEMS)
    skills = {s.id for s in load("skills", Skill) if "prerequisites_class" not in s.id}
    class10 = {s for s in skills if s.startswith(("MATH.ALG.QUAD", "MATH.ALG.AP", "MATH.TRIG"))}
    assert class10 <= set(per), class10 - set(per)
    assert all(n >= 5 for n in per.values())
