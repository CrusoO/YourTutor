"""The source (rights) register: `<content>/rights/register.yaml`.

One row per source an item may be derived from, including the sources we must not use (so a
mistaken reference fails loudly instead of silently). The register records facts about licences
as the owner's research found them; a row with `unverified: true` has not been re-checked against
the licence text itself. It stores no source text.

Validation rules (all errors, so `content validate` and `content load` refuse a bad reference):
- an item that names a source must name a row that exists;
- a row with `allowed: false` or `commercial_ok: false` can never be referenced by an item that is
  not retired;
- every referenced row needs `checked_on` and an `attribution_text`;
- a share-alike row belongs to `pool: share_alike`, and an item from that pool cannot also be
  marked `original` (an LLM must never rewrite share-alike material into an "original");
- `derived_item_ids` in the register and the items' own `provenance.source_id` must agree.

This is not `content/sources/notes.yaml`: that file lists authored notes for lessons
(app.lessons.sources). The two are separate on purpose.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, ValidationError

from app.content.schema import ContentStatus, Item

REGISTER_RELATIVE = Path("rights") / "register.yaml"

Pool = Literal["main", "share_alike", "excluded"]


class SourceRow(BaseModel):
    model_config = {"extra": "forbid"}

    id: str = Field(min_length=1)
    name: str
    url: str | None = None
    licence_id: str
    licence_version: str | None = None
    commercial_ok: bool
    derivatives_ok: bool
    share_alike: bool
    allowed: bool = True
    pool: Pool = "main"
    attribution_text: str | None = None
    checked_on: date | None = None
    checked_by: str | None = None
    unverified: bool = False
    notes: str = ""
    reason: str | None = None  # why a source is not allowed
    derived_item_ids: list[str] = []


def register_path(root: Path) -> Path:
    return root / REGISTER_RELATIVE


def load_register(root: Path) -> list[SourceRow]:
    """Rows of the register; an empty list when the file does not exist."""
    path = register_path(root)
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rows = data.get("sources") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise ValueError(f"{path} must contain a `sources:` list")
    return [SourceRow.model_validate(row) for row in rows]


def register_row_errors(rows: list[SourceRow]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for row in rows:
        if row.id in seen:
            errors.append(f"source {row.id}: duplicate id")
        seen.add(row.id)
        if not row.allowed and not (row.reason or "").strip():
            errors.append(f"source {row.id}: allowed is false but no reason is given")
        if row.allowed and row.pool == "excluded":
            errors.append(f"source {row.id}: allowed rows cannot be in pool excluded")
        if not row.allowed and row.pool != "excluded":
            errors.append(f"source {row.id}: a source that is not allowed belongs in pool excluded")
        if row.allowed and row.share_alike != (row.pool == "share_alike"):
            errors.append(f"source {row.id}: share_alike and pool share_alike must go together")
        if row.allowed and not row.commercial_ok:
            errors.append(f"source {row.id}: commercial_ok is false, so it cannot be allowed")
    return errors


def register_errors(rows: list[SourceRow], items: list[Item]) -> list[str]:
    """Problems in the register and in every item's reference to it."""
    errors = register_row_errors(rows)
    by_id = {row.id: row for row in rows}
    item_ids = {item.id for item in items}
    referenced: dict[str, set[str]] = {}
    for item in items:
        source_id = item.provenance.source_id if item.provenance else None
        if not source_id or item.status == ContentStatus.retired:
            continue
        row = by_id.get(source_id)
        if row is None:
            errors.append(f"{item.id}: source {source_id!r} is not in the source register")
            continue
        referenced.setdefault(source_id, set()).add(item.id)
        if not row.allowed:
            errors.append(f"{item.id}: source {source_id} is not allowed ({row.reason})")
        if not row.commercial_ok:
            errors.append(f"{item.id}: source {source_id} does not allow commercial use")
        if row.checked_on is None:
            errors.append(f"{item.id}: source {source_id} has no checked_on date")
        if not (row.attribution_text or "").strip():
            errors.append(f"{item.id}: source {source_id} has no attribution_text")
        if row.pool == "share_alike" and item.provenance and item.provenance.original:
            errors.append(
                f"{item.id}: an item from the share_alike pool ({source_id}) cannot be original"
            )
    for row in rows:
        for derived in row.derived_item_ids:
            if derived not in item_ids:
                errors.append(f"source {row.id}: derived item {derived} does not exist")
            elif derived not in referenced.get(row.id, set()):
                errors.append(f"source {row.id}: lists {derived}, which does not cite it")
        for item_id in sorted(referenced.get(row.id, set()) - set(row.derived_item_ids)):
            errors.append(f"{item_id}: cites {row.id} but is missing from its derived_item_ids")
    return errors


def rights_errors(root: Path, items: list[Item]) -> list[str]:
    """Hook for `content validate` / `content load`: register file problems plus item references."""
    try:
        rows = load_register(root)
    except (ValueError, ValidationError, yaml.YAMLError) as exc:
        return [f"source register: {str(exc).splitlines()[0]}"]
    return register_errors(rows, items)
