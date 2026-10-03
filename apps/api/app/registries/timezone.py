from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


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
