"""Spending limits for an API that strangers can use: model calls a day, and the video queue.

Opening "ask anything" to visitors with no account means anyone can spend the owner's model and
render budget. These limits are the brake, all set from the environment so the owner decides:

- LLM_DAILY_CAP: the most model-backed requests (lessons, stories, explanations, chat) the whole
  API serves in one UTC day. 0 turns it off. Held in this process, which is right for one API
  process and a floor, not a ceiling, for several.
- VIDEO_QUEUE_MAX: the most video jobs that may wait in the queue at once. 0 turns it off.
- VIDEO_JOBS_PER_DAY (signed in) and VIDEO_JOBS_PER_DAY_GUEST: the most jobs one learner may
  start in 24 hours. A guest is a hidden account and starting guests is limited per address, so
  this holds a person to a small number without needing their address here.

Over a limit the answer is a plain "busy" the page already knows how to show, never an error.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import VideoJobRow


class DailyBudget:
    """A counter that starts again each UTC day."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._day: str = ""
        self._used = 0

    def charge(self, limit: int, now: datetime | None = None) -> bool:
        """True when this request may go ahead (and is counted). Always True when `limit` is 0."""
        if limit <= 0:
            return True
        today = (now or datetime.now(UTC)).strftime("%Y-%m-%d")
        with self._lock:
            if today != self._day:
                self._day, self._used = today, 0
            if self._used >= limit:
                return False
            self._used += 1
            return True

    def used(self) -> int:
        with self._lock:
            return self._used

    def reset(self) -> None:
        with self._lock:
            self._day, self._used = "", 0


llm_budget = DailyBudget()


def video_queue_full(db: Session, limit: int) -> bool:
    if limit <= 0:
        return False
    waiting = db.scalar(
        select(func.count()).select_from(VideoJobRow).where(VideoJobRow.status == "queued")
    )
    return int(waiting or 0) >= limit


def video_jobs_today(db: Session, student_id: object, now: datetime | None = None) -> int:
    since = (now or datetime.now(UTC)) - timedelta(hours=24)
    count = db.scalar(
        select(func.count())
        .select_from(VideoJobRow)
        .where(VideoJobRow.student_id == student_id, VideoJobRow.created_at >= since)
    )
    return int(count or 0)
