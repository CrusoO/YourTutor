"""Matched checkpoint forms (A and B) from stamped checkpoint-pool items.

A form is only a list of item ids, so it is generated, not typed: every id comes from a stamped
item in the lane folder, and the A and B items of a pair share a skill and differ in difficulty
by at most MAX_DIFFICULTY_GAP. Pairs rotate over the chapter's skills so each skill is covered
before any is repeated. A chapter with fewer than `minimum` pairs gets no form.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

MAX_DIFFICULTY_GAP = 0.1
FORM_MAX = 15


def _read(folder: Path) -> list[dict[str, Any]]:
    out = []
    for path in sorted(folder.rglob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            out.append(data)
    return out


def build_forms(root: Path, *, minimum: int = 10) -> list[dict[str, Any]]:
    """One forms record per overlay under `root` that has at least `minimum` matched pairs."""
    items = [
        i for i in _read(root / "items") if i.get("pool") == "checkpoint" and i.get("verification")
    ]
    by_skill: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        by_skill[str(item["skill_ids"][0])].append(item)
    forms: list[dict[str, Any]] = []
    for overlay in _read(root / "overlays"):
        queues: list[list[tuple[str, str]]] = []
        for skill in overlay.get("skill_ids", []):
            mine = sorted(by_skill.get(skill, []), key=lambda i: (i["difficulty"], i["id"]))
            pairs = [
                (a["id"], b["id"])
                for a, b in zip(mine[0::2], mine[1::2], strict=False)
                if abs(a["difficulty"] - b["difficulty"]) <= MAX_DIFFICULTY_GAP + 1e-9
            ]
            if pairs:
                queues.append(pairs)
        chosen: list[tuple[str, str]] = []
        depth = 0
        while len(chosen) < FORM_MAX and any(len(q) > depth for q in queues):
            chosen += [q[depth] for q in queues if len(q) > depth][: FORM_MAX - len(chosen)]
            depth += 1
        if len(chosen) < minimum:
            continue
        cp = "CP." + str(overlay["id"]).upper().replace("-", "_")
        forms.append(
            {
                "id": f"{cp}.FORMS",
                "checkpoint_id": cp,
                "A": [a for a, _ in chosen],
                "B": [b for _, b in chosen],
                "match_map": {a: b for a, b in chosen},
            }
        )
    return forms
