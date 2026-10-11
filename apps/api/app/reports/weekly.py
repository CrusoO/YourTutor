"""The weekly guardian report: `python -m app.reports weekly`.

For every family the report is built from the child's own events of the last seven days, in the
guardian's language (English wherever a reviewer has not written another), and sent on a channel
the jurisdiction profile allows. Nothing is sent during the profile's quiet hours in the family's
time zone, nothing twice for the same week, nothing for a week without practice, and nothing for a
guest, who has no guardian to write to. The text never ranks or compares.
"""

from __future__ import annotations

import argparse
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.consent import GUEST_ROLE, active_consent
from app.auth.security import now_utc
from app.config import settings
from app.db.models import ReportLogRow, StudentRow, UserRow
from app.registries.locale_resolve import resolve_locale_chain
from app.registries.paths import config_dir
from app.registries.quiet_hours import in_quiet_hours
from app.registries.startup import deployment_jurisdiction_profile
from app.reports.senders import EmailReportSender, ReportSender
from app.views.guardian import week_summary

SENDERS: dict[str, ReportSender] = {"email": EmailReportSender()}


@lru_cache(maxsize=1)
def _templates() -> dict[str, Any]:
    path: Path = config_dir() / "reports.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _text(key: str, language: str) -> str:
    data = _templates()
    table = data.get("messages", {})
    for code in (*resolve_locale_chain(language), data.get("default_language", "en")):
        found = (table.get(code) or {}).get(key)
        if found:
            return str(found)
    return ""


def week_key(moment: datetime) -> str:
    year, week, _ = moment.isocalendar()
    return f"{year}-W{week:02d}"


@dataclass
class Report:
    subject: str
    body: str


def build_report(
    db: Session, student: StudentRow, language: str, now: datetime, url: str
) -> Report | None:
    """The text for one child, or None when the child did not practise this week."""
    week = week_summary(db, student, now, language)
    if week["sessions"] == 0:
        return None
    name = student.display_name
    lines = [
        _text("greeting", language),
        "",
        _text("activity", language).format(
            name=name, days=week["days_active"], minutes=week["active_minutes"]
        ),
    ]
    if week["learned"]:
        skills = ", ".join(row["title"] for row in week["learned"])
        lines.append(_text("learned", language).format(skills=skills))
    else:
        lines.append(_text("learned_none", language))
    if week["practised"]:
        lines.append(_text("practised", language).format(skills=", ".join(week["practised"])))
    lines += [
        "",
        _text("open", language).format(name=name, url=url),
        "",
        _text("footer", language).format(name=name),
    ]
    return Report(_text("subject", language).format(name=name), "\n".join(lines))


@dataclass
class WeeklyRun:
    sent: list[str] = field(default_factory=list)
    skipped: dict[str, str] = field(default_factory=dict)  # student id -> why

    def note(self, student: StudentRow, why: str) -> None:
        self.skipped[str(student.id)] = why


def run_weekly(
    db: Session,
    now: datetime | None = None,
    *,
    senders: dict[str, ReportSender] | None = None,
    base_url: str = "http://localhost:3000/guardian",
) -> WeeklyRun:
    moment = now or now_utc()
    profile = deployment_jurisdiction_profile()
    available = senders if senders is not None else SENDERS
    channels = [c for c in profile.report_channels if c in available]
    result = WeeklyRun()
    rows = db.execute(
        select(StudentRow, UserRow)
        .join(UserRow, UserRow.id == StudentRow.parent_id)
        .order_by(StudentRow.created_at, StudentRow.id)
    ).all()
    for student, parent in rows:
        if parent.role == GUEST_ROLE:
            result.note(student, "guest")
            continue
        if active_consent(db, student.id) is None:
            result.note(student, "no_consent")
            continue
        if not channels:
            result.note(student, "no_channel")
            continue
        tz = ZoneInfo(student.timezone or "UTC")
        if in_quiet_hours(moment, tz, profile):
            result.note(student, "quiet_hours")
            continue
        report = build_report(db, student, parent.locale or "en", moment, base_url)
        if report is None:
            result.note(student, "no_activity")
            continue
        key = week_key(moment)
        for channel in channels:
            if db.scalar(
                select(ReportLogRow.id).where(
                    ReportLogRow.student_id == student.id,
                    ReportLogRow.week_key == key,
                    ReportLogRow.channel == channel,
                )
            ):
                result.note(student, "already_sent")
                continue
            available[channel].send(parent.email, report.subject, report.body)
            db.add(
                ReportLogRow(
                    id=uuid.uuid4(),
                    student_id=student.id,
                    parent_id=parent.id,
                    week_key=key,
                    channel=channel,
                    sent_at=moment,
                )
            )
            result.sent.append(str(student.id))
        db.flush()
    db.commit()
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.reports")
    parser.add_argument("job", choices=["weekly"])
    parser.add_argument("--base-url", default=settings.public_web_url)
    args = parser.parse_args(argv)
    from app.db.session import session_factory

    with session_factory()() as db:
        outcome = run_weekly(db, base_url=args.base_url)
    print(f"sent {len(outcome.sent)}; skipped {len(outcome.skipped)}")
    for student_id, why in sorted(outcome.skipped.items()):
        print(f"  skipped {student_id}: {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
