from __future__ import annotations

from app.config import settings
from app.content.schema import ContentStatus, Item, Overlay


def allow_draft_content() -> bool:
    return settings.allow_draft_content


def item_is_servable(item: Item, *, allow_draft: bool | None = None) -> bool:
    if item.status == ContentStatus.approved:
        return True
    if allow_draft is None:
        allow_draft = allow_draft_content()
    return allow_draft


def overlay_is_targetable(overlay: Overlay, *, allow_draft: bool | None = None) -> bool:
    if overlay.live:
        return True
    if allow_draft is None:
        allow_draft = allow_draft_content()
    return allow_draft
