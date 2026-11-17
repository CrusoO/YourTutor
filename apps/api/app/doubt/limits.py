"""Per-student request windows for the doubt route, held in process memory only.

The key is the student id and it is never written anywhere: not to the database, not to a log. A
restart forgets it, which is the intended retention.
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque

HOUR = 3600.0
DAY = 86400.0
PER_HOUR = 30
PER_DAY = 150


class StudentWindow:
    def __init__(self, per_hour: int = PER_HOUR, per_day: int = PER_DAY) -> None:
        self.per_hour = per_hour
        self.per_day = per_day
        self._hits: dict[uuid.UUID, deque[float]] = defaultdict(deque)

    def allow(self, student_id: uuid.UUID, now: float | None = None) -> bool:
        moment = time.monotonic() if now is None else now
        q = self._hits[student_id]
        while q and moment - q[0] >= DAY:
            q.popleft()
        if len(q) >= self.per_day or sum(1 for t in q if moment - t < HOUR) >= self.per_hour:
            return False
        q.append(moment)
        return True

    def reset(self) -> None:
        self._hits.clear()


student_window = StudentWindow()
