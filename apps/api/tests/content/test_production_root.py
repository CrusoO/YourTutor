"""The production content root is a near-empty skeleton; the legacy pack is a test fixture."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import func, select

from app.content.loader import load_path
from app.content.schema import Item
from app.content.validator import validate_path
from app.db.models import ItemRow
from app.db.session import session_factory
from app.registries.loaders import load_all_curricula
from app.registries.paths import repo_root
from app.registries.sections import dangling_overlay_warnings
from tests.legacy_content import LEGACY_CONTENT_ROOT

PRODUCTION = repo_root() / "content"


def _is_unchecked_draft(item: Item) -> bool:
    """A model-drafted item from the authoring pipeline: tier C, draft, never stamped."""
    return (
        item.tier is not None
        and item.tier.value == "C"
        and item.status.value == "draft"
        and item.provenance is not None
        and item.provenance.author == "model-draft"
        and item.verification is None
    )


def test_production_root_validates() -> None:
    """The root holds what the lanes have stamped (tier A) and the unchecked model drafts (tier C,
    for reviewers only: the serving gate never serves tier C). It must validate cleanly, and no
    item may be anything else: no approved, tier B or untiered item sneaks in."""
    report = validate_path(PRODUCTION)
    assert report.errors == []
    assert report.bundle is not None
    items = report.bundle.items
    assert all(
        (i.tier is not None and i.tier.value == "A") or _is_unchecked_draft(i) for i in items
    )
    assert any(i.tier is not None and i.tier.value == "A" for i in items)
    assert all(not o.live for o in report.bundle.overlays)  # nothing is live yet


def test_production_root_loads_into_an_empty_database(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'prod.db'}"
    report = load_path(PRODUCTION, database_url=url)
    assert report.ok
    assert report.bundle is not None
    assert load_path(PRODUCTION, database_url=url).ok  # idempotent: a second load changes nothing
    with session_factory(url)() as db:
        stored = db.scalar(select(func.count()).select_from(ItemRow)) or 0
        assert stored == len(report.bundle.items)


def test_the_empty_skeleton_still_validates_with_zero_items(tmp_path: Path) -> None:
    root = tmp_path / "skeleton"
    for name in ("items", "skills", "overlays", "lessons", "passages", "templates"):
        (root / "cbse" / "10" / "maths" / name).mkdir(parents=True)
    report = validate_path(root)
    assert report.errors == []
    assert report.bundle is not None
    assert report.bundle.items == []
    assert report.bundle.skills == []


def test_the_legacy_fixture_still_validates() -> None:
    report = validate_path(LEGACY_CONTENT_ROOT)
    assert report.errors == []
    assert report.bundle is not None
    assert len(report.bundle.items) == 406


def test_chapters_without_an_overlay_file_warn() -> None:
    warnings = dangling_overlay_warnings([], load_all_curricula())
    assert any("cbse.10.maths.ch02" in w for w in warnings)
    report = validate_path(PRODUCTION)
    assert any("cbse.10.maths.ch02" in w for w in report.warnings)
    # chapters whose overlay file exists (physics) do not warn; maths chapters without one do
    missing = [w for w in report.warnings if "no overlay file" in w]
    assert not any("cbse.10.physics.electricity" in w for w in missing)
    assert not any("cbse.10.physics.light" in w for w in missing)
    assert any("cbse.10.maths.quadratic" in w for w in report.warnings)


def test_a_chapter_with_its_overlay_does_not_warn() -> None:
    spec = load_all_curricula()["seba"]
    overlay = type("O", (), {"id": spec.books[0].chapters[0].overlay_id})()
    assert dangling_overlay_warnings([overlay], {"seba": spec}) == []
