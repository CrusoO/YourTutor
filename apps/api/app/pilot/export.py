"""The pilot's data: every answer, and how learners did on skills they had left alone for a while.

Pure functions over the event log. The log already holds each answer, its hint level, the learner's
"sure or unsure", the time taken and the diagnosis, so nothing new is recorded here; this only
reads it and adds two things the log leaves implicit:

- how many days passed since that skill was last practised, and
- whether the answer was the first, unhinted go at the item (the only kind that says what a learner
  knows).

A delayed retest is a review (a warm-up) of a skill last practised at least 7 days before, and one
at least 21 days before is the longer one. These are the same gaps the "Retains" ladder level needs.
Everything about a person is replaced by a keyed pseudonym before it leaves this module.
"""

from __future__ import annotations

import hashlib
import hmac
import uuid
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.auth.security import as_utc
from app.db.models import EventRow
from app.orchestrator.types import CatalogItem

RETEST_DAYS = 7  # a review this long after the last practice is a delayed retest
LONG_RETEST_DAYS = 21
MIN_SALT_CHARS = 16
HELP_EVENTS = frozenset({"request_help", "request_hint", "stuck_choice", "stuck_step"})

ATTEMPT_COLUMNS = (
    "pseudonym",
    "at",
    "session_type",
    "pool",
    "skill_id",
    "item_id",
    "role",
    "difficulty",
    "correct",
    "first_try",
    "hinted",
    "hint_level",
    "confidence",
    "latency_ms",
    "diagnosis",
    "rule_id",
    "attempt_on_skill",
    "days_since_skill_practice",
)


def pseudonym(salt: str, student_id: uuid.UUID) -> str:
    """A stable, keyed stand-in for a learner. Without the salt it cannot be reversed or matched."""
    if len(salt) < MIN_SALT_CHARS:
        raise ValueError(f"the pilot salt must be at least {MIN_SALT_CHARS} characters")
    return hmac.new(salt.encode(), str(student_id).encode(), hashlib.sha256).hexdigest()[:16]


@dataclass
class _SkillClock:
    last_at: datetime | None = None
    attempts: int = 0


def attempts_for_student(
    rows: Iterable[tuple[EventRow, str]],
    catalog: Mapping[str, CatalogItem],
) -> list[dict[str, Any]]:
    """One row per judged answer, in log order. `rows` are (event, session type) already sorted."""
    clocks: dict[str, _SkillClock] = defaultdict(_SkillClock)
    helped: set[tuple[str, str]] = set()  # (session, item) that asked for help before answering
    answered: set[tuple[str, str]] = set()
    out: list[dict[str, Any]] = []
    for event, session_type in rows:
        item = catalog.get(event.item_id or "")
        if item is None:
            continue
        key = (str(event.session_id), item.id)
        at = as_utc(event.created_at)
        if event.event_type in HELP_EVENTS:
            helped.add(key)
            clocks[item.primary_skill].last_at = at
            continue
        if event.event_type != "answer" or event.correct is None:
            continue
        clock = clocks[item.primary_skill]
        payload = event.payload if isinstance(event.payload, dict) else {}
        diagnosis = payload.get("diagnosis")
        gap = None if clock.last_at is None else (at - clock.last_at).total_seconds() / 86_400
        first = key not in answered
        answered.add(key)
        clock.attempts += 1
        confidence = payload.get("confidence")
        out.append(
            {
                "at": at.isoformat(),
                "session_type": session_type,
                "pool": "warmup" if event.state_before == "warmup" else "practice",
                "skill_id": item.primary_skill,
                "item_id": item.id,
                "role": item.role,
                "difficulty": item.difficulty,
                "correct": bool(event.correct),
                "first_try": first,
                "hinted": key in helped,
                "hint_level": event.hint_level,
                "confidence": confidence if confidence in ("sure", "unsure") else "",
                "latency_ms": event.latency_ms,
                "diagnosis": diagnosis.get("class", "") if isinstance(diagnosis, dict) else "",
                "rule_id": event.rule_id or "",
                "attempt_on_skill": clock.attempts,
                "days_since_skill_practice": None if gap is None else round(gap, 3),
            }
        )
        clock.last_at = at
    return out


def bucket(days: float | None) -> str:
    """ "" for a review too soon to count, else "7d" or "21d"."""
    if days is None or days < RETEST_DAYS:
        return ""
    return "21d" if days >= LONG_RETEST_DAYS else "7d"


def is_retest(row: Mapping[str, Any]) -> bool:
    """A review of a skill left alone for a week or more, first go and without help."""
    return bool(
        row["pool"] == "warmup"
        and row["first_try"]
        and not row["hinted"]
        and bucket(row["days_since_skill_practice"])
    )


def retests(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {**row, "bucket": bucket(row["days_since_skill_practice"])}
        for row in rows
        if is_retest(row)
    ]


def summarise(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """The pilot's headline: how often the learners were right after a gap, against a normal day."""
    first_tries = [
        r for r in rows if r["first_try"] and not r["hinted"] and r["pool"] == "practice"
    ]
    summary: dict[str, Any] = {
        "answers": len(rows),
        "learners": len({r["pseudonym"] for r in rows if "pseudonym" in r}),
        "unhinted_first_try_practice": _rate(first_tries),
        "retests": {},
    }
    for name in ("7d", "21d"):
        summary["retests"][name] = _rate([r for r in retests(rows) if r["bucket"] == name])
    # Sure but wrong is the confident error the hypercorrection research is about.
    confident = [r for r in rows if r["first_try"] and r["confidence"] == "sure"]
    summary["sure_but_wrong"] = {
        "of_sure_answers": len(confident),
        "wrong": sum(1 for r in confident if not r["correct"]),
    }
    return summary


def _rate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    right = sum(1 for r in rows if r["correct"])
    return {"n": len(rows), "right": right, "rate": round(right / len(rows), 4) if rows else None}
