from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

from app.content.loader import load_path
from app.db.models import ItemRow, SkillRow
from app.db.session import session_factory


def test_load_sqlite(content_root: Path, tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'content.db'}"
    load_path(content_root, database_url=url)
    factory = session_factory(url)
    with factory() as session:
        skills = session.scalars(select(SkillRow)).all()
        items = session.scalars(select(ItemRow)).all()
        assert len(skills) == 1
        assert items[0].primary_skill == "MATH.S1"
