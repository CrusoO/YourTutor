"""Dev-only clock control, used to replay history for preview scenarios."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime

from app.auth import security
from app.config import settings


@contextmanager
def frozen(moment: datetime) -> Iterator[None]:
    """Make `now_utc()` return `moment` inside the block, then restore the previous clock."""
    if not settings.allow_draft_content:
        raise RuntimeError("clock override needs ALLOW_DRAFT_CONTENT=true (dev only)")
    previous = security.get_now_override()
    security.set_now_override(moment)
    try:
        yield
    finally:
        security.set_now_override(previous)
