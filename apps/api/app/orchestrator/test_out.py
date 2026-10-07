"""Skip ahead (ARCHITECTURE §9.7): pure item selection and pass rule. No I/O."""

from __future__ import annotations

from collections.abc import Sequence

from app.content.validator import item_tier
from app.orchestrator.types import CatalogItem

TEST_OUT_ITEMS = 2
_STRETCH_ROLES = frozenset({"apply", "transfer"})


def _servable(item: CatalogItem, allow_draft: bool) -> bool:
    if item.status == "retired":
        return False
    return item.status == "approved" or allow_draft


def select_items(
    catalog: Sequence[CatalogItem], skill_id: str, *, allow_draft: bool
) -> list[CatalogItem] | None:
    """Two hard practice items for the skill, at least one `apply` or `transfer`.

    Deterministic (sorted by id). None when the skill cannot offer such a pair.
    """
    hard = sorted(
        (
            item
            for item in catalog
            if item.pool == "practice"
            and item.primary_skill == skill_id
            and item_tier(item.difficulty) == "hard"
            and _servable(item, allow_draft)
        ),
        key=lambda item: item.id,
    )
    stretch = [item for item in hard if item.role in _STRETCH_ROLES]
    if not stretch:
        return None
    first = stretch[0]
    rest = [item for item in hard if item.id != first.id]
    if not rest:
        return None
    return [rest[0], first] if rest[0].role not in _STRETCH_ROLES else [first, rest[0]]


def passed(answers: Sequence[bool]) -> bool:
    return len(answers) == TEST_OUT_ITEMS and all(answers)
