"""Done screen content (S1b): pure. No streaks, ranks, scores or comparisons."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def done_summary(
    path: Sequence[Mapping[str, Any]],
    *,
    start_levels: Mapping[str, int],
    touched: Sequence[str],
    remaining: int,
) -> dict[str, Any]:
    """`path` is the chapter's skill path (see `learner.chapters.skill_path`, with titles)."""

    def brief(row: Mapping[str, Any]) -> dict[str, Any]:
        return {"id": row["id"], "title": row["title"], "status": row["status"]}

    touched_set = set(touched)
    current = next((row for row in path if row.get("current")), None)
    return {
        "learned": [brief(row) for row in path if row["level"] > start_levels.get(row["id"], 0)],
        "practised": [brief(row) for row in path if row["id"] in touched_set],
        "skills": [brief(row) for row in path],
        "next": {"id": current["id"], "title": current["title"]} if current else None,
        "remaining_active_minutes": max(0, int(remaining)),
    }
