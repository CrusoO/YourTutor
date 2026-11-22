"""Mistake notebook: when a wrong answer comes back, as pure functions.

A notebook entry is made when a learner's first answer to an item is wrong. It comes back for a
retrieval attempt after the first, second and third return (days in `config/notebook.yaml`, counted
from the miss). `stage` is the index of the return the entry is waiting for (0, 1, 2).

- Right at stage k moves to k + 1; right at the last stage settles the entry.
- Wrong goes back one stage (never below the first) and the days are counted again from now, so a
  wrong return never comes back before the first return gap has passed.

Nothing here reads a clock, a database or a learner's text. Time is always passed in.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

import yaml

from app.registries.paths import config_dir

OPEN = "open"
SETTLED = "settled"
OUTCOMES: frozenset[str] = frozenset({"right", "wrong"})


@dataclass(frozen=True)
class NotebookConfig:
    return_days: tuple[int, ...]
    due_limit: int

    @property
    def stages(self) -> int:
        return len(self.return_days)


@dataclass(frozen=True)
class EntryState:
    """The schedule part of an entry: where it is, what it is counted from, and when it is due."""

    stage: int
    state: str
    anchor_at: datetime  # the miss, or the last wrong return
    due_at: datetime | None  # None once settled


def parse_config(raw: object) -> NotebookConfig:
    if not isinstance(raw, dict):
        raise ValueError("notebook.yaml: expected a mapping")
    days = raw.get("return_days")
    limit = raw.get("due_limit")
    if (
        not isinstance(days, list)
        or not days
        or any(isinstance(d, bool) or not isinstance(d, int) or d < 1 for d in days)
        or list(days) != sorted(set(days))
    ):
        raise ValueError("notebook.yaml: return_days must be rising whole days of 1 or more")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("notebook.yaml: due_limit must be a whole number of 1 or more")
    return NotebookConfig(tuple(days), limit)


@lru_cache(maxsize=4)
def _load(path: str) -> NotebookConfig:
    with open(path, encoding="utf-8") as handle:
        return parse_config(yaml.safe_load(handle))


def load_config(root: Path | None = None) -> NotebookConfig:
    return _load(str((root or config_dir()) / "notebook.yaml"))


def due_at_for(anchor_at: datetime, stage: int, cfg: NotebookConfig) -> datetime:
    return anchor_at + timedelta(days=cfg.return_days[stage])


def new_entry(missed_at: datetime, cfg: NotebookConfig) -> EntryState:
    return EntryState(0, OPEN, missed_at, due_at_for(missed_at, 0, cfg))


def is_due(entry: EntryState, now: datetime) -> bool:
    return entry.state == OPEN and entry.due_at is not None and entry.due_at <= now


def apply_return(entry: EntryState, outcome: str, now: datetime, cfg: NotebookConfig) -> EntryState:
    """The entry after a return attempt. A settled entry does not change."""
    if outcome not in OUTCOMES:
        raise ValueError("outcome must be right or wrong")
    if entry.state != OPEN:
        return entry
    if outcome == "right":
        nxt = entry.stage + 1
        if nxt >= cfg.stages:
            return EntryState(entry.stage, SETTLED, entry.anchor_at, None)
        # counted from the miss, but never earlier than now
        due = max(now, due_at_for(entry.anchor_at, nxt, cfg))
        return EntryState(nxt, OPEN, entry.anchor_at, due)
    back = max(entry.stage - 1, 0)
    return EntryState(back, OPEN, now, due_at_for(now, back, cfg))


def stage_counts(entries: list[EntryState], cfg: NotebookConfig) -> dict[str, int]:
    """Entries waiting for each return ("1", "2", ...) and how many are settled."""
    out = {str(i + 1): 0 for i in range(cfg.stages)}
    out["settled"] = 0
    for e in entries:
        if e.state == SETTLED:
            out["settled"] += 1
        else:
            out[str(e.stage + 1)] += 1
    return out


def pick_new_form(
    original_id: str,
    original_stem: str,
    candidates: list[tuple[str, str, float]],
    difficulty: float,
) -> str | None:
    """A different item for the same skill: (id, stem, difficulty) candidates.

    Never the original and never one with the same stem; the closest difficulty wins, ties by id,
    so the choice is the same every time. None when there is no alternative.
    """
    pool = [c for c in candidates if c[0] != original_id and c[1].strip() != original_stem.strip()]
    if not pool:
        return None
    return min(pool, key=lambda c: (abs(c[2] - difficulty), c[0]))[0]
