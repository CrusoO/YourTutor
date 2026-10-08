"""Preview scenarios are built by replaying events through the real engine."""

from __future__ import annotations

import inspect
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import service
from app.config import settings
from app.content.loader import load_path
from app.db.models import (
    ConsentRow,
    EventRow,
    MasteryRow,
    ReviewCardRow,
    SessionRow,
    StudentRow,
    UserRow,
)
from app.db.session import session_factory
from app.dev import scenarios
from app.dev.scenarios import PIN, SCENARIOS, seed_scenarios
from app.learner.bkt import BktParams
from app.learner.status import REVIEW_DUE, review_overdue, skill_status
from app.player.runtime import load_catalog, recompute_ladders
from app.registries.paths import repo_root

NAMES = [
    "new_student",
    "mid_chapter",
    "skill_at_level_4",
    "review_due",
    "all_skills_level_4",
    "slip_prone",
]


@pytest.fixture(scope="module")
def seeded(tmp_path_factory: pytest.TempPathFactory) -> Iterator[tuple[str, list[dict]]]:
    url = f"sqlite:///{tmp_path_factory.mktemp('scenarios') / 'preview.db'}"
    load_path(repo_root() / "content", database_url=url)
    previous = settings.allow_draft_content
    settings.allow_draft_content = True
    try:
        report = seed_scenarios(url)
    finally:
        settings.allow_draft_content = previous
    yield url, report


def _db(url: str) -> Session:
    return session_factory(url)()


def _student(db: Session, name: str) -> StudentRow:
    spec = next(s for s in SCENARIOS if s.name == name)
    row = db.scalar(select(StudentRow).where(StudentRow.family_code == spec.family_code))
    assert row is not None, name
    return row


def _levels(db: Session, student: StudentRow) -> dict[str, int]:
    rows = db.scalars(select(MasteryRow).where(MasteryRow.student_id == student.id)).all()
    return {row.skill_id: row.ladder_level for row in rows}


def _overlay_skills(db: Session, student: StudentRow) -> list[str]:
    from app.player.runtime import _overlay_skills as overlay_skills

    return list(overlay_skills(db, student))


def test_scenario_names_are_the_six_required_ones() -> None:
    assert [s.name for s in SCENARIOS] == NAMES
    assert len({s.family_code for s in SCENARIOS}) == 6


def test_seeding_is_refused_unless_draft_content_is_allowed(tmp_path: Path) -> None:
    settings.allow_draft_content = False
    with pytest.raises(RuntimeError, match="ALLOW_DRAFT_CONTENT"):
        seed_scenarios(f"sqlite:///{tmp_path / 'x.db'}")


def test_seeding_without_loaded_content_explains_what_to_run(tmp_path: Path) -> None:
    from app.db.models import Base
    from app.db.session import make_engine

    url = f"sqlite:///{tmp_path / 'empty.db'}"
    Base.metadata.create_all(make_engine(url))
    settings.allow_draft_content = True
    with pytest.raises(RuntimeError, match="content load"):
        seed_scenarios(url)


def test_report_lists_family_code_and_pin_per_scenario(seeded: tuple[str, list[dict]]) -> None:
    _, report = seeded
    assert [row["name"] for row in report] == NAMES
    for row in report:
        assert row["pin"] == PIN and row["family_code"]


def test_every_scenario_student_can_log_in_with_family_code_and_pin(
    seeded: tuple[str, list[dict]],
) -> None:
    url, _ = seeded
    with _db(url) as db:
        for spec in SCENARIOS:
            assert service.verify_family_pin(db, spec.family_code, PIN)
        db.rollback()


def test_new_student_has_no_history(seeded: tuple[str, list[dict]]) -> None:
    with _db(seeded[0]) as db:
        student = _student(db, "new_student")
        for model in (SessionRow, MasteryRow, ReviewCardRow):
            column = model.student_id
            assert (
                db.scalar(select(func.count()).select_from(model).where(column == student.id)) == 0
            )
        consent = db.scalar(select(ConsentRow).where(ConsentRow.student_id == student.id))
        assert consent is not None and "tutoring" in consent.scopes


