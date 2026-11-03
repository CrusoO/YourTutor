"""Is the database at the version this code expects?

The app does not migrate the database when it starts, so a new container on an old database fails
later, in the middle of a request, with a 500 on whatever table is new. This checks once at start-up
instead. In production a database that is behind stops the app with a clear message; anywhere else
it is logged loudly, and `AUTO_MIGRATE=true` brings the database up to date first.

A database with no `alembic_version` table (the test database, built straight from the models) is
left alone: there is nothing to compare.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger("yourtutor.schema")
API_ROOT = Path(__file__).resolve().parents[2]


def head_revision() -> str:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_ROOT / "migrations"))
    return ScriptDirectory.from_config(cfg).get_current_head() or ""


def current_revision(engine: Engine) -> str | None:
    """The database's revision, or None when it has no alembic_version table."""
    try:
        with engine.connect() as conn:
            return conn.execute(text("select version_num from alembic_version")).scalar()
    except Exception:  # noqa: BLE001 - no table, or no database: nothing to compare
        return None


def behind(revision: str | None, head: str) -> bool:
    """True only when the database has a version and it is not the code's head."""
    return revision is not None and bool(head) and revision != head


def migrate() -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_ROOT / "migrations"))
    command.upgrade(cfg, "head")


def check_schema(engine: Engine, *, production: bool, auto_migrate: bool) -> str | None:
    """Returns a message when the database is behind and was left that way, else None.

    Raises RuntimeError in production when the database is behind and AUTO_MIGRATE is off.
    """
    revision, head = current_revision(engine), head_revision()
    if not behind(revision, head):
        return None
    if auto_migrate:
        logger.warning("database at %s, code expects %s: migrating", revision, head)
        migrate()
        return None
    message = (
        f"the database is at migration {revision} but this code expects {head}: "
        "run `alembic upgrade head`, or set AUTO_MIGRATE=true"
    )
    if production:
        raise RuntimeError(f"Refusing to start: {message}.")
    logger.error("WARNING: %s. Requests to newer tables will fail.", message)
    return message
