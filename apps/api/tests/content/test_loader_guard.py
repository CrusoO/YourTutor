"""Loading must never treat a missing or empty content root as 'delete everything'."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.config import settings
from app.content.loader import LoadError, load_path
from app.db.models import ItemRow, SkillRow
from app.db.session import session_factory
from app.registries.paths import repo_root


def _counts(url: str) -> tuple[int, int]:
    with session_factory(url)() as db:
        items = db.scalar(select(func.count()).select_from(ItemRow)) or 0
        skills = db.scalar(select(func.count()).select_from(SkillRow)) or 0
        return items, skills


def test_missing_content_root_is_refused_and_nothing_is_deleted(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'guard.db'}"
    load_path(repo_root() / "content", database_url=url)
    before = _counts(url)
    assert before[0] > 0
    settings.allow_draft_content = True  # the mode that hard-deletes orphans
    with pytest.raises(LoadError, match="does not exist"):
        load_path(tmp_path / "no_such_folder", database_url=url)
    assert _counts(url) == before


def test_empty_content_root_is_refused_and_nothing_is_deleted(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'guard2.db'}"
    load_path(repo_root() / "content", database_url=url)
    before = _counts(url)
    empty = tmp_path / "empty"
    empty.mkdir()
    settings.allow_draft_content = True
    with pytest.raises(LoadError, match="no skills or items"):
        load_path(empty, database_url=url)
    assert _counts(url) == before