def test_skill_at_level_4_has_exactly_the_first_skill_done(seeded: tuple[str, list[dict]]) -> None:
    with _db(seeded[0]) as db:
        student = _student(db, "skill_at_level_4")
        skills = _overlay_skills(db, student)
        levels = _levels(db, student)
        assert levels[skills[0]] >= 4
        assert all(levels.get(skill, 0) < 4 for skill in skills[1:])


def test_review_due_skill_is_level_4_with_an_overdue_card(seeded: tuple[str, list[dict]]) -> None:
    with _db(seeded[0]) as db:
        student = _student(db, "review_due")
        first = _overlay_skills(db, student)[0]
        level = _levels(db, student)[first]
        card = db.get(ReviewCardRow, (student.id, first))
        assert level >= 4 and card is not None
        now = datetime.now(UTC)
        due = card.due_at if card.due_at.tzinfo else card.due_at.replace(tzinfo=UTC)
        assert review_overdue(due, now)
        assert skill_status(level, review_overdue=True) == REVIEW_DUE
        started = db.scalars(
            select(SessionRow.started_at).where(SessionRow.student_id == student.id)
        ).all()
        oldest = min(s if s.tzinfo else s.replace(tzinfo=UTC) for s in started)
        assert now - oldest > timedelta(days=3)  # history is in the past, not "today"


def test_mid_chapter_has_four_skills_done_one_started_rest_untouched(
    seeded: tuple[str, list[dict]],
) -> None:
    with _db(seeded[0]) as db:
        student = _student(db, "mid_chapter")
        skills = _overlay_skills(db, student)
        levels = _levels(db, student)
        assert all(levels[skill] >= 4 for skill in skills[:4])
        assert skills[4] in levels and levels[skills[4]] < 4
        assert all(skill not in levels for skill in skills[5:])


def test_all_skills_level_4_covers_the_whole_chapter(seeded: tuple[str, list[dict]]) -> None:
    with _db(seeded[0]) as db:
        student = _student(db, "all_skills_level_4")
        skills = _overlay_skills(db, student)
        levels = _levels(db, student)
        assert len(skills) >= 12
        assert all(levels.get(skill, 0) >= 4 for skill in skills)


def test_ladders_come_from_events_not_from_written_rows(seeded: tuple[str, list[dict]]) -> None:
    """Stored ladder == recompute from the event log, and evidence ids are real event ids."""
    with _db(seeded[0]) as db:
        for name in ("skill_at_level_4", "mid_chapter", "all_skills_level_4"):
            student = _student(db, name)
            catalog = load_catalog(db, allow_draft=True)
            params = {
                skill: BktParams(p_init=0.2, p_learn=0.15, p_slip=0.1, p_guess=0.2)
                for skill in _overlay_skills(db, student)
            }
            ladders = recompute_ladders(
                db, student.id, catalog, params, now=datetime.now(UTC) + timedelta(days=1)
            )
            event_ids = {
                str(i)
                for i in db.scalars(
                    select(EventRow.client_event_id)
                    .join(SessionRow, EventRow.session_id == SessionRow.id)
                    .where(SessionRow.student_id == student.id)
                ).all()
            }
            for row in db.scalars(select(MasteryRow).where(MasteryRow.student_id == student.id)):
                if row.ladder_level == 0:
                    continue
                assert ladders[row.skill_id].level == row.ladder_level, (name, row.skill_id)
                evidence_ids = {i for ids in row.ladder_evidence.values() for i in ids}
                assert evidence_ids <= event_ids


def test_scenario_code_never_writes_mastery_rows() -> None:
    source = inspect.getsource(scenarios)
    assert "MasteryRow" not in source
    assert "persist_learner" not in source


