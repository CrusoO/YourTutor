"""Baseline numbers (Plan A, slice A0): a read-only look at how sessions go today.

Everything is computed from rows that already exist (`sessions`, `events`); nothing is written and
no event shape changes. The report is aggregate only: no student id, name or free text leaves this
module, and any cell backed by fewer than `MIN_STUDENTS` distinct students is replaced by
`SUPPRESSED` ("n<20").

Window: sessions whose `started_at` UTC date lies in [since, until], both inclusive. Only sessions
of `session_type` count (default "practice", as in pilot.py; "all" keeps every type). The same
filter applies to the first-session date used for day-N return.

Definitions
- Answer: an event with `event_type == "answer"`. Time-to-first-answer is first answer
  `created_at` minus session `started_at`; sessions with no answer are left out, and so are
  negative gaps (clock skew from offline sync).
- Time-to-first-correct: the same, for the first answer with `correct is True`.
- Hints per answered item: for every (session, item) with at least one answer event, the count of
  `request_help` / `request_hint` events on that item in that session. Hints on items never
  answered are not counted. Distribution buckets: 0, 1, 2, 3+.
- Completion: a session "reached its planned end" when `ended_at` is set and `ended_reason` is one
  of PLANNED_ENDS (chapter, diagnostic or checkpoint finished, or a soft/hard cap). Other
  `ended_at` values (idle, break, day_rollover, superseded, consent_revoked, or no reason) are
  "ended early". A session with no `ended_at` is "never ended": the app records no idle expiry
  for it, so abandoned and still-open sessions cannot be told apart. Completion rate is planned
  ends over all sessions.
- Day-N return: day 0 is the UTC date of the student's first session ever. Only students whose
  day 0 is inside the window and whose day-N date is on or before `until` are counted; they return
  if they have any session starting on exactly day 0 + N.

Not measured here: hint dwell (how long a hint stayed on screen), which representation was shown,
confidence (`payload.confidence` is not read), and any time spent outside recorded events.
Guest, demo and test students: `students` has no reliable flag for them, so none are excluded.
Run against a database that holds only real learners (or a filtered copy).
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import as_utc
from app.db.models import EventRow, SessionRow

MIN_STUDENTS = 20
SUPPRESSED = "n<20"
PLANNED_ENDS = frozenset(
    {"chapter_complete", "diagnostic_complete", "checkpoint_complete", "soft_cap", "hard_cap"}
)
HINT_EVENTS = frozenset({"request_help", "request_hint"})
RETURN_DAYS = (1, 7)
DEFAULT_SESSION_TYPE = "practice"  # same as pilot.py; "all" keeps every type

NOT_MEASURED = (
    "hint dwell (time a hint stayed on screen)",
    "which representation was shown or used",
    "confidence (payload.confidence is not read)",
    "idle expiry of sessions that never ended (abandoned vs still open)",
    "guest/demo/test students (no reliable flag, none excluded)",
)


def suppress(value: Any, students: int) -> Any:
    """Return `value` only when at least MIN_STUDENTS students stand behind it."""
    return value if students >= MIN_STUDENTS else SUPPRESSED


def _percentile(sorted_vals: Sequence[float], q: float) -> float:
    """Nearest-rank percentile of a non-empty sorted list."""
    rank = max(1, math.ceil(q * len(sorted_vals)))
    return sorted_vals[rank - 1]


def _type_filter(session_type: str) -> list[Any]:
    return [] if session_type == "all" else [SessionRow.type == session_type]


def _window_bounds(since: date, until: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(since, time.min, tzinfo=UTC),
        datetime.combine(until + timedelta(days=1), time.min, tzinfo=UTC),
    )


def _duration_cell(samples: list[tuple[object, float]]) -> dict[str, Any]:
    students = len({s for s, _ in samples})
    vals = sorted(v for _, v in samples)
    if not vals:
        return {"sessions": 0, "students": 0, "median_s": None, "p90_s": None}
    return {
        "sessions": suppress(len(vals), students),
        "students": students,
        "median_s": suppress(round(_percentile(vals, 0.5), 1), students),
        "p90_s": suppress(round(_percentile(vals, 0.9), 1), students),
    }


def baseline_metrics(
    db: Session, since: date, until: date, session_type: str = DEFAULT_SESSION_TYPE
) -> dict[str, Any]:
    if until < since:
        raise ValueError("until must not be before since")
    start, end = _window_bounds(since, until)
    sessions = db.execute(
        select(
            SessionRow.id,
            SessionRow.student_id,
            SessionRow.started_at,
            SessionRow.ended_at,
            SessionRow.ended_reason,
        ).where(
            SessionRow.started_at >= start,
            SessionRow.started_at < end,
            *_type_filter(session_type),
        )
    ).all()
    by_id = {s.id: s for s in sessions}

    first_answer: dict[object, datetime] = {}
    first_correct: dict[object, datetime] = {}
    answered: set[tuple[object, str]] = set()
    hints: dict[tuple[object, str], int] = defaultdict(int)
    if by_id:
        events = db.execute(
            select(
                EventRow.session_id,
                EventRow.item_id,
                EventRow.event_type,
                EventRow.correct,
                EventRow.created_at,
            ).where(EventRow.session_id.in_(list(by_id)))
        ).all()
        for ev in events:
            key = (ev.session_id, ev.item_id or "")
            at = as_utc(ev.created_at)
            if ev.event_type == "answer":
                answered.add(key)
                if ev.session_id not in first_answer or at < first_answer[ev.session_id]:
                    first_answer[ev.session_id] = at
                if ev.correct is True and (
                    ev.session_id not in first_correct or at < first_correct[ev.session_id]
                ):
                    first_correct[ev.session_id] = at
            elif ev.event_type in HINT_EVENTS and ev.item_id:
                hints[key] += 1

    def gaps(firsts: dict[object, datetime]) -> list[tuple[object, float]]:
        out: list[tuple[object, float]] = []
        for sid, at in firsts.items():
            s = by_id[sid]
            gap = (at - as_utc(s.started_at)).total_seconds()
            if gap >= 0:
                out.append((s.student_id, gap))
        return out

    # Hints per answered item (items with an id only).
    counts = [hints.get(key, 0) for key in answered if key[1]]
    item_students = len({by_id[k[0]].student_id for k in answered if k[1]})
    hint_cell: dict[str, Any] = {"items": 0, "students": 0, "mean": None, "distribution": None}
    if counts:
        buckets = {"0": 0, "1": 0, "2": 0, "3+": 0}
        for n in counts:
            buckets[str(n) if n < 3 else "3+"] += 1
        hint_cell = {
            "items": suppress(len(counts), item_students),
            "students": item_students,
            "mean": suppress(round(sum(counts) / len(counts), 3), item_students),
            "distribution": suppress(buckets, item_students),
        }

    # Completion.
    n_students = len({s.student_id for s in sessions})
    planned = sum(1 for s in sessions if s.ended_at and s.ended_reason in PLANNED_ENDS)
    never = sum(1 for s in sessions if s.ended_at is None)
    total = len(sessions)
    completion: dict[str, Any] = {
        "students": n_students,
        "sessions": 0,
        "reached_planned_end": None,
        "ended_early": None,
        "never_ended": None,
        "completion_rate": None,
    }
    if total:
        completion.update(
            sessions=suppress(total, n_students),
            reached_planned_end=suppress(planned, n_students),
            ended_early=suppress(total - planned - never, n_students),
            never_ended=suppress(never, n_students),
            completion_rate=suppress(round(planned / total, 4), n_students),
        )

    return {
        "window": {
            "since": since.isoformat(),
            "until": until.isoformat(),
            "session_type": session_type,
        },
        "sessions_in_window": suppress(total, n_students) if total else 0,
        "students_in_window": suppress(n_students, n_students) if total else 0,
        "time_to_first_answer": _duration_cell(gaps(first_answer)),
        "time_to_first_correct": _duration_cell(gaps(first_correct)),
        "hints_per_answered_item": hint_cell,
        "completion": completion,
        "return": _returns(db, since, until, session_type),
        "not_measured": list(NOT_MEASURED),
    }


def _returns(db: Session, since: date, until: date, session_type: str) -> dict[str, Any]:
    """Day-N return for students whose first-ever session date is in the window."""
    _, end = _window_bounds(since, until)
    dates: dict[object, set[date]] = defaultdict(set)
    for student_id, started_at in db.execute(
        select(SessionRow.student_id, SessionRow.started_at).where(*_type_filter(session_type))
    ).all():
        if as_utc(started_at) < end:  # later sessions never matter: day-N is capped at `until`
            dates[student_id].add(as_utc(started_at).date())
    out: dict[str, Any] = {}
    for n in RETURN_DAYS:
        eligible = returned = 0
        for days in dates.values():
            day0 = min(days)
            if not (since <= day0 <= until) or day0 + timedelta(days=n) > until:
                continue
            eligible += 1
            returned += (day0 + timedelta(days=n)) in days
        out[f"day_{n}"] = {
            "eligible_students": suppress(eligible, eligible) if eligible else 0,
            "returned": suppress(returned, eligible) if eligible else 0,
            "rate": suppress(round(returned / eligible, 4), eligible) if eligible else None,
        }
    return out


def render_table(report: dict[str, Any]) -> str:
    def f(v: Any) -> str:
        return "-" if v is None else str(v)

    w = report["window"]
    t1, t2 = report["time_to_first_answer"], report["time_to_first_correct"]
    h, c, r = report["hints_per_answered_item"], report["completion"], report["return"]
    rows = [
        ("window (UTC dates)", f"{w['since']} .. {w['until']}, sessions: {w['session_type']}"),
        (
            "sessions / students",
            f"{f(report['sessions_in_window'])} / {f(report['students_in_window'])}",
        ),
        ("first answer, median / p90 (s)", f"{f(t1['median_s'])} / {f(t1['p90_s'])}"),
        ("first correct, median / p90 (s)", f"{f(t2['median_s'])} / {f(t2['p90_s'])}"),
        ("hints per answered item, mean", f(h["mean"])),
        ("hints distribution 0/1/2/3+", f(h["distribution"])),
        (
            "planned end / ended early / never ended",
            f"{f(c['reached_planned_end'])} / {f(c['ended_early'])} / {f(c['never_ended'])}",
        ),
        ("completion rate (planned end)", f(c["completion_rate"])),
    ]
    for n in RETURN_DAYS:
        d = r[f"day_{n}"]
        rows.append(
            (
                f"day-{n} return rate (returned of eligible)",
                f"{f(d['rate'])} ({f(d['returned'])} of {f(d['eligible_students'])})",
            )
        )
    width = max(len(a) for a, _ in rows)
    lines = [f"{a.ljust(width)}  {b}" for a, b in rows]
    lines.append("")
    lines.append("Not measured: " + "; ".join(report["not_measured"]) + ".")
    lines.append(f"Cells backed by fewer than {MIN_STUDENTS} students show '{SUPPRESSED}'.")
    return "\n".join(lines)
