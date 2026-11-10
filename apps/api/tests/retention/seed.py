"""Seed one row in every table that refers to an account's learner, and list them by reflection.

`referencing_tables` walks the model metadata, so a table added later that points at a student or
user shows up here without anyone remembering to list it.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth.security import now_utc
from app.auth.sender import MemoryOtpSender
from app.db.models import (
    AuthSessionRow,
    Base,
    CheckpointResultRow,
    CheckpointTokenRow,
    ClassMembershipRow,
    ClassRow,
    ConsentRow,
    EventRow,
    GroupLessonRow,
    GroupResultRow,
    ItemRow,
    LessonRecordRow,
    LlmCallRow,
    LoopBRecordRow,
    LoopBSnapshotRow,
    MasteryRow,
    MisconceptionHitRow,
    MisconceptionRow,
    OtpChallengeRow,
    PaperEntryRow,
    ReportLogRow,
    ReviewCardRow,
    ReviewQueueRow,
    SafetyFlagRow,
    SessionRow,
    StudentRow,
    StudyParticipantRow,
    TeacherAlertRow,
    UserRow,
    VideoJobRow,
)
from tests.conftest import auth_header, seed_user, signup

# Tables the delete code knows about (every table that refers, directly or through another such
# table, to a student or a user of the account). A new table not named here fails the test below:
# add its delete to purge_students (app/auth/service.py), its export to app/auth/export.py if it
# holds the learner's data, then add it here.
HANDLED = frozenset(
    {
        "auth_sessions",
        "checkpoint_results",
        "checkpoint_tokens",
        "class_memberships",
        "consents",
        "events",
        "group_lessons",
        "group_results",
        "lesson_records",
        "llm_calls",
        "loop_b_records",
        "loop_b_snapshots",
        "mastery",
        "misconception_hits",
        "paper_entries",
        "report_log",
        "review_cards",
        "review_queue",
        "safety_flags",
        "sessions",
        "students",
        "study_participants",
        "teacher_alerts",
        "video_jobs",
    }
)
# Referencing tables that hold another person's rows by design (a teacher's own classes): the
# account's delete does not remove them, and they are not seeded.
NOT_THE_ACCOUNTS = frozenset({"classes"})


def referencing_tables() -> dict[str, list[tuple[str, str]]]:
    """table -> [(its column, the table it points to)] for every table that reaches an account.

    Starts from `students` and `users`, then adds tables pointing at any table already in the
    set, until nothing new appears. Catalog tables (items, locales, ...) are never reached because
    only the direction "this table refers to an account table" is followed.
    """
    found: dict[str, list[tuple[str, str]]] = {}
    reached = {"students", "users"}
    changed = True
    while changed:
        changed = False
        for table in Base.metadata.sorted_tables:
            if table.name in reached:
                continue
            links = [
                (fk.parent.name, fk.column.table.name)
                for fk in table.foreign_keys
                if fk.column.table.name in reached
            ]
            if links:
                found[table.name] = links
                reached.add(table.name)
                changed = True
    return found


def account_rows(db: Session, user_ids: list[uuid.UUID], student_ids: list[uuid.UUID]) -> dict:
    """How many rows in every reaching table belong to these ids (directly or by a chain)."""
    ids: dict[str, set[Any]] = {"users": set(user_ids), "students": set(student_ids)}
    counts: dict[str, int] = {
        "users": len(db.scalars(select(UserRow.id).where(UserRow.id.in_(user_ids))).all()),
        "students": len(
            db.scalars(select(StudentRow.id).where(StudentRow.id.in_(student_ids))).all()
        ),
    }
    links = referencing_tables()
    pending = dict(links)
    while pending:
        progressed = False
        for name, cols in list(pending.items()):
            if any(target not in ids and target in pending for _, target in cols):
                continue
            table = Base.metadata.tables[name]
            clauses = [
                table.c[col].in_(ids.get(target, set()) or [uuid.uuid4()]) for col, target in cols
            ]
            rows = db.execute(select(table).where(or_(*clauses))).mappings().all()
            counts[name] = len(rows)
            if "id" in table.c:
                ids[name] = {r["id"] for r in rows}
            del pending[name]
            progressed = True
        assert progressed, "a cycle of references among account tables"
    return counts


class Account:
    def __init__(self, email: str, user_id: uuid.UUID, students: list[uuid.UUID], token: str):
        self.email = email
        self.user_id = user_id
        self.students = students
        self.token = token


def make_account(
    client: TestClient, sender: MemoryOtpSender, db: Session, email: str, jobs: Path | None = None
) -> Account:
    """A signed-in guardian with two learners, and one row in every table that refers to them."""
    token = signup(client, sender, email)
    kids = []
    for name in ("Ava", "Ben"):
        res = client.post(
            "/students",
            json={"display_name": name, "grade": 9, "board": "bhutan"},
            headers=auth_header(token),
        )
        assert res.status_code == 200, res.text
        kids.append(uuid.UUID(res.json()["id"]))
    user = db.scalar(select(UserRow).where(UserRow.email == email))
    assert user is not None
    account = Account(email, user.id, kids, token)
    for kid in kids:
        seed_learner(db, account, kid, jobs, first=kid == kids[0])
    db.commit()
    return account


def seed_learner(
    db: Session, account: Account, sid: uuid.UUID, jobs: Path | None, first: bool
) -> None:
    now = now_utc()
    tag = account.email.split("@")[0]
    student = db.get(StudentRow, sid)
    assert student is not None
    if db.get(MisconceptionRow, f"MC.{tag}") is None:
        db.add(
            MisconceptionRow(
                id=f"MC.{tag}", title={}, explanation={}, remedial_skill="S", status="draft"
            )
        )
        db.add(
            ItemRow(
                id=f"ITEM.{tag}",
                skill_ids=[],
                primary_skill="S",
                difficulty=0.5,
                type="mcq",
                pool="practice",
                stem={},
                answer={},
                solution_steps=[],
                hints=[],
                prediction_prompt={},
                misconception_rules=[],
                status="draft",
            )
        )
        db.flush()
    sess = SessionRow(
        id=uuid.uuid4(), student_id=sid, started_at=now, type="practice", last_active_at=now
    )
    db.add(sess)
    db.flush()
    consent = ConsentRow(
        id=uuid.uuid4(),
        student_id=sid,
        parent_id=account.user_id,
        version="v1",
        scopes=["tutoring"],
        granted_at=now,
    )
    db.add(consent)
    db.flush()
    part = StudyParticipantRow(
        id=uuid.uuid4(),
        student_id=sid,
        site_id="s",
        pseudonymous_code=f"P-{uuid.uuid4().hex[:8]}",
        group="a",
        consent_id=consent.id,
        assigned_at=now,
        assignment_seed="secret-seed",
        pretest_form="A",
        household_id=student.family_code,
    )
    db.add(part)
    db.flush()
    db.add_all(
        [
            EventRow(
                id=uuid.uuid4(),
                session_id=sess.id,
                item_id=f"ITEM.{tag}",
                event_type="answer",
                payload={"text": f"answer-of-{tag}"},
                correct=True,
                created_at=now,
            ),
            LlmCallRow(
                id=uuid.uuid4(),
                created_at=now,
                session_id=sess.id,
                purpose="hint",
                prompt_version="v1",
                band_id="b",
                language="en",
                outcome="llm",
            ),
            MasteryRow(
                student_id=sid, skill_id="S1", p_known=0.5, last_updated=now, ladder_level=2
            ),
            ReviewCardRow(student_id=sid, skill_id="S1", fsrs_state={}, due_at=now),
            MisconceptionHitRow(
                id=uuid.uuid4(),
                student_id=sid,
                misconception_id=f"MC.{tag}",
                item_id=f"ITEM.{tag}",
                created_at=now,
            ),
            LoopBRecordRow(student_id=sid, version=1, data={"k": 1}, updated_at=now),
            LoopBSnapshotRow(
                id=uuid.uuid4(),
                student_id=sid,
                session_id="s",
                watermark=1,
                record_version=1,
                versions={},
                payload={},
                created_at=now,
            ),
            LessonRecordRow(
                id=uuid.uuid4(),
                student_id=sid,
                topic=f"topic-{tag}",
                taken_at=now,
                items=[],
                created_at=now,
            ),
            SafetyFlagRow(
                id=uuid.uuid4(), student_id=sid, kind="distress", source="ask", created_at=now
            ),
            ReportLogRow(
                id=uuid.uuid4(),
                student_id=sid,
                parent_id=account.user_id,
                week_key="2026-W01",
                channel="email",
                sent_at=now,
            ),
            ReviewQueueRow(id=uuid.uuid4(), student_id=sid, created_at=now),
            TeacherAlertRow(
                id=uuid.uuid4(), student_id=sid, skill_id="S1", type="wheel", created_at=now
            ),
            AuthSessionRow(
                id=uuid.uuid4(),
                token_hash=f"hash-{uuid.uuid4().hex}",
                role="student",
                student_id=sid,
                expires_at=now + timedelta(days=1),
                created_at=now,
            ),
            CheckpointResultRow(
                id=uuid.uuid4(),
                student_id=sid,
                participant_id=part.id,
                checkpoint_id="cp",
                form="A",
                score=0.5,
                per_skill={},
                occasion="pre",
                taken_at=now,
            ),
            CheckpointTokenRow(
                id=uuid.uuid4(),
                checkpoint_id="cp",
                form="A",
                token_hash=f"tok-{uuid.uuid4().hex}",
                consent_id=consent.id,
                participant_id=part.id,
                expires_at=now,
                issued_at=now,
            ),
            PaperEntryRow(
                id=uuid.uuid4(),
                participant_id=part.id,
                checkpoint_id="cp",
                form="A",
                occasion="pre",
                entry_pass=1,
                answers=[],
                created_at=now,
            ),
        ]
    )
    teacher = db.scalar(select(UserRow).where(UserRow.email == "teacher-of-class@example.com"))
    if teacher is None:
        teacher = seed_user(db, "teacher", "teacher-of-class@example.com")
    klass = db.scalar(select(ClassRow).where(ClassRow.teacher_id == teacher.id))
    if klass is None:
        klass = ClassRow(
            id=uuid.uuid4(),
            teacher_id=teacher.id,
            name="C",
            curriculum_id="bhutan",
            created_at=now,
        )
        db.add(klass)
        db.flush()
    db.add(ClassMembershipRow(class_id=klass.id, student_id=sid))
    video_name = f"job-{uuid.uuid4().hex[:12]}"
    result_path = str((jobs or Path("jobs")) / video_name)
    if jobs is not None:
        (jobs / video_name).mkdir(parents=True, exist_ok=True)
        (jobs / video_name / "lesson.mp4").write_bytes(b"mp4")
    db.add(
        VideoJobRow(
            id=uuid.uuid4(),
            student_id=sid,
            node_id="n",
            request_json={"prompt": f"typed-{tag}"},
            idempotency_key=f"idem-{uuid.uuid4().hex}",
            status="done",
            result_path=result_path,
            created_at=now,
            completed_at=now,
        )
    )
    if first:
        db.add(
            OtpChallengeRow(
                id=uuid.uuid4(),
                email=account.email,
                code_hash="h",
                ip="1.2.3.4",
                created_at=now,
                expires_at=now,
            )
        )
        group = GroupLessonRow(
            id=uuid.uuid4(),
            owner_id=account.user_id,
            code=f"g{uuid.uuid4().hex[:10]}",
            prompt="p",
            language="en",
            blocks=[],
            created_at=now,
        )
        db.add(group)
        db.flush()
        db.add(
            GroupResultRow(
                id=uuid.uuid4(), group_id=group.id, participant="x", submitted_at=now, items=[]
            )
        )
        db.add(
            VideoJobRow(
                id=uuid.uuid4(),
                org_id=account.user_id,
                node_id="n",
                request_json={},
                idempotency_key=f"idem-{uuid.uuid4().hex}",
                status="done",
                created_at=now,
            )
        )


def count(db: Session, model: type) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def days_ago(days: float, now: datetime | None = None) -> datetime:
    return (now or now_utc()) - timedelta(days=days)
