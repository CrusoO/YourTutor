"""Offline pack eligibility (M7b). Same rules as ARCHITECTURE §11."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.content.gate import content_status_is_servable

if TYPE_CHECKING:
    from app.content.schema import Item
    from app.db.models import ItemRow


def item_is_offline_verifiable(*, item_type: str, answer: dict | None, verify: str | dict | None) -> bool:
    del verify
    if item_type in ("numeric", "mcq"):
        return True
    if item_type in ("short_text", "expression"):
        return bool((answer or {}).get("accept"))
    return False


def item_row_offline_pack_eligible(row: ItemRow, *, allow_draft: bool) -> bool:
    if row.pool != "practice":
        return False
    if not content_status_is_servable(row.status, allow_draft=allow_draft):
        return False
    return item_is_offline_verifiable(
        item_type=row.type,
        answer=row.answer if isinstance(row.answer, dict) else None,
        verify=row.verify,
    )


def item_schema_offline_pack_eligible(item: Item, *, allow_draft: bool) -> bool:
    if item.pool.value != "practice":
        return False
    if not content_status_is_servable(item.status.value, allow_draft=allow_draft):
        return False
    return item_is_offline_verifiable(
        item_type=item.type.value,
        answer=item.answer.model_dump(),
        verify=item.verify if isinstance(item.verify, str) else (
            item.verify.model_dump() if item.verify else None
        ),
    )
