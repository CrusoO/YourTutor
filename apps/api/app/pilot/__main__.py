"""`python -m app.pilot export --out DIR`: the pilot's answers and delayed retests, as CSV.

Read-only. Only learners whose guardian (or who themselves, as an adult) agreed to the
`research_pseudonymised` scope are included; a guest never is. Each learner appears as a keyed
pseudonym: set PILOT_EXPORT_SALT (at least 16 characters, kept outside the repository). Nothing
here prints a name, an email or a real id.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from sqlalchemy import select

from app.auth.consent import has_scope
from app.config import settings
from app.db.models import EventRow, SessionRow, StudentRow
from app.db.session import session_factory
from app.pilot.export import (
    ATTEMPT_COLUMNS,
    MIN_SALT_CHARS,
    attempts_for_student,
    pseudonym,
    retests,
    summarise,
)
from app.player.runtime import load_catalog

SCOPE = "research_pseudonymised"


def _write(path: Path, columns: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.pilot")
    parser.add_argument("command", choices=["export"])
    parser.add_argument("--out", required=True, help="a folder for attempts.csv and retests.csv")
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args(argv)
    salt = settings.pilot_export_salt
    if len(salt) < MIN_SALT_CHARS:
        print(
            f"ERROR: set PILOT_EXPORT_SALT to a secret of at least {MIN_SALT_CHARS} characters",
            file=sys.stderr,
        )
        return 1
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    with session_factory(args.database_url)() as db:
        catalog = {
            item.id: item for item in load_catalog(db, allow_draft=settings.allow_draft_content)
        }
        for student_id in db.scalars(select(StudentRow.id)).all():
            if not has_scope(db, student_id, SCOPE):
                continue
            logged = db.execute(
                select(EventRow, SessionRow.type)
                .join(SessionRow, EventRow.session_id == SessionRow.id)
                .where(SessionRow.student_id == student_id)
                .order_by(EventRow.created_at, EventRow.id)
            ).all()
            who = pseudonym(salt, student_id)
            rows += [
                {"pseudonym": who, **row}
                for row in attempts_for_student([(event, kind) for event, kind in logged], catalog)
            ]
    _write(out / "attempts.csv", ATTEMPT_COLUMNS, rows)
    _write(out / "retests.csv", (*ATTEMPT_COLUMNS, "bucket"), retests(rows))
    summary = summarise(rows)
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
