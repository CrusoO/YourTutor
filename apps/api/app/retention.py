"""Retention jobs: `python -m app.retention <job> [--dry-run]`, the one entrypoint for all of them.

Jobs: purge_guests, otp, rate_events, auth_sessions, llm_calls, video_jobs, or `all`.
Nothing here is scheduled by the code; see docs/OPERATOR.md for the cron line.

Every job is idempotent (a second run finds nothing to do), deletes in batches so one run never
holds a long lock, and prints one line with counts only. `--dry-run` counts and changes nothing.
The output never names a person, an email, an address or a file path. Exit code is 0 unless the
job itself fails (a failed job does not stop the others).

Periods live here, in one place, except the guest window, which the jurisdiction profile owns
(`guest_retention_days`, 90 in default_strict).
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import ColumnElement, delete, func, select, update
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.auth.consent import GUEST_ROLE, _profile_id_for
from app.auth.security import as_utc, now_utc
from app.auth.service import purge_students
from app.db.models import (
    AuthSessionRow,
    LlmCallRow,
    OtpChallengeRow,
    RateEventRow,
    SessionRow,
    StudentRow,
    UserRow,
    VideoJobRow,
)
from app.db.session import session_factory
from app.registries.startup import deployment_jurisdiction_profile
from app.video_jobs.files import delete_job_folder, job_folder_name

logger = logging.getLogger(__name__)

# Why each number: the shortest period that still does the job the row exists for.
OTP_HOURS = 24  # a sign-in code lives minutes; a day keeps recent ones for abuse checks, no longer
RATE_EVENT_DAYS = 7  # the limiter's windows are minutes to a day; a week covers an abuse review
AUTH_SESSION_DAYS = 30  # an expired sign-in token has no use; a month after expiry then it goes
LLM_REPLY_TEXT_DAYS = 14  # the review window: reply text may repeat a learner's words, so it is
#                           removed once staff have had two weeks to read the sampled replies
LLM_METADATA_DAYS = 90  # call metadata (model, tokens, time) is for cost and quality, a quarter
VIDEO_JOB_DAYS = 30  # a finished, failed or cancelled job and its files, a month to watch it
VIDEO_STALE_DAYS = 30  # a job still queued or running after this long was abandoned: also removed
BATCH = 500  # rows per delete statement

Counts = dict[str, int]


def _cutoff(now: datetime, **delta: int) -> datetime:
    return now - timedelta(**delta)


def _delete_in_batches(
    db: Session, id_column: InstrumentedAttribute[Any], where: ColumnElement[bool], dry_run: bool
) -> int:
    """Delete the rows matching `where` BATCH at a time; with dry_run only count them."""
    table = id_column.class_
    if dry_run:
        return db.scalar(select(func.count()).select_from(table).where(where)) or 0
    total = 0
    while True:
        ids: list[Any] = list(db.scalars(select(id_column).where(where).limit(BATCH)))
        if not ids:
            return total
        db.execute(delete(table).where(id_column.in_(ids)))
        db.commit()
        total += len(ids)


def purge_guests(db: Session, now: datetime | None = None, dry_run: bool = False) -> int:
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
        purged += 1
        if dry_run:
            continue
        purge_students(db, [student.id])
        db.delete(owner)
        db.commit()
    return purged


def purge_otp(db: Session, now: datetime | None = None, dry_run: bool = False) -> int:
    """Sign-in code rows (email, IP, hashed code) older than OTP_HOURS."""
    cutoff = _cutoff(now or now_utc(), hours=OTP_HOURS)
    return _delete_in_batches(db, OtpChallengeRow.id, OtpChallengeRow.created_at < cutoff, dry_run)


def purge_rate_events(db: Session, now: datetime | None = None, dry_run: bool = False) -> int:
    cutoff = _cutoff(now or now_utc(), days=RATE_EVENT_DAYS)
    return _delete_in_batches(db, RateEventRow.id, RateEventRow.created_at < cutoff, dry_run)


def purge_auth_sessions(db: Session, now: datetime | None = None, dry_run: bool = False) -> int:
    """Sign-in tokens that expired more than AUTH_SESSION_DAYS ago.

    A sign-out deletes its row at once (there is no `revoked` flag), so expiry is the only way a
    token row outlives its use.
    """
    cutoff = _cutoff(now or now_utc(), days=AUTH_SESSION_DAYS)
    return _delete_in_batches(db, AuthSessionRow.id, AuthSessionRow.expires_at < cutoff, dry_run)


def purge_llm_calls(
    db: Session, now: datetime | None = None, dry_run: bool = False
) -> tuple[int, int]:
    """Null reply text after LLM_REPLY_TEXT_DAYS; delete the metadata after LLM_METADATA_DAYS.

    Returns (reply texts removed, rows deleted).
    """
    moment = now or now_utc()
    text_cut = _cutoff(moment, days=LLM_REPLY_TEXT_DAYS)
    has_text = (LlmCallRow.created_at < text_cut) & LlmCallRow.output_text.is_not(None)
    cleared = 0
    if dry_run:
        cleared = db.scalar(select(func.count()).select_from(LlmCallRow).where(has_text)) or 0
    else:
        while True:
            ids = list(db.scalars(select(LlmCallRow.id).where(has_text).limit(BATCH)))
            if not ids:
                break
            db.execute(update(LlmCallRow).where(LlmCallRow.id.in_(ids)).values(output_text=None))
            db.commit()
            cleared += len(ids)
    old = LlmCallRow.created_at < _cutoff(moment, days=LLM_METADATA_DAYS)
    return cleared, _delete_in_batches(db, LlmCallRow.id, old, dry_run)


def purge_video_jobs(
    db: Session, now: datetime | None = None, dry_run: bool = False
) -> tuple[int, int]:
    """Finished, failed or cancelled jobs older than VIDEO_JOB_DAYS (and abandoned queued or
    running ones older than VIDEO_STALE_DAYS), with their output folders.

    Returns (rows deleted, folders removed). A folder is removed only if it sits directly inside
    the configured jobs directory (see app.video_jobs.files); a stored path elsewhere is ignored.
    """
    moment = now or now_utc()
    done_cut = _cutoff(moment, days=VIDEO_JOB_DAYS)
    stale_cut = _cutoff(moment, days=VIDEO_STALE_DAYS)
    finished = VideoJobRow.status.in_(("done", "failed", "cancelled")) & (
        func.coalesce(VideoJobRow.completed_at, VideoJobRow.created_at) < done_cut
    )
    abandoned = VideoJobRow.status.in_(("queued", "running")) & (VideoJobRow.created_at < stale_cut)
    where = finished | abandoned
    if dry_run:
        return db.scalar(select(func.count()).select_from(VideoJobRow).where(where)) or 0, 0
    rows = folders = 0
    while True:
        batch = [
            (r[0], r[1], r[2])
            for r in db.execute(
                select(VideoJobRow.id, VideoJobRow.result_path, VideoJobRow.request_json)
                .where(where)
                .limit(BATCH)
            )
        ]
        if not batch:
            return rows, folders
        db.execute(delete(VideoJobRow).where(VideoJobRow.id.in_([b[0] for b in batch])))
        db.commit()
        rows += len(batch)
        for job_id, result_path, request_json in batch:
            if delete_job_folder(job_folder_name(job_id, result_path, request_json)):
                folders += 1


def run_job(db: Session, job: str, dry_run: bool = False, now: datetime | None = None) -> str:
    """Run one job and return its summary line (counts only)."""
    mode = "would delete" if dry_run else "deleted"
    if job == "purge_guests":
        return f"purge_guests: {mode} {purge_guests(db, now, dry_run)} guest(s)"
    if job == "otp":
        return f"otp: {mode} {purge_otp(db, now, dry_run)} sign-in code row(s)"
    if job == "rate_events":
        return f"rate_events: {mode} {purge_rate_events(db, now, dry_run)} row(s)"
    if job == "auth_sessions":
        return f"auth_sessions: {mode} {purge_auth_sessions(db, now, dry_run)} row(s)"
    if job == "llm_calls":
        cleared, rows = purge_llm_calls(db, now, dry_run)
        verb = "would clear" if dry_run else "cleared"
        return f"llm_calls: {verb} {cleared} reply text(s), {mode} {rows} row(s)"
    if job == "video_jobs":
        rows, folders = purge_video_jobs(db, now, dry_run)
        files = "(folders not counted in a dry run)" if dry_run else f"{folders} folder(s)"
        return f"video_jobs: {mode} {rows} job(s), {files}"
    raise ValueError(f"unknown job {job}")


JOBS: tuple[str, ...] = (
    "purge_guests",
    "otp",
    "rate_events",
    "auth_sessions",
    "llm_calls",
    "video_jobs",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.retention")
    parser.add_argument("job", choices=[*JOBS, "all"])
    parser.add_argument("--dry-run", action="store_true", help="count only; delete nothing")
    args = parser.parse_args(argv)
    names = JOBS if args.job == "all" else (args.job,)
    failed = 0
    with session_factory()() as db:
        for name in names:
            try:
                print(run_job(db, name, args.dry_run))
            except Exception:
                # A failing job must not stop the others; the type is logged, never the row data.
                db.rollback()
                failed += 1
                logger.exception("retention job %s failed", name)
                print(f"{name}: FAILED (see the log)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
