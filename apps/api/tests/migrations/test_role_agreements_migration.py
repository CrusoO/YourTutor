"""Migration 0034 is idempotent: it can run on an old schema, and again on a new one (SQLite here;
Postgres in CI through the round-trip test and the same inspector checks)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

API_ROOT = Path(__file__).resolve().parents[2]
PATH = API_ROOT / "migrations" / "versions" / "0034_role_agreements.py"


def _load():
    spec = importlib.util.spec_from_file_location("m0034", PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _old_schema(engine: sa.engine.Engine) -> None:
    meta = sa.MetaData()
    sa.Table(
        "users", meta, sa.Column("id", sa.String, primary_key=True), sa.Column("email", sa.String)
    )
    sa.Table("students", meta, sa.Column("id", sa.String, primary_key=True))
    meta.create_all(engine)


def _run(engine: sa.engine.Engine, step: str) -> None:
    module = _load()
    with engine.begin() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            getattr(module, step)()


def _state(engine: sa.engine.Engine) -> dict[str, set[str]]:
    insp = sa.inspect(engine)
    out = {t: {c["name"] for c in insp.get_columns(t)} for t in insp.get_table_names()}
    out["_indexes"] = {
        i["name"] for t in insp.get_table_names() for i in insp.get_indexes(t) if i["name"]
    }
    return out


def test_upgrade_adds_everything_and_can_run_twice() -> None:
    engine = sa.create_engine("sqlite://")
    _old_schema(engine)
    _run(engine, "upgrade")
    first = _state(engine)
    assert {"phone"} <= first["users"]
    assert {"is_adult", "birth_year", "username"} <= first["students"]
    assert {"agreement_acceptances", "guardian_approvals"} <= set(first)
    assert {"ix_users_phone", "ix_students_username", "ix_guardian_approvals_token_hash"} <= first[
        "_indexes"
    ]
    _run(engine, "upgrade")  # a second run finds it all done
    assert _state(engine) == first


def test_downgrade_removes_it_and_can_run_twice() -> None:
    engine = sa.create_engine("sqlite://")
    _old_schema(engine)
    _run(engine, "upgrade")
    _run(engine, "downgrade")
    after = _state(engine)
    assert "phone" not in after["users"] and "agreement_acceptances" not in after
    assert not {"is_adult", "birth_year", "username"} & after["students"]
    _run(engine, "downgrade")
    assert _state(engine) == after


def test_the_models_and_the_migration_agree_on_the_new_columns() -> None:
    from app.db.models import AgreementRow, GuardianApprovalRow

    engine = sa.create_engine("sqlite://")
    _old_schema(engine)
    _run(engine, "upgrade")
    state = _state(engine)
    assert {c.key for c in AgreementRow.__table__.columns} == state["agreement_acceptances"]
    assert {c.key for c in GuardianApprovalRow.__table__.columns} == state["guardian_approvals"]
