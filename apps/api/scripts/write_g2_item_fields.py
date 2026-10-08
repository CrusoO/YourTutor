"""Add draft G2 fields (step hints, restated question, slip patterns, ...) to practice items.

Reads every practice item YAML under content/items, and for items that do not have the fields yet
writes them back with `app.content.diagnosis_fields.draft_fields`. Drafts only: the items keep
their status. Re-running changes nothing.

    cd apps/api && python scripts/write_g2_item_fields.py ../../content
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from app.content.diagnosis_fields import draft_fields
from app.content.schema import Item

FIELDS = ("step_hints", "hint_restate", "slip_patterns", "intermediate_values", "min_plausible_ms")


def main(root: Path) -> int:
    changed = 0
    for path in sorted((root / "items").rglob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or raw.get("pool") != "practice":
            continue
        if "step_hints" in raw:
            continue
        item = Item.model_validate(raw)
        drafts = draft_fields(item)
        for key in FIELDS:
            value = drafts[key]
            if value in ([], None):
                continue
            raw[key] = value
        path.write_text(
            yaml.safe_dump(raw, sort_keys=False, allow_unicode=True), encoding="utf-8", newline="\n"
        )
        changed += 1
    print(f"updated {changed} item files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1] if len(sys.argv) > 1 else "../../content")))
