from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.registries.loaders import JurisdictionProfile, QuietHours


def _parse_hhmm(value: str) -> time:
    hour, minute = value.split(":", 1)
    return time(hour=int(hour), minute=int(minute))


def in_quiet_hours(
    moment: datetime,
    tz: ZoneInfo,
    profile: JurisdictionProfile,
) -> bool:
    local = moment.astimezone(tz)
    return _in_quiet_hours_local(local.time(), profile.quiet_hours)


def _in_quiet_hours_local(clock: time, window: QuietHours) -> bool:
    start = _parse_hhmm(window.start)
    end = _parse_hhmm(window.end)
    if start <= end:
        return start <= clock < end
    return clock >= start or clock < end
