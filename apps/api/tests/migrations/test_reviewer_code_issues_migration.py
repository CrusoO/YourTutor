"""Migration 0040 is idempotent, reversible, and agrees with the model."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from app.db.models import ReviewerCodeIssueRow

PATH = Path(__file__).resolve().parents[2] / "migrations" / "versions"
PATH = PATH / "0040_reviewer_code_issues.py"
TABLE = "reviewer_code_issues"


def _load():
    spec = importlib.util.spec_from_file_location("m0040", PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(engine: sa.engine.Engine, step: str) -> None:
    with engine.begin() as conn, Operations.context(MigrationContext.configure(conn)):
        getattr(_load(), step)()


def test_upgrade_downgrade_upgrade_on_sqlite() -> None:
    engine = sa.create_engine("sqlite://")
    _run(engine, "upgrade")
    _run(engine, "upgrade")  # idempotent
    assert TABLE in sa.inspect(engine).get_table_names()
    columns = {c["name"] for c in sa.inspect(engine).get_columns(TABLE)}
    assert columns == {c.key for c in ReviewerCodeIssueRow.__table__.columns}
    _run(engine, "downgrade")
    _run(engine, "downgrade")
    assert TABLE not in sa.inspect(engine).get_table_names()
    _run(engine, "upgrade")
    assert TABLE in sa.inspect(engine).get_table_names()


def test_chain_is_linear() -> None:
    assert _load().down_revision == "0039_reviewer_desk"
