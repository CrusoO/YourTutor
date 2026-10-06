from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.auth.security import now_utc
from app.config import settings
from app.dev.clock import frozen

PAST = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


def test_now_utc_is_real_time_by_default() -> None:
    assert abs(now_utc() - datetime.now(UTC)) < timedelta(seconds=5)


def test_frozen_clock_overrides_now_and_restores() -> None:
    settings.allow_draft_content = True
    with frozen(PAST):
        assert now_utc() == PAST
        with frozen(PAST + timedelta(days=1)):
            assert now_utc() == PAST + timedelta(days=1)
        assert now_utc() == PAST
    assert abs(now_utc() - datetime.now(UTC)) < timedelta(seconds=5)


def test_frozen_clock_restores_even_after_an_error() -> None:
    settings.allow_draft_content = True
    with pytest.raises(RuntimeError, match="boom"):
        with frozen(PAST):
            raise RuntimeError("boom")
    assert abs(now_utc() - datetime.now(UTC)) < timedelta(seconds=5)


def test_clock_override_refused_unless_draft_content_is_allowed() -> None:
    settings.allow_draft_content = False
    with pytest.raises(RuntimeError, match="ALLOW_DRAFT_CONTENT"):
        with frozen(PAST):
            pass
    assert abs(now_utc() - datetime.now(UTC)) < timedelta(seconds=5)