def test_reseeding_replaces_the_scenarios_without_duplicates(
    seeded: tuple[str, list[dict]],
) -> None:
    url, _ = seeded
    settings.allow_draft_content = True
    report = seed_scenarios(url, only=["new_student", "skill_at_level_4"])
    assert [row["name"] for row in report] == ["new_student", "skill_at_level_4"]
    with _db(url) as db:
        spec_codes = {s.family_code for s in SCENARIOS}
        count = db.scalar(
            select(func.count())
            .select_from(StudentRow)
            .where(StudentRow.family_code.in_(spec_codes))
        )
        assert count == 6
        parents = db.scalar(
            select(func.count()).select_from(UserRow).where(UserRow.email.like("scenario.%"))
        )
        assert parents == 6
        assert uuid.UUID(str(_student(db, "new_student").id))


def _first_action(url: str, name: str) -> dict:
    """Start a session the way the student's Start practice button does, without keeping it."""
    from app.auth.actor import Actor
    from app.player.runtime import session_view

    settings.allow_draft_content = True  # the preview API runs with draft content on
    with _db(url) as db:
        student = _student(db, name)
        admin = Actor(role="admin")
        row = service.start_session(db, admin, student.id, "practice")
        action = session_view(db, admin, row)["action"]
        db.rollback()
        return action


def _open_sessions(url: str, name: str) -> int:
    with _db(url) as db:
        student = _student(db, name)
        count = db.scalar(
            select(func.count())
            .select_from(SessionRow)
            .where(
                SessionRow.student_id == student.id,
                (SessionRow.ended_at.is_(None)) | (SessionRow.resumable.is_(True)),
            )
        )
        return int(count or 0)


def test_review_due_opens_with_a_warmup_for_the_overdue_skill(
    seeded: tuple[str, list[dict]],
) -> None:
    url, _ = seeded
    assert _open_sessions(url, "review_due") == 0
    action = _first_action(url, "review_due")
    assert action["type"] == "warmup_item"
    with _db(url) as db:
        student = _student(db, "review_due")
        assert action["skill_id"] == _overlay_skills(db, student)[0]


def test_all_skills_level_4_starts_extension_practice_with_an_apply_item(
    seeded: tuple[str, list[dict]],
) -> None:
    from app.db.models import ItemRow

    url, _ = seeded
    assert _open_sessions(url, "all_skills_level_4") == 0
    action = _first_action(url, "all_skills_level_4")
    assert action["type"] in {"show_item", "warmup_item"}
    with _db(url) as db:
        item = db.get(ItemRow, action["item_id"])
        assert item is not None and item.role in {"apply", "procedure"}


def test_slip_prone_starts_with_an_item_that_can_show_check_your_work(
    seeded: tuple[str, list[dict]],
) -> None:
    from app.db.models import ItemRow

    url, _ = seeded
    assert _open_sessions(url, "slip_prone") == 0
    action = _first_action(url, "slip_prone")
    assert action["type"] in {"show_item", "warmup_item"}
    with _db(url) as db:
        student = _student(db, "slip_prone")
        assert all(level >= 4 for level in _levels(db, student).values())
        item = db.get(ItemRow, action["item_id"])
        assert item is not None and item.slip_patterns and item.step_hints and item.hint_restate


def test_skill_at_level_4_and_mid_chapter_keep_a_session_open_to_resume(
    seeded: tuple[str, list[dict]],
) -> None:
    url, _ = seeded
    assert _open_sessions(url, "skill_at_level_4") >= 1
    assert _open_sessions(url, "mid_chapter") >= 1
    from app.auth.security import now_utc
    from app.registries.timezone import same_local_day

    with _db(url) as db:
        for name in ("skill_at_level_4", "mid_chapter"):
            student = _student(db, name)
            rows = db.scalars(
                select(SessionRow).where(
                    SessionRow.student_id == student.id, SessionRow.resumable.is_(True)
                )
            ).all()
            assert rows, name
            for row in rows:  # resumable only on the day of last use (G2 rule)
                assert same_local_day(row.last_active_at, now_utc(), student.timezone), name
