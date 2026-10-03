from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.registries.loaders import load_jurisdiction_profile
from app.registries.quiet_hours import in_quiet_hours


def test_quiet_hours_default_strict_two_zones() -> None:
    profile = load_jurisdiction_profile("default_strict")
    # 22:00 local is inside 21:00–07:00
    thimphu = datetime(2026, 6, 1, 16, 30, tzinfo=ZoneInfo("UTC"))  # 22:00 Asia/Thimphu
    kolkata = datetime(2026, 6, 1, 16, 30, tzinfo=ZoneInfo("UTC"))  # 22:00 Asia/Kolkata
    assert in_quiet_hours(thimphu, ZoneInfo("Asia/Thimphu"), profile)
    assert in_quiet_hours(kolkata, ZoneInfo("Asia/Kolkata"), profile)
    noon_thimphu = datetime(2026, 6, 1, 6, 30, tzinfo=ZoneInfo("UTC"))  # 12:00 local
    assert not in_quiet_hours(noon_thimphu, ZoneInfo("Asia/Thimphu"), profile)
