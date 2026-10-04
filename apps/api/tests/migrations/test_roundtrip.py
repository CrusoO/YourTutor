"""Alembic downgrade to the pre-G0 revision and back to head, with data present."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.auth.security import now_utc
from app.db.models import OverlayRow, StudentRow, UserRow

API_ROOT = Path(__file__).resolve().parents[2]
PRE_G0_REVISION = "0008_retire"


def _postgres_url() -> str | None:
    url = os.environ.get("TEST_DATABASE_URL", "")
    if url.startswith("postgresql"):
        return url
    candidate = "postgresql+psycopg://tutor:tutor@localhost:5432/yourtutor_test"
    try:
        engine = create_engine(candidate, future=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return candidate
    except OperationalError:
        return None


def _config(url: str) -> Config:
    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    cfg.attributes["database_url"] = url
    return cfg


def _tables(engine: Engine) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        )
        return {row[0] for row in rows}


@pytest.mark.postgres
def test_downgrade_to_pre_g0_and_upgrade_to_head_keeps_data() -> None:
    url = _postgres_url()
    if url is None:
        pytest.skip("Postgres is not available")
    engine = create_engine(url, future=True)
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    cfg = _config(url)
    command.upgrade(cfg, "head")
    registry = {"locales", "curricula", "books", "chapters", "sections"}
    assert registry <= _tables(engine)

    parent_id = uuid.uuid4()
    ids = {"bhutan": uuid.uuid4(), "seba": uuid.uuid4()}
    factory = sessionmaker(bind=engine, future=True)
    with factory() as session:
        session.add(
            UserRow(
                id=parent_id,
                role="parent",
                email="roundtrip@example.com",
                locale="en",
                created_at=now_utc(),
            )
        )
        session.flush()
        for board, student_id in ids.items():
            session.add(
                StudentRow(
                    id=student_id,
                    parent_id=parent_id,
                    display_name=f"Kid {board}",
                    grade=9,
                    board=board,
                    curriculum_id=board,
                    book_id=f"{board}_class9",
                    context_key={
                        "curriculum_id": board,
                        "book_id": f"{board}_class9",
                        "chapter_id": f"{board}_class9",
                    },
                    home_language="en",
                    exam_language="en",
                    timezone="Asia/Thimphu",
                    created_at=now_utc(),
                )
            )
        session.add(
            OverlayRow(
                id="OV.ROUNDTRIP",
                board="bhutan",
                grade=9,
                chapter="linear_equations",
                skill_ids=["MATH.X"],
                live=False,
            )
        )
        session.commit()

    command.downgrade(cfg, PRE_G0_REVISION)
    after_down = _tables(engine)
    assert not {"locales", "curricula", "books", "chapters", "sections"} & after_down
    with engine.connect() as conn:
        cols = {
            row[0]
            for row in conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'students'"
                )
            )
        }
        assert {"curriculum_id", "book_id", "context_key"}.isdisjoint(cols)
        names = {
            row[0] for row in conn.execute(text("SELECT display_name FROM students ORDER BY 1"))
        }
        assert names == {"Kid bhutan", "Kid seba"}
        assert conn.execute(text("SELECT count(*) FROM overlays")).scalar_one() == 1
        assert conn.execute(text("SELECT count(*) FROM users")).scalar_one() == 1

    command.upgrade(cfg, "head")
    assert registry <= _tables(engine)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM sections")).scalar_one() >= 9
        assert conn.execute(text("SELECT section_map FROM overlays")).scalar_one() == {}
        rows = conn.execute(
            text("SELECT board, curriculum_id, book_id, context_key FROM students ORDER BY board")
        ).all()
        assert [(r.board, r.curriculum_id, r.book_id) for r in rows] == [
            ("bhutan", "bhutan", "bhutan_class9"),
            ("seba", "seba", "seba_class9"),
        ]
        for row in rows:
            assert row.context_key["curriculum_id"] == row.curriculum_id
        assert conn.execute(text("SELECT count(*) FROM overlays")).scalar_one() == 1
        assert conn.execute(text("SELECT count(*) FROM locales")).scalar_one() >= 3
        assert conn.execute(text("SELECT count(*) FROM curricula")).scalar_one() >= 3
    engine.dispose()
