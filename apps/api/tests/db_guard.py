"""A guard for the one thing the suite does that cannot be undone: dropping every table in
the database TEST_DATABASE_URL names.

A database is allowed when it is SQLite, when its name contains "_test", when the run is in
CI (a throwaway service container), or when the person running the tests names that exact
database in ALLOW_TEST_DATABASE_WIPE. Anything else is refused, and the message names the
database but never the password.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class UnsafeTestDatabase(RuntimeError):
    pass


def assert_safe_test_database(url: str, environ: Mapping[str, str] | None = None) -> None:
    env = os.environ if environ is None else environ
    try:
        parsed = make_url(url)
    except ArgumentError as exc:
        raise UnsafeTestDatabase("TEST_DATABASE_URL is not a database URL") from exc
    if parsed.get_backend_name() == "sqlite":
        return
    name = parsed.database or ""
    if "_test" in name:
        return
    if env.get("CI", "").lower() in {"1", "true", "yes"}:
        return
    if name and env.get("ALLOW_TEST_DATABASE_WIPE") == name:
        return
    raise UnsafeTestDatabase(
        f"the tests drop every table, and the database '{name}' is not a test database "
        "(its name has no '_test'). Point TEST_DATABASE_URL at one such as yourtutor_test, "
        f"or set ALLOW_TEST_DATABASE_WIPE={name} if you really mean this one."
    )
