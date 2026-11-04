"""The start-up check that the database is at the version the code expects."""

from __future__ import annotations

import logging
import re

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.db import schema_check
from app.db.schema_check import behind, check_schema, current_revision, head_revision


def _engine(revision: str | None) -> Engine:
    engine = create_engine("sqlite://")
    if revision is not None:
        with engine.begin() as conn:
            conn.execute(text("create table alembic_version (version_num varchar(64))"))
            conn.execute(text("insert into alembic_version values (:v)"), {"v": revision})
    return engine


def test_the_head_is_a_numbered_migration() -> None:
    assert re.match(r"^\d{4}_", head_revision())


def test_behind_means_a_version_that_is_not_the_head() -> None:
    assert behind("0026_vj_video_jobs", "0029_lesson_records")
    assert not behind("0029_lesson_records", "0029_lesson_records")
    assert not behind(None, "0029_lesson_records")  # no version table: nothing to compare
    assert not behind("0026", "")


def test_a_database_without_a_version_table_is_left_alone() -> None:
    assert current_revision(_engine(None)) is None
    assert check_schema(_engine(None), production=True, auto_migrate=False) is None


def test_an_up_to_date_database_passes_in_production() -> None:
    engine = _engine(head_revision())
    assert check_schema(engine, production=True, auto_migrate=False) is None


def test_production_refuses_to_start_on_a_database_that_is_behind() -> None:
    with pytest.raises(RuntimeError, match="0026_old.*alembic upgrade head"):
        check_schema(_engine("0026_old"), production=True, auto_migrate=False)


def test_elsewhere_a_database_that_is_behind_is_reported_not_fatal(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.ERROR, logger="yourtutor.schema"):
        message = check_schema(_engine("0026_old"), production=False, auto_migrate=False)
    assert message is not None and "0026_old" in message
    assert "will fail" in caplog.text


def test_auto_migrate_runs_the_upgrade_instead_of_failing(monkeypatch: pytest.MonkeyPatch) -> None:
    ran: list[bool] = []
    monkeypatch.setattr(schema_check, "migrate", lambda: ran.append(True))
    assert check_schema(_engine("0026_old"), production=True, auto_migrate=True) is None
    assert ran == [True]
