"""G2b step 1: grade bands drive session caps and word limits (ARCHITECTURE §15, §20)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import StudentRow
from app.orchestrator.policy import policy
from app.orchestrator.types import HARD_ACTIVE_MS, SOFT_ACTIVE_MS, SOFT_ITEM_CAP, Event
from app.registries.grade_bands import band_for_grade, session_limits
from app.registries.loaders import RegistryLoadError, load_grade_bands
from tests.conftest import World, auth_header
from tests.orchestrator.conftest import make_learner, make_session

MIN = 60_000


def test_the_four_bands_match_the_architecture_table() -> None:
    bands = {b.id: b for b in load_grade_bands()}
    assert set(bands) == {"primary", "middle", "lower_secondary", "upper_secondary"}
    expected = {
        "primary": ((1, 5), 25, 8, 8, 12, True),
        "middle": ((6, 8), 40, 12, 10, 18, False),
        "lower_secondary": ((9, 10), 60, 15, 12, 20, False),
        "upper_secondary": ((11, 12), 80, 20, 15, 30, False),
    }
    for band_id, (span, words, soft_min, soft_items, hard_min, read_aloud) in expected.items():
        band = bands[band_id]
        assert (min(band.grades), max(band.grades)) == span
        assert band.max_words == words
        assert band.soft_minutes == soft_min and band.soft_items == soft_items
        assert band.hard_minutes == hard_min
        assert band.read_aloud_default is read_aloud


def test_every_grade_from_1_to_12_has_exactly_one_band() -> None:
    bands = load_grade_bands()
    for grade in range(1, 13):
        assert sum(grade in b.grades for b in bands) == 1, grade


@pytest.mark.parametrize(
    ("grade", "band"),
    [
        (1, "primary"),
        (5, "primary"),
        (6, "middle"),
        (8, "middle"),
        (9, "lower_secondary"),
        (10, "lower_secondary"),
        (11, "upper_secondary"),
        (12, "upper_secondary"),
    ],
)
def test_band_for_grade(grade: int, band: str) -> None:
    found = band_for_grade(grade, load_grade_bands())
    assert found is not None and found.id == band


def test_a_grade_outside_every_band_uses_the_nearest_band() -> None:
    bands = load_grade_bands()
    below = band_for_grade(0, bands)
    above = band_for_grade(14, bands)
    assert below is not None and below.id == "primary"
    assert above is not None and above.id == "upper_secondary"


def test_session_limits_in_milliseconds() -> None:
    limits = session_limits(4)
    assert (limits.soft_active_ms, limits.soft_items, limits.hard_active_ms) == (
        8 * MIN,
        8,
        12 * MIN,
    )
    assert limits.max_words == 25
    default = session_limits(9)
    assert (default.soft_active_ms, default.soft_items, default.hard_active_ms) == (
        SOFT_ACTIVE_MS,
        SOFT_ITEM_CAP,
        HARD_ACTIVE_MS,
    )


def test_overlapping_bands_are_refused(tmp_path: Path) -> None:
    (tmp_path / "grade_bands.yaml").write_text(
        "bands:\n"
        "  - {id: a, grades: [1, 2, 3], max_words: 25, soft_minutes: 8, soft_items: 8,"
        " hard_minutes: 12, read_aloud_default: true}\n"
        "  - {id: b, grades: [3, 4], max_words: 40, soft_minutes: 12, soft_items: 10,"
        " hard_minutes: 18, read_aloud_default: false}\n",
        encoding="utf-8",
    )
    with pytest.raises(RegistryLoadError, match="grade 3"):
        load_grade_bands(tmp_path)


def test_a_band_missing_a_setting_is_refused(tmp_path: Path) -> None:
    (tmp_path / "grade_bands.yaml").write_text(
        "bands:\n  - {id: a, grades: [1, 2]}\n", encoding="utf-8"
    )
    with pytest.raises(RegistryLoadError, match="max_words"):
        load_grade_bands(tmp_path)


# ---- policy ---------------------------------------------------------------------------------


def _session(**limits: int):
    session = make_session(introduced={"MATH.S1"})
    for key, value in limits.items():
        setattr(session, key, value)
    return session


def test_the_soft_item_cap_comes_from_the_session_limits() -> None:
    session = _session(soft_item_cap=3)
    session.items_completed = 3
    action = policy(make_learner(), session, None)
    assert action.type == "end_session" and action.ended_reason == "soft_cap"
    session = _session(soft_item_cap=3)
    session.items_completed = 2
    assert policy(make_learner(), session, None).type != "end_session"


def test_the_soft_and_hard_time_caps_come_from_the_session_limits() -> None:
    session = _session(soft_active_ms=8 * MIN, hard_active_ms=12 * MIN)
    session.active_ms = 8 * MIN
    assert policy(make_learner(), session, None).ended_reason == "soft_cap"
    session = _session(soft_active_ms=8 * MIN, hard_active_ms=12 * MIN)
    session.active_ms = 12 * MIN
    action = policy(make_learner(), session, Event(type="idle_nudge"))
    assert action.type == "end_session" and action.ended_reason == "hard_cap"


def test_default_limits_are_unchanged_for_grades_9_and_10() -> None:
    session = make_session()
    assert session.soft_active_ms == SOFT_ACTIVE_MS
    assert session.soft_item_cap == SOFT_ITEM_CAP
    assert session.hard_active_ms == HARD_ACTIVE_MS


# ---- API ------------------------------------------------------------------------------------


def _set_grade(db: Session, world: World, grade: int) -> None:
    student = db.get(StudentRow, uuid.UUID(world.student_share_id))
    assert student is not None
    student.grade = grade
    db.commit()


@pytest.mark.parametrize(("grade", "minutes"), [(3, 8), (7, 12), (9, 15), (12, 20)])
def test_today_goal_minutes_follow_the_students_band(
    client: TestClient, db: Session, world: World, grade: int, minutes: int
) -> None:
    _set_grade(db, world, grade)
    body = client.get("/students/me/today", headers=auth_header(world.student_token)).json()
    assert body["goal_minutes"] == minutes
    assert body["remaining_active_minutes"] <= minutes


def test_a_state_built_for_a_primary_student_gets_the_primary_limits(
    db: Session, world: World
) -> None:
    from app.auth.security import now_utc
    from app.db.models import SessionRow
    from app.player.runtime import _build_state, limits_for_student

    _set_grade(db, world, 3)
    student = db.get(StudentRow, uuid.UUID(world.student_share_id))
    assert student is not None
    assert limits_for_student(student).soft_items == 8
    row = SessionRow(
        id=uuid.uuid4(),
        student_id=student.id,
        started_at=now_utc(),
        type="practice",
        last_active_at=now_utc(),
        plan={},
    )
    db.add(row)
    db.flush()
    state, _ = _build_state(db, row, student)
    assert (state.soft_item_cap, state.soft_active_ms, state.hard_active_ms) == (
        8,
        8 * MIN,
        12 * MIN,
    )
    assert state.max_words == 25
