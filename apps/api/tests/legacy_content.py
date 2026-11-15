"""The one place that knows where the frozen legacy content pack lives.

`content/` is the production root and is filled only by the content factory. The old Class 9
linear-equations draft pack (skills, items, lessons, passages, templates, ...) is kept as a test
fixture so the loader, validator, lesson player and review tools stay covered. Tests import
`LEGACY_CONTENT_ROOT`; CI asks for the path with `python -m tests.legacy_content`.
"""

from __future__ import annotations

from pathlib import Path

LEGACY_CONTENT_ROOT = Path(__file__).resolve().parent / "fixtures" / "legacy_content"


if __name__ == "__main__":
    print(LEGACY_CONTENT_ROOT)
