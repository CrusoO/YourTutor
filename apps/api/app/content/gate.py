from __future__ import annotations

from typing import Any

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


def tier_is_servable(
    *,
    status: str,
    tier: str | None,
    reviewed_by: str | None,
    original: bool,
    allow_draft: bool,
    serve_tier_a_unreviewed: bool,
    suspended: bool = False,
    tier_backed: bool | None = None,
) -> bool:
    """The serving rule that adds verification tiers on top of the approval status.

    - suspended (telemetry or a person switched it off): never, even in development.
    - a tier A (or B without a recorded reviewer) that is not backed by an intact stamped
      verification record (`tier_backed is False`) is ignored: the item is treated as having no
      tier. `tier_backed=None` is the legacy call and trusts the tier as before.
    - retired: never.
    - ALLOW_DRAFT_CONTENT (development): everything else, Tier C included.
    - Tier C: never otherwise.
    - approved: served (a human approved it). Tier B also needs a recorded reviewer. A legacy item
      with no tier keeps the old rule.
    - draft: only a Tier A original, and only when SERVE_TIER_A_UNREVIEWED is on; or a Tier B
      with a recorded reviewer.
    """
    if suspended or status == RETIRED_STATUS:
        return False
    if allow_draft:
        return True
    if tier_backed is False and tier in ("A", "B") and not (tier == "B" and reviewed_by):
        tier = None
    if tier == "C":
        return False
    if tier == "B" and not reviewed_by:
        return False
    if status == ContentStatus.approved.value:
        return True
    if tier == "B":
        return True
    return tier == "A" and original and serve_tier_a_unreviewed


def row_is_servable(row: Any, *, allow_draft: bool, serve_tier_a_unreviewed: bool) -> bool:
    """`tier_is_servable` for an ItemRow (kept untyped so this module stays free of the db)."""
    provenance = getattr(row, "provenance", None) or {}
    tier = getattr(row, "tier", None)
    return tier_is_servable(
        status=row.status,
        tier=tier,
        reviewed_by=row.reviewed_by,
        original=bool(provenance.get("original")),
        allow_draft=allow_draft,
        serve_tier_a_unreviewed=serve_tier_a_unreviewed,
        suspended=getattr(row, "suspended_at", None) is not None,
        tier_backed=row_tier_backed(row),
    )


def row_tier_backed(row: Any) -> bool | None:
    """Whether the row's tier A/B is backed by an intact verification record (None: no tier).

    The record must be intact and carry this tier, and it must name the content the row holds now:
    the item hash is recomputed from the stored columns, so a row edited after the stamp (a stem,
    an option text under factory-2) stops being backed.
    """
    from app.content.verification import tier_backed

    tier = getattr(row, "tier", None)
    if tier not in ("A", "B"):
        return None
    record = getattr(row, "verification", None)
    if not tier_backed(record, tier):
        return False
    return _row_matches_record(row, record or {})


def _row_matches_record(row: Any, record: dict[str, Any]) -> bool:
    from pydantic import ValidationError

    from app.content.signatures import item_content_hash

    try:
        item = Item.model_validate(
            {
                "id": row.id,
                "skill_ids": list(row.skill_ids or []),
                "difficulty": row.difficulty,
                "type": row.type,
                "pool": row.pool,
                "role": row.role or "procedure",
                "stem": row.stem,
                "verify": row.verify,
                "options": list(row.options or []),
                "answer": row.answer,
                "solution_steps": list(row.solution_steps or []),
                "hints": list(row.hints or []),
                "prediction_prompt": row.prediction_prompt or {"en": ""},
                "step_hints": list(row.step_hints or []),
                "hint_restate": row.hint_restate,
                "generator_version": row.generator_version,
            }
        )
    except (ValidationError, ValueError, TypeError):
        return False
    return item_content_hash(item) == record.get("item_hash")


def overlay_is_targetable(
    overlay: Overlay, *, allow_draft: bool | None = None, actor: Actor | None = None
) -> bool:
    if overlay.live:
        return True
    if allow_draft is None:
        allow_draft = allow_draft_content(actor)
    return allow_draft
