"""Operator checks: `python -m app.operator check`.

Answers "is this install ready for a pilot?" with one line per check: the database answers, the
migrations are at head, content is loaded, the jurisdiction profile is valid, production switches
are safe, and the jobs have what they need. Exit code 0 only when nothing failed.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

from app.config import DEFAULT_DB_PASSWORD, settings
from app.db.session import session_factory
from app.registries.startup import validate_startup_config

PRODUCTION = "production"


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str


def _head_revision() -> str:
    from pathlib import Path

    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "migrations"))
    return ScriptDirectory.from_config(cfg).get_current_head() or ""


def run_checks() -> list[Check]:
    checks: list[Check] = []
    counts: dict[str, int] = {}
    try:
        with session_factory()() as db:
            db.execute(text("select 1"))
            checks.append(Check("database", True, "answers"))
            revision = db.execute(text("select version_num from alembic_version")).scalar()
            head = _head_revision()
            checks.append(Check("migrations", revision == head, f"at {revision}, head is {head}"))
            for table in ("skills", "items", "lessons", "passages", "overlays"):
                counts[table] = int(db.execute(text(f"select count(*) from {table}")).scalar() or 0)
    except Exception as exc:  # noqa: BLE001 - any failure is the answer to "is it ready?"
        checks.append(Check("database", False, f"{type(exc).__name__}: {exc}"[:200]))
    if counts:
        loaded = counts.get("items", 0) > 0 and counts.get("overlays", 0) > 0
        detail = ", ".join(f"{k} {v}" for k, v in counts.items())
        checks.append(Check("content loaded", loaded, detail))
    try:
        validate_startup_config()
        checks.append(Check("jurisdiction profile", True, settings.jurisdiction_profile))
    except Exception as exc:  # noqa: BLE001
        checks.append(Check("jurisdiction profile", False, str(exc)[:200]))
    prod = settings.app_env.lower() == PRODUCTION
    checks.append(
        Check(
            "draft content off in production",
            not (prod and settings.allow_draft_content),
            f"APP_ENV={settings.app_env}, ALLOW_DRAFT_CONTENT={settings.allow_draft_content}",
        )
    )
    checks.append(
        Check(
            "dev tools off in production",
            not (prod and settings.dev_tools),
            f"DEV_TOOLS={settings.dev_tools}",
        )
    )
    checks.append(
        Check(
            "token pepper changed",
            not (prod and settings.token_pepper == "dev-only-change-me"),
            "TOKEN_PEPPER is set" if settings.token_pepper != "dev-only-change-me" else "default",
        )
    )
    checks.append(
        Check(
            "database password changed",
            not (prod and settings.postgres_password == DEFAULT_DB_PASSWORD),
            "POSTGRES_PASSWORD is set"
            if settings.postgres_password != DEFAULT_DB_PASSWORD
            else "default",
        )
    )
    checks.append(
        Check(
            "email for codes and reports",
            bool(settings.smtp_host) or not prod,
            "SMTP_HOST set" if settings.smtp_host else "codes and reports only go to the log",
        )
    )
    checks.append(
        Check("rate limits on", settings.rate_limit_enabled, str(settings.rate_limit_enabled))
    )
    return checks


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if args != ["check"]:
        print("usage: python -m app.operator check", file=sys.stderr)
        return 2
    results = run_checks()
    for check in results:
        print(f"{'ok  ' if check.ok else 'FAIL'} {check.name}: {check.detail}")
    failed = [c for c in results if not c.ok]
    print(f"{len(results) - len(failed)} of {len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
