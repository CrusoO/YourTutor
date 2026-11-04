"""Helplines from `config/helplines.yaml`. Every entry is unverified until the owner says otherwise.

`unverified_helplines()` is the hook for the production start-up guard: it lists every helpline
that can be shown to a student and has not been confirmed. Nothing here invents a number.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.registries.paths import config_dir


@dataclass(frozen=True)
class Helpline:
    id: str
    region: str
    kind: str  # mental_health | child_protection | exam_counselling
    name: str
    number: str
    languages: tuple[str, ...]
    hours: str | None
    verified: bool

    def public(self) -> dict[str, Any]:
        """What the web may show. The verified flag travels so the UI can say so if it wishes."""
        return {
            "id": self.id,
            "kind": self.kind,
            "name": self.name,
            "number": self.number,
            "hours": self.hours,
            "verified": self.verified,
        }


def _row(raw: dict[str, Any], default_kind: str, default_region: str) -> Helpline | None:
    number = raw.get("number")
    if not number:  # a placeholder with no number is never shown
        return None
    return Helpline(
        id=str(raw["id"]),
        region=str(raw.get("region") or default_region),
        kind=str(raw.get("kind") or default_kind),
        name=str(raw["name"]),
        number=str(number),
        languages=tuple(str(x) for x in raw.get("languages") or ()),
        hours=raw.get("hours"),
        verified=raw.get("verified") is True,
    )


def load_helplines(root: Path | None = None) -> tuple[str, tuple[Helpline, ...]]:
    data = yaml.safe_load(((root or config_dir()) / "helplines.yaml").read_text("utf-8")) or {}
    region = str(data.get("default_region") or "")
    rows = [_row(raw, "mental_health", region) for raw in data.get("helplines") or ()] + [
        _row(raw, "exam_counselling", region) for raw in data.get("exam_counselling") or ()
    ]
    return region, tuple(r for r in rows if r is not None)


@lru_cache(maxsize=1)
def _default() -> tuple[str, tuple[Helpline, ...]]:
    return load_helplines()


def all_helplines(root: Path | None = None) -> tuple[Helpline, ...]:
    return (load_helplines(root) if root else _default())[1]


def helplines_for(
    kinds: tuple[str, ...] | None = None, region: str | None = None, root: Path | None = None
) -> list[Helpline]:
    default_region, rows = load_helplines(root) if root else _default()
    wanted = region or default_region
    chosen = [r for r in rows if r.region == wanted and (kinds is None or r.kind in kinds)]
    if kinds is not None:  # the caller's order of kinds is the order shown
        chosen.sort(key=lambda r: kinds.index(r.kind))
    return chosen


def unverified_helplines(root: Path | None = None) -> list[str]:
    """Ids of every shown-able helpline that is not verified. Empty means safe for production."""
    return [r.id for r in all_helplines(root) if not r.verified]
