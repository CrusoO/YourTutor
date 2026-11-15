"""The one place that knows where the frozen legacy content pack lives.

`content/` is the production root and is filled only by the content factory. The old Class 9
linear-equations draft pack (skills, items, lessons, passages, templates, ...) is kept as a test
fixture so the loader, validator, lesson player and review tools stay covered. Tests import
`LEGACY_CONTENT_ROOT`; CI asks for the path with `python -m tests.legacy_content`.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

LEGACY_CONTENT_ROOT = Path(__file__).resolve().parent / "fixtures" / "legacy_content"


def point_app_defaults_at_legacy_content(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make app code that defaults to the production root (lessons, source titles, the Ask
    eval harness) read the legacy fixture instead. Curricula still come from `content/`."""
    from app.lessons import sources

    monkeypatch.setattr("app.lessons.loader.content_root", lambda: LEGACY_CONTENT_ROOT)
    monkeypatch.setattr("app.ask.evals.content_root", lambda: LEGACY_CONTENT_ROOT)
    original: Callable[..., dict[str, str]] = sources.source_titles
    monkeypatch.setattr(
        sources, "source_titles", lambda root=None: original(root or LEGACY_CONTENT_ROOT)
    )


if __name__ == "__main__":
    print(LEGACY_CONTENT_ROOT)
