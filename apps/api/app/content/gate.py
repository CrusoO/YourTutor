from __future__ import annotations

from app.auth.actor import Actor
from app.auth.authz import can_load_draft
from app.content.schema import ContentStatus, Item, Overlay

RETIRED_STATUS = ContentStatus.retired.value


def allow_draft_content(actor: Actor | None = None) -> bool:
    return can_load_draft(actor)


def content_status_is_servable(status: str, *, allow_draft: bool) -> bool:
    if status == RETIRED_STATUS:
        return False
    if status == ContentStatus.approved.value:
        return True
    return allow_draft


def item_is_servable(
    item: Item, *, allow_draft: bool | None = None, actor: Actor | None = None
) -> bool:
    if item.status == ContentStatus.retired:
        return False
    if item.status == ContentStatus.approved:
        return True
    if allow_draft is None:
        allow_draft = allow_draft_content(actor)
    return allow_draft


def overlay_is_targetable(
    overlay: Overlay, *, allow_draft: bool | None = None, actor: Actor | None = None
) -> bool:
    if overlay.live:
        return True
    if allow_draft is None:
        allow_draft = allow_draft_content(actor)
    return allow_draft
