"""Let the video worker sleep until there is work, instead of asking the database every few seconds.

On a free hosted database every query keeps the database awake, and a 5-second poll uses up a
month's free hours in about two weeks. With VIDEO_WAKE_FILE set, the API touches that file when it
queues a job, and an idle worker only looks at the database when the file changes, plus once every
VIDEO_WORKER_IDLE_POLL_SECONDS as a safety net (set that above 5 minutes so the database can sleep).
Both must run on the same machine; without the setting, nothing changes: the worker polls as before.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from pathlib import Path

SLICE_SECONDS = 0.5  # how often an idle worker looks at the file (a stat call, not a query)


def touch(path: str) -> None:
    """Mark that a job was queued. Never raises: a missing wake file only slows the worker down."""
    if not path:
        return
    try:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch()
        now = time.time()
        os.utime(target, (now, now))
    except OSError:
        return


def stamp(path: str) -> float:
    """The file's last-change time, or 0.0 when there is no file."""
    if not path:
        return 0.0
    try:
        return os.stat(path).st_mtime
    except OSError:
        return 0.0


def wait_for_work(
    path: str,
    seen: float,
    idle_seconds: float,
    *,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> float:
    """Sleep until the wake file changes or `idle_seconds` pass; return the file's new stamp.

    Without a wake file this is just a sleep of `idle_seconds`, the old behaviour.
    """
    if not path:
        sleep(idle_seconds)
        return 0.0
    deadline = clock() + idle_seconds
    while clock() < deadline:
        current = stamp(path)
        if current != seen:
            return current
        sleep(min(SLICE_SECONDS, max(0.0, deadline - clock())))
    return stamp(path)
