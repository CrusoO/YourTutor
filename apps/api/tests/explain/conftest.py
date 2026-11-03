from __future__ import annotations

from collections.abc import Iterator

import pytest

from app.explain import lesson_cache


@pytest.fixture(autouse=True)
def _fresh_lesson_cache() -> Iterator[None]:
    """A lesson cached by one test must never answer another."""
    lesson_cache.clear()
    yield
    lesson_cache.clear()
