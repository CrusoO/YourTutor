"""Retention jobs. `python -m app.retention purge_guests` deletes guests idle past the window.

A guest has no guardian to ask, so the jurisdiction profile's `guest_retention_days` decides how
long an idle guest's records are kept. Activity is the latest of the guest's creation and its last
session activity. Upgraded students are family students and never touched here.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.consent import GUEST_ROLE, _profile_id_for
from app.auth.security import as_utc, now_utc
from app.auth.service import purge_students
from app.db.models import SessionRow, StudentRow, UserRow
from app.db.session import session_factory
from app.registries.startup import deployment_jurisdiction_profile


def purge_guests(db: Session, now: datetime | None = None) -> int:
    """Delete every guest idle longer than its profile's window. Returns the number deleted."""
    moment = now or now_utc()
    guests = db.execute(
        select(StudentRow, UserRow)
        .join(UserRow, UserRow.id == StudentRow.parent_id)
        .where(UserRow.role == GUEST_ROLE)
    ).all()
    purged = 0
    for student, owner in guests:
        last = db.scalar(
            select(func.max(SessionRow.last_active_at)).where(SessionRow.student_id == student.id)
        )
        active = as_utc(max(filter(None, [student.created_at, last])))
        profile = deployment_jurisdiction_profile(_profile_id_for(db, student))
        if moment - active <= timedelta(days=profile.guest_retention_days):
            continue
        purge_students(db, [student.id])
        db.delete(owner)
        purged += 1
    db.commit()
    return purged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.retention")
    parser.add_argument("job", choices=["purge_guests"])
    parser.parse_args(argv)
    with session_factory()() as db:
        print(f"purged {purge_guests(db)} guest(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
