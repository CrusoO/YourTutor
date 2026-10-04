from __future__ import annotations

from pathlib import Path

from app.content.schema import ContentStatus, Item, ItemRole
from app.content.signatures import item_content_hash
from app.content.validator import load_bundle, validate_bundle
from tests.content.conftest import minimal_item

NEW_ROLES = {"explain", "apply", "transfer"}


def _approve(item: Item) -> None:
    item.status = ContentStatus.approved
    item.reviewed_by = "teacher.test"
    item.content_hash = item_content_hash(item)


def _live_bundle(content_root: Path, *, with_roles: bool, approved_roles: bool = True):
    bundle = load_bundle(content_root)
    for item in bundle.items:
        _approve(item)
    overlay = bundle.overlays[0]
    overlay.live = True
    if with_roles:
        for index, role in enumerate(ItemRole):
            if role.value not in NEW_ROLES:
                continue
            data = minimal_item(
                f"ITEM.ROLE.{index}",
                stem=f"[role {index}] Solve for x: x + {20 + index} = {40 + index}",
                answer="20",
            )
            data["role"] = role.value
            item = Item.model_validate(data)
            if approved_roles:
                _approve(item)
            bundle.items.append(item)
    return bundle


def test_live_chapter_requires_explain_apply_and_transfer(content_root: Path) -> None:
    report = validate_bundle(_live_bundle(content_root, with_roles=False))
    live_errors = [e for e in report.errors if "live but below threshold" in e]
    assert live_errors
    for role in NEW_ROLES:
        assert f"MATH.S1 role {role} 0/1" in live_errors[0]


def test_live_chapter_role_coverage_is_met_with_approved_items(content_root: Path) -> None:
    report = validate_bundle(_live_bundle(content_root, with_roles=True))
    assert not [e for e in report.errors if " role " in e], report.errors


def test_draft_role_items_do_not_count_toward_live_coverage(content_root: Path) -> None:
    report = validate_bundle(_live_bundle(content_root, with_roles=True, approved_roles=False))
    live_errors = [e for e in report.errors if "live but below threshold" in e]
    assert live_errors and "role explain 0/1" in live_errors[0]


def test_role_gaps_only_warn_when_the_overlay_is_not_live(content_root: Path) -> None:
    bundle = load_bundle(content_root)
    report = validate_bundle(bundle)
    assert not [e for e in report.errors if " role " in e]
    assert any("not live" in w for w in report.warnings)
