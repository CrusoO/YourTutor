"""Verification records (vrec/1) and the rule that a tier must be backed by one.

The tier of an item used to be a free YAML field. Now a factory tier (A, or a factory B) counts
only when the item carries a record that (1) hashes correctly, (2) names this item's current
content hash, (3) carries a label that maps to that tier, and (4) was written by the stamp step,
which we know because its hash is in the hash-chained ledger.

Honest labels only. The factory cannot emit `human-reviewed` or `teacher-approved`: those words
are not in the schema's label type, and `record_errors` refuses them by name.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Collection
from typing import Any

VREC_SCHEMA = "vrec/1"
CALCULATION_CHECKED = "calculation-checked"
FACT_CHECKED = "fact-checked-against-sources"
DIAGRAM_CHECKED = "diagram-spec-checked"
HONEST_LABELS = (CALCULATION_CHECKED, FACT_CHECKED, DIAGRAM_CHECKED)
FORBIDDEN_LABELS = ("human-reviewed", "teacher-approved")  # only people can grant these
LABEL_TIER = {CALCULATION_CHECKED: "A", DIAGRAM_CHECKED: "A", FACT_CHECKED: "B"}


# Fields the schema defaults. A record with a default left out and the same record with it spelled
# out hash alike, so a round trip through the Item model cannot change the hash.
FIELD_DEFAULTS: dict[str, Any] = {
    "template_hash": None, "lane": None, "chapter_ref": None, "methods_agreeing": [],
    "checks": [], "generated_by": {}, "llm_involved": False,
}  # fmt: skip


def record_hash(record: dict[str, Any]) -> str:
    """sha256 over the canonical JSON of the record without its own hash."""
    body = {**FIELD_DEFAULTS, **{k: v for k, v in record.items() if k != "record_hash"}}
    text = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def record_errors(
    record: dict[str, Any] | None,
    *,
    item_hash: str | None = None,
    stamped_hashes: Collection[str] | None = None,
) -> list[str]:
    """Why a record does not back a tier (empty list: it does).

    `item_hash`: the item's current content hash (None skips the binding check, as at serve time
    when only the stored row is at hand). `stamped_hashes`: record hashes found in an intact
    ledger (None skips the check; the loader always passes it).
    """
    if not record:
        return ["no verification record"]
    errors: list[str] = []
    if record.get("schema") != VREC_SCHEMA:
        errors.append("unknown record schema")
    label = record.get("label")
    if label in FORBIDDEN_LABELS:
        errors.append(f"label {label!r} can only be granted by a person, never by the factory")
    elif label not in HONEST_LABELS:
        errors.append(f"unknown label {label!r}")
    elif LABEL_TIER[label] != record.get("tier"):
        errors.append("tier does not match the label")
    if record.get("record_hash") != record_hash(record):
        errors.append("record hash does not match its contents (edited by hand?)")
    if item_hash is not None and record.get("item_hash") != item_hash:
        errors.append("record was stamped for different item content")
    if stamped_hashes is not None and record.get("record_hash") not in stamped_hashes:
        errors.append("record is not in the stamp ledger")
    return errors


def tier_backed(record: dict[str, Any] | None, tier: str | None) -> bool:
    """Serve-time check on a stored row: the record is intact and carries exactly this tier."""
    return bool(record) and not record_errors(record) and record.get("tier") == tier  # type: ignore[union-attr]


def effective_tier(
    claimed: str | None,
    record: dict[str, Any] | None,
    *,
    item_hash: str,
    stamped_hashes: Collection[str],
    reviewed_by: str | None,
) -> tuple[str | None, str | None]:
    """(tier to store, warning). A hand-written A is ignored; a hand-written B stands only with
    a recorded reviewer (a human vouches, as before); C always stands (it only restricts)."""
    if claimed is None or claimed == "C":
        return claimed, None
    if record is not None:
        problems = record_errors(record, item_hash=item_hash, stamped_hashes=stamped_hashes)
        if not problems and record.get("tier") == claimed:
            return claimed, None
        why = "; ".join(problems) or "record tier differs from the tier written"
        return (claimed, None) if claimed == "B" and reviewed_by else (None, why)
    if claimed == "B" and reviewed_by:
        return claimed, None
    return None, "hand-written tier without a verification record"
