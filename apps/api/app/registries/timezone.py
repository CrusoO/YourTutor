from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _zone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or "UTC")
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def same_local_day(a: datetime, b: datetime, tz_name: str | None) -> bool:
    """Whether two instants fall on the same calendar day in the given IANA zone.

    Local midnight belongs to the new day. An unknown zone is treated as UTC.
    """
    zone = _zone(tz_name)
    return a.astimezone(zone).date() == b.astimezone(zone).date()


def resolve_student_timezone(
    *,
    student_override: str | None,
    curriculum_default: str | None,
    device_timezone: str | None = None,
) -> str:
    for candidate in (student_override, curriculum_default, device_timezone, "UTC"):
        if not candidate:
            continue
        try:
            ZoneInfo(candidate)
        except ZoneInfoNotFoundError:
            continue
        return candidate
    return "UTC"
