"""Lessons generated from verified solution traces (owner default, 17 Nov 2026).

A worked-example lesson whose steps come from stamped items' solution traces, in wording written
from an authored template that a person reviewed once, is servable on the same footing as a
calculation-checked item: only when the owner's `SERVE_TIER_A_UNREVIEWED` switch is on and every
trace item is still backed by an intact stamp (hash, ledger, not suspended). Anything else needs
`status: approved`. Hand-built interactive widgets are never generated, so a lesson with an
`explore` beat does not qualify.

Items are read from the content files, as lessons are, so no database session is needed.
"""

from __future__ import annotations

import time
from pathlib import Path

import yaml
from pydantic import ValidationError

from app.config import settings
from app.content.factory_roots import content_roots, read_ledgers
from app.content.schema import Item
from app.content.signatures import item_content_hash
from app.content.verification import effective_tier
from app.lessons.schema import Lesson
from app.registries.paths import content_root

TRACE_KIND = "worked_example_trace"
ALLOWED_BEATS = frozenset({"predict", "explain_scene", "worked_example", "faded_example", "check"})
CACHE_SECONDS = 30.0

_CACHE: dict[str, tuple[float, frozenset[str]]] = {}


def backed_item_ids(root: Path | None = None) -> frozenset[str]:
    """Ids of the items whose tier A is backed by an intact record in an intact ledger."""
    base = root or content_root()
    key = str(base)
    hit = _CACHE.get(key)
    if hit is not None and time.monotonic() - hit[0] < CACHE_SECONDS:
        return hit[1]
    ledgers = read_ledgers(base)
    found: set[str] = set()
    for folder in content_roots(base):
        for path in sorted((folder / "items").rglob("*.yaml")):
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict) or not data.get("verification"):
                    continue
                item = Item.model_validate(data)
            except (OSError, yaml.YAMLError, ValidationError):
                continue
            record = item.verification.as_record() if item.verification else None
            tier, _ = effective_tier(
                item.tier.value if item.tier else None,
                record,
                item_hash=item_content_hash(item),
                stamped_hashes=ledgers.stamped,
                reviewed_by=item.reviewed_by,
            )
            original = bool(item.provenance and item.provenance.original)
            if tier == "A" and original and item.id not in ledgers.suspended:
                found.add(item.id)
    result = frozenset(found)
    _CACHE[key] = (time.monotonic(), result)
    return result


def generated_servable(lesson: Lesson, root: Path | None = None) -> bool:
    """The owner-default rule for a draft lesson (see the module docstring)."""
    info = lesson.generated
    if info is None or not settings.serve_tier_a_unreviewed:
        return False
    if not info.wording_reviewed_by.strip() or not info.trace_item_ids:
        return False
    if any(beat.kind not in ALLOWED_BEATS for beat in lesson.beats):
        return False
    return set(info.trace_item_ids) <= backed_item_ids(root)
