from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import OperationalError

from app.content.loader import load_path
from app.db.models import ItemRow, LessonRow, SceneRow, SkillRow, WidgetRow
from app.db.session import session_factory

API_ROOT = Path(__file__).resolve().parents[2]

CONTENT = Path(__file__).resolve().parents[4] / "content"


def _postgres_url() -> str | None:
    if os.environ.get("TEST_DATABASE_URL", "").startswith("postgresql"):
        return os.environ["TEST_DATABASE_URL"]
    candidate = "postgresql+psycopg://tutor:tutor@127.0.0.1:5432/yourtutor_test"
    try:
        engine = create_engine(candidate, future=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return candidate
    except OperationalError:
        return None


@pytest.mark.postgres
def test_load_seed_postgres() -> None:
    url = _postgres_url()
    if url is None:
        pytest.skip("Postgres is not available")
    engine = create_engine(url, future=True)
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    cfg.attributes["database_url"] = url
    command.upgrade(cfg, "head")
    from app.db.models import Base

    Base.metadata.create_all(engine)
    load_path(CONTENT, database_url=url)
    factory = session_factory(url)
    with factory() as session:
        skills = session.scalars(select(SkillRow)).all()
        items = session.scalars(select(ItemRow)).all()
        assert len(skills) == 12
        assert len(items) == 406
        lessons = session.scalars(select(LessonRow)).all()
        assert len(lessons) == 4
        assert all(row.source_ref and row.status == "draft" for row in lessons)
        scenes = session.scalars(select(SceneRow)).all()
        widgets = session.scalars(select(WidgetRow)).all()
        assert scenes and widgets
        assert all(row.source_ref and row.kb_per_minute > 0 for row in scenes)
        assert {row.lesson_id for row in scenes} <= {row.id for row in lessons}
        assert {row.type for row in widgets} <= {"balance_scale", "function_graph"}
    engine.dispose()
