"""The shipped Class 10 maths and physics content reaches a student end to end.

Loads the real content folders into the test database, then checks, with the owner's switch on and
off, that each curriculum chapter is live by tier, that its served items carry misconception
rules on wrong options, and that the label a student sees is the honest one.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.content.gate import row_is_servable, tier_live_gaps
from app.content.labels import VERIFICATION_BADGE, item_labels
from app.content.loader import _factory_backing, _upsert
from app.content.validator import ValidationReport, load_bundle
from app.db.models import ItemRow, OverlayRow
from app.learner.chapters import _is_live
from app.player.runtime import load_catalog

CONTENT = Path(__file__).resolve().parents[4] / "content"
CHAPTERS = {
    "cbse.10.maths.quadratic": "MATH.ALG.QUAD",
    "cbse.10.maths.ap": "MATH.ALG.AP",
    "cbse.10.maths.trig_applications": "MATH.TRIG.HD",
    "cbse.10.physics.electricity": "PHY.ELEC",
    "cbse.10.physics.light": "PHY.LIGHT",
}


@pytest.fixture(scope="module")
def loaded(tmp_path_factory: pytest.TempPathFactory):  # type: ignore[no-untyped-def]
    bundle = load_bundle(CONTENT)
    report = ValidationReport(bundle=bundle)
    backing, _ = _factory_backing(CONTENT, report)
    assert report.errors == []
    return bundle, backing


@pytest.fixture
def served_db(db: Session, loaded) -> Session:  # type: ignore[no-untyped-def]
    bundle, backing = loaded
    _upsert(db, bundle, prune=False, backing=backing)
    db.commit()
    return db


def test_every_stamped_item_is_factory_2_with_rules_on_wrong_options(served_db: Session) -> None:
    rows = [r for r in served_db.scalars(select(ItemRow)) if r.tier == "A"]
    assert len(rows) > 900
    for row in rows:
        assert row.generator_version == "factory-2", row.id
        assert row.type in ("mcq", "numeric", "expression")
        assert row.misconception_rules, row.id


def test_stamped_items_serve_only_with_the_owner_switch(served_db: Session) -> None:
    settings.allow_draft_content = False
    settings.serve_tier_a_unreviewed = False
    assert load_catalog(served_db, allow_draft=False) == ()
    settings.serve_tier_a_unreviewed = True
    assert len(load_catalog(served_db, allow_draft=False)) > 900


@pytest.mark.parametrize(("overlay_id", "prefix"), list(CHAPTERS.items()))
def test_each_chapter_is_live_by_tier_and_every_skill_has_a_diagnostic(
    served_db: Session, overlay_id: str, prefix: str
) -> None:
    overlay = served_db.get(OverlayRow, overlay_id)
    assert overlay is not None and overlay.live is False  # the file stays live: false
    assert overlay.skill_ids and all(s.startswith(prefix) for s in overlay.skill_ids)
    settings.allow_draft_content = False
    settings.serve_tier_a_unreviewed = False
    assert _is_live(served_db, overlay) is False
    settings.serve_tier_a_unreviewed = True
    rows = list(served_db.scalars(select(ItemRow)))
    assert tier_live_gaps(overlay.skill_ids, rows, allow_draft=False) == []
    assert _is_live(served_db, overlay) is True


def test_the_label_a_student_sees_is_calculation_checked_never_human_reviewed(
    served_db: Session,
) -> None:
    settings.serve_tier_a_unreviewed = True
    row = next(
        r for r in served_db.scalars(select(ItemRow)) if r.tier == "A" and r.pool == "practice"
    )
    assert row_is_servable(row, allow_draft=False, serve_tier_a_unreviewed=True)
    labels = item_labels(
        pool=row.pool,
        tier=row.tier,
        original=bool((row.provenance or {}).get("original")),
        reviewed=row.reviewed_by is not None,
        pattern=None,
        verification_label=row.verification["label"],
    )
    assert labels is not None and labels["badge"] == VERIFICATION_BADGE
    assert "reviewed" not in labels  # nobody has reviewed it
    assert "calculation" in labels["verification"] and "human" not in labels["verification"]
