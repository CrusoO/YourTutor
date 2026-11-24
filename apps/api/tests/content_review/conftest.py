from __future__ import annotations

from collections.abc import Iterator

import pytest

from app.content_review import service


@pytest.fixture(autouse=True)
def _fresh_items_cache() -> Iterator[None]:
    """A test must never see the loaded content of another test (or of the real content folder)."""
    service.clear_items_cache()
    yield
    service.clear_items_cache()
