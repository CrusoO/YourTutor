"""Plan A slice A0: baseline numbers are read-only, aggregate and suppressed below 20 students."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.security import now_utc
from app.db.models import EventRow, SessionRow, StudentRow, UserRow
from app.metrics.baseline import (
    MIN_STUDENTS,
    SUPPRESSED,
    baseline_metrics,
    render_table,
    suppress,
)

D0 = date(2026, 3, 1)


def _t(day: date, seconds: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=UTC) + timedelta(seconds=seconds)


PARENT_EMAIL = "baseline-parent@example.com"


def ensure_student(db: Session, student: uuid.UUID) -> None:
    """A real student row (Postgres enforces the foreign key; SQLite does not)."""
    if db.get(StudentRow, student) is not None:
        return
    parent = db.scalars(select(UserRow).where(UserRow.email == PARENT_EMAIL)).first()
    if parent is None:
        parent = UserRow(
            id=uuid.uuid4(), role="parent", email=PARENT_EMAIL, locale="en", created_at=now_utc()
        )
        db.add(parent)
        db.flush()
    db.add(
        StudentRow(
            id=student,
            parent_id=parent.id,
            display_name="Kid",
            grade=9,
            board="bhutan",
            curriculum_id="bhutan",
            book_id="bhutan_class9",
            home_language="en",
            exam_language="en",
            timezone="Asia/Thimphu",
            created_at=now_utc(),
        )
    )
    db.flush()


def add_session(
    db: Session,
    student: uuid.UUID,
    day: date,
    *,
    ended_reason: str | None = None,
    ended: bool | None = None,
    offset: int = 0,
) -> uuid.UUID:
    start = _t(day, offset)
    ensure_student(db, student)
    is_ended = ended if ended is not None else ended_reason is not None
    row = SessionRow(
        id=uuid.uuid4(),
        student_id=student,
        started_at=start,
        ended_at=start + timedelta(minutes=10) if is_ended else None,
        ended_reason=ended_reason,
        type="practice",
        last_active_at=start,
        plan={},
    )
    db.add(row)
    db.flush()
    return row.id


def add_event(
    db: Session,
    session_id: uuid.UUID,
    when: datetime,
    event_type: str = "answer",
    item: str | None = "i1",
    correct: bool | None = None,
) -> None:
    db.add(
        EventRow(
            id=uuid.uuid4(),
            session_id=session_id,
            item_id=item,
            event_type=event_type,
            payload={"free_text": "SECRET ANSWER"},
            correct=correct,
            created_at=when,
        )
    )


def cohort(db: Session, n: int, day: date = D0, *, answer_after: int = 30) -> list[uuid.UUID]:
    students = [uuid.uuid4() for _ in range(n)]
    for i, st in enumerate(students):
        sid = add_session(db, st, day, ended_reason="chapter_complete")
        add_event(db, sid, _t(day, answer_after + i), correct=False)
        add_event(db, sid, _t(day, 100 + i), correct=True, item="i2")
    db.commit()
    return students


def test_empty_window_reports_nothing(db: Session) -> None:
    r = baseline_metrics(db, D0, D0 + timedelta(days=3))
    assert r["sessions_in_window"] == 0
    assert r["time_to_first_answer"]["median_s"] is None
    assert r["completion"]["completion_rate"] is None
    assert r["return"]["day_1"]["rate"] is None
    assert "Not measured" in render_table(r)


def test_until_before_since_is_refused(db: Session) -> None:
    with pytest.raises(ValueError):
        baseline_metrics(db, D0, D0 - timedelta(days=1))


def test_times_to_first_answer_and_first_correct(db: Session) -> None:
    cohort(db, MIN_STUDENTS)
    r = baseline_metrics(db, D0, D0)
    # first answers at 30..49 s, nearest-rank median of 20 values is the 10th (39), p90 the 18th
    assert r["time_to_first_answer"]["median_s"] == 39.0
    assert r["time_to_first_answer"]["p90_s"] == 47.0
    # first correct at 100..119 s
    assert r["time_to_first_correct"]["median_s"] == 109.0
    assert r["time_to_first_correct"]["sessions"] == MIN_STUDENTS


def test_session_without_answers_is_skipped_and_negative_gap_ignored(db: Session) -> None:
    st = uuid.uuid4()
    s1 = add_session(db, st, D0)  # no events at all
    s2 = add_session(db, st, D0, offset=500)
    add_event(db, s2, _t(D0, 400), correct=True)  # before the session start: clock skew
    add_event(db, s1, _t(D0, 50), event_type="request_help")  # hint only, no answer
    db.commit()
    r = baseline_metrics(db, D0, D0)
    assert r["time_to_first_answer"] == {
        "sessions": 0,
        "students": 0,
        "median_s": None,
        "p90_s": None,
    }
    assert (
        r["hints_per_answered_item"]["mean"] == SUPPRESSED
    )  # the skewed answer still counts as an answered item


def test_hints_per_answered_item_and_distribution(db: Session) -> None:
    students = [uuid.uuid4() for _ in range(MIN_STUDENTS)]
    for st in students:
        sid = add_session(db, st, D0)
        add_event(db, sid, _t(D0, 10), item="a", correct=True)  # 0 hints
        add_event(db, sid, _t(D0, 20), "request_hint", item="b")
        add_event(db, sid, _t(D0, 25), "request_help", item="b")
        add_event(db, sid, _t(D0, 30), item="b", correct=True)  # 2 hints
        for k in range(4):
            add_event(db, sid, _t(D0, 40 + k), "request_hint", item="c")
        add_event(db, sid, _t(D0, 50), item="c", correct=False)  # 4 hints -> 3+
        add_event(db, sid, _t(D0, 60), "request_hint", item="never")  # not answered
    db.commit()
    h = baseline_metrics(db, D0, D0)["hints_per_answered_item"]
    assert h["items"] == 60
    assert h["mean"] == 2.0
    assert h["distribution"] == {"0": 20, "1": 0, "2": 20, "3+": 20}


def test_completion_is_defined_by_reason(db: Session) -> None:
    for reason, ended in [
        ("chapter_complete", True),
        ("diagnostic_complete", True),
        ("idle", True),
        ("superseded", True),
        (None, False),
    ]:
        for _ in range(MIN_STUDENTS):
            add_session(db, uuid.uuid4(), D0, ended_reason=reason, ended=ended)
    db.commit()
    c = baseline_metrics(db, D0, D0)["completion"]
    assert c["sessions"] == 5 * MIN_STUDENTS
    assert c["reached_planned_end"] == 2 * MIN_STUDENTS
    assert c["ended_early"] == 2 * MIN_STUDENTS
    assert c["never_ended"] == MIN_STUDENTS
    assert c["completion_rate"] == 0.4


def test_window_boundaries_are_inclusive_utc_dates(db: Session) -> None:
    st = uuid.uuid4()
    add_session(db, st, D0 - timedelta(days=1), offset=86399)  # one second before since
    add_session(db, st, D0)  # first second of since
    add_session(db, st, D0 + timedelta(days=1), offset=86399)  # last second of until
    add_session(db, st, D0 + timedelta(days=2))  # first second after until
    db.commit()
    r = baseline_metrics(db, D0, D0 + timedelta(days=1))
    assert r["sessions_in_window"] == SUPPRESSED  # 2 sessions, 1 student: suppressed
    n = db.scalar(select(func.count()).select_from(SessionRow))
    assert n == 4  # nothing was deleted or written
    # prove the count through a cohort big enough to show
    for _ in range(MIN_STUDENTS):
        add_session(db, uuid.uuid4(), D0 + timedelta(days=1), offset=86399)
    db.commit()
    assert baseline_metrics(db, D0, D0 + timedelta(days=1))["sessions_in_window"] == 22


def test_day_1_and_day_7_return(db: Session) -> None:
    until = D0 + timedelta(days=7)
    kept = [uuid.uuid4() for _ in range(MIN_STUDENTS)]
    for i, st in enumerate(kept):
        add_session(db, st, D0)
        if i < 10:
            add_session(db, st, D0 + timedelta(days=1))
        if i < 5:
            add_session(db, st, D0 + timedelta(days=7))
    # A student whose first session is on day 3: day 7 not elapsed, day 1 is.
    late = [uuid.uuid4() for _ in range(MIN_STUDENTS)]
    for st in late:
        add_session(db, st, D0 + timedelta(days=3))
        add_session(db, st, D0 + timedelta(days=4))
    # A student first seen before the window is not a window cohort member.
    old = uuid.uuid4()
    add_session(db, old, D0 - timedelta(days=5))
    add_session(db, old, D0 + timedelta(days=1))
    db.commit()
    r = baseline_metrics(db, D0, until)["return"]
    assert r["day_1"]["eligible_students"] == 2 * MIN_STUDENTS
    assert r["day_1"]["returned"] == 10 + MIN_STUDENTS
    assert r["day_7"]["eligible_students"] == MIN_STUDENTS
    assert r["day_7"]["returned"] == 5
    assert r["day_7"]["rate"] == 0.25
    # Shrink the window by a day: day 7 for the day-0 cohort has not fully elapsed.
    short = baseline_metrics(db, D0, until - timedelta(days=1))["return"]
    assert short["day_7"]["rate"] is None and short["day_7"]["eligible_students"] == 0


def test_one_student_is_suppressed_everywhere(db: Session) -> None:
    st = uuid.uuid4()
    sid = add_session(db, st, D0, ended_reason="chapter_complete")
    add_event(db, sid, _t(D0, 12), correct=True)
    add_session(db, st, D0 + timedelta(days=1))
    db.commit()
    r = baseline_metrics(db, D0, D0 + timedelta(days=8))
    assert r["time_to_first_answer"]["median_s"] == SUPPRESSED
    assert r["time_to_first_correct"]["p90_s"] == SUPPRESSED
    assert r["hints_per_answered_item"]["mean"] == SUPPRESSED
    assert r["completion"]["completion_rate"] == SUPPRESSED
    assert r["return"]["day_1"]["rate"] == SUPPRESSED


@pytest.mark.parametrize("students", [0, 1, 19, 20, 21, 500])
def test_suppression_threshold_property(students: int) -> None:
    shown = suppress(7, students)
    assert (shown == 7) if students >= MIN_STUDENTS else (shown == SUPPRESSED)


def test_report_carries_no_identifiers_or_free_text(db: Session) -> None:
    students = cohort(db, MIN_STUDENTS)
    r = baseline_metrics(db, D0, D0 + timedelta(days=8))
    blob = json.dumps(r) + render_table(r)
    assert "SECRET ANSWER" not in blob
    assert all(str(s) not in blob for s in students)
    assert r["time_to_first_answer"]["students"] == MIN_STUDENTS  # counts only


def test_the_report_is_read_only(db: Session) -> None:
    cohort(db, 3)
    before = (
        db.scalar(select(func.count()).select_from(SessionRow)),
        db.scalar(select(func.count()).select_from(EventRow)),
    )
    baseline_metrics(db, D0, D0 + timedelta(days=8))
    assert not db.new and not db.dirty and not db.deleted
    after = (
        db.scalar(select(func.count()).select_from(SessionRow)),
        db.scalar(select(func.count()).select_from(EventRow)),
    )
    assert before == after


def test_session_type_filter_defaults_to_practice_and_all_includes_the_rest(db: Session) -> None:
    for _ in range(MIN_STUDENTS):
        st = uuid.uuid4()
        add_session(db, st, D0)
        diag = add_session(db, st, D0)
        row = db.get(SessionRow, diag)
        assert row is not None
        row.type = "diagnostic"
    db.commit()
    default = baseline_metrics(db, D0, D0)
    assert default["window"]["session_type"] == "practice"
    assert default["sessions_in_window"] == MIN_STUDENTS
    assert baseline_metrics(db, D0, D0, "all")["sessions_in_window"] == 2 * MIN_STUDENTS
    only = baseline_metrics(db, D0, D0, "diagnostic")
    assert only["sessions_in_window"] == MIN_STUDENTS
    assert "sessions: diagnostic" in render_table(only)
    assert baseline_metrics(db, D0, D0, "checkpoint")["sessions_in_window"] == 0


def test_return_uses_the_same_type_filter(db: Session) -> None:
    for _ in range(MIN_STUDENTS):
        st = uuid.uuid4()
        d = add_session(db, st, D0)
        db.get(SessionRow, d).type = "diagnostic"  # type: ignore[union-attr]
        add_session(db, st, D0 + timedelta(days=1))  # practice only on day 1
    db.commit()
    until = D0 + timedelta(days=2)
    assert baseline_metrics(db, D0, until, "all")["return"]["day_1"]["rate"] == 1.0
    # practice only: day 0 is the practice session on day 1, so nobody returned on day 2
    assert baseline_metrics(db, D0, until)["return"]["day_1"]["rate"] == 0.0
