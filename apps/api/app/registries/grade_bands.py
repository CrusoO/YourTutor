"""Grade-band lookup and session limits (ARCHITECTURE sections 15 and 20). Pure."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from app.registries.loaders import GradeBand, load_grade_bands

MINUTE_MS = 60_000


@dataclass(frozen=True)
class SessionLimits:
    soft_active_ms: int
    soft_items: int
    hard_active_ms: int
    max_words: int
    read_aloud_default: bool


def band_for_grade(grade: int, bands: tuple[GradeBand, ...] | None = None) -> GradeBand | None:
    """The band that lists the grade; a grade outside every band uses the nearest band."""
    table = bands if bands is not None else load_grade_bands()
    if not table:
        return None
    for band in table:
        if grade in band.grades:
            return band
    return min(table, key=lambda b: min(abs(grade - g) for g in b.grades))


@lru_cache(maxsize=1)
def _cached_bands() -> tuple[GradeBand, ...]:
    return load_grade_bands()


def limits_for_band(band: GradeBand) -> SessionLimits:
    return SessionLimits(
        soft_active_ms=band.soft_minutes * MINUTE_MS,
        soft_items=band.soft_items,
        hard_active_ms=band.hard_minutes * MINUTE_MS,
        max_words=band.max_words,
        read_aloud_default=band.read_aloud_default,
    )


def session_limits(grade: int) -> SessionLimits:
    band = band_for_grade(grade, _cached_bands())
    assert band is not None, "config/grade_bands.yaml defines no bands"
    return limits_for_band(band)
