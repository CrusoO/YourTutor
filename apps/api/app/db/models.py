from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.db.types import TextArray


class Base(DeclarativeBase):
    pass


JSONType = JSON


class SkillRow(Base):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[dict] = mapped_column(JSONType)
    grade_band: Mapped[list] = mapped_column(JSONType)
    subject: Mapped[str] = mapped_column(String)
    prerequisites: Mapped[list] = mapped_column(JSONType)
    related: Mapped[list] = mapped_column(JSONType)
    misconceptions: Mapped[list] = mapped_column(JSONType)
    bkt: Mapped[dict] = mapped_column(JSONType)
    status: Mapped[str] = mapped_column(String)


class ItemRow(Base):
    __tablename__ = "items"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    skill_ids: Mapped[list] = mapped_column(JSONType)
    primary_skill: Mapped[str] = mapped_column(String, index=True)
    difficulty: Mapped[float] = mapped_column(Float)
    type: Mapped[str] = mapped_column(String)
    pool: Mapped[str] = mapped_column(String, index=True)
    role: Mapped[str] = mapped_column(String, default="procedure")
    stem: Mapped[dict] = mapped_column(JSONType)
    verify: Mapped[dict | str | None] = mapped_column(JSONType, nullable=True)
    options: Mapped[list] = mapped_column(JSONType, default=list)
    answer: Mapped[dict] = mapped_column(JSONType)
    solution_steps: Mapped[list] = mapped_column(JSONType)
    hints: Mapped[list] = mapped_column(JSONType)
    prediction_prompt: Mapped[dict] = mapped_column(JSONType)
    misconception_rules: Mapped[list] = mapped_column(JSONType)
    slip_patterns: Mapped[list] = mapped_column(JSONType, default=list)
    prereq_signatures: Mapped[list] = mapped_column(JSONType, default=list)
    intermediate_values: Mapped[list] = mapped_column(JSONType, default=list)
    min_plausible_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    step_hints: Mapped[list] = mapped_column(JSONType, default=list)
    hint_restate: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    status: Mapped[str] = mapped_column(String, index=True)
    reviewed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    template_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    generator_version: Mapped[str | None] = mapped_column(String, nullable=True)
    template_hash: Mapped[str | None] = mapped_column(String, nullable=True)


class MisconceptionRow(Base):
    __tablename__ = "misconceptions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[dict] = mapped_column(JSONType)
    explanation: Mapped[dict] = mapped_column(JSONType)
    remedial_skill: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)


class MisconceptionHitRow(Base):
    __tablename__ = "misconception_hits"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True
    )
    misconception_id: Mapped[str] = mapped_column(
        ForeignKey("misconceptions.id", ondelete="RESTRICT")
    )
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OverlayRow(Base):
    __tablename__ = "overlays"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    curriculum_id: Mapped[str] = mapped_column(String)
    grade: Mapped[int] = mapped_column(Integer)
    chapter: Mapped[str] = mapped_column(String)
    skill_ids: Mapped[list] = mapped_column(JSONType)
    live: Mapped[bool] = mapped_column(Boolean, default=False)
    # section key -> skill ids (keys resolve against `sections` of every chapter using this overlay)
    section_map: Mapped[dict] = mapped_column(JSONType, default=dict)


class GlossaryTermRow(Base):
    __tablename__ = "glossary_terms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    language: Mapped[str] = mapped_column(String)
    term: Mapped[str] = mapped_column(String)
    translation: Mapped[str] = mapped_column(String)


class LocaleRow(Base):
    __tablename__ = "locales"

    code: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    script: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    fallback_chain: Mapped[list] = mapped_column(JSONType)


class CurriculumRow(Base):
    __tablename__ = "curricula"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    default_timezone: Mapped[str] = mapped_column(String)
    jurisdiction_profile: Mapped[str] = mapped_column(String)
    legacy_board: Mapped[str | None] = mapped_column(String, nullable=True)


class BookRow(Base):
    __tablename__ = "books"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    curriculum_id: Mapped[str] = mapped_column(ForeignKey("curricula.id"))
    grade: Mapped[int] = mapped_column(Integer)
    default_chapter_id: Mapped[str] = mapped_column(String)


class SectionRow(Base):
    __tablename__ = "sections"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    chapter_id: Mapped[str] = mapped_column(ForeignKey("chapters.id"))
    order: Mapped[int] = mapped_column(Integer)
    titles: Mapped[dict] = mapped_column(JSONType)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ChapterRow(Base):
    __tablename__ = "chapters"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    book_id: Mapped[str] = mapped_column(ForeignKey("books.id"))
    overlay_id: Mapped[str] = mapped_column(String)
    chapter_key: Mapped[str] = mapped_column(String)
    titles: Mapped[dict] = mapped_column(JSONType, default=dict)
    position: Mapped[int] = mapped_column(Integer, default=0)


class CheckpointFormRow(Base):
    __tablename__ = "checkpoint_forms"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    checkpoint_id: Mapped[str] = mapped_column(String)
    form_a: Mapped[list] = mapped_column(JSONType)
    form_b: Mapped[list] = mapped_column(JSONType)
    match_map: Mapped[dict] = mapped_column(JSONType)


class LessonRow(Base):
    __tablename__ = "lessons"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    skill_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    title: Mapped[dict] = mapped_column(JSONType)
    source_ref: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    beats: Mapped[list] = mapped_column(JSONType)


class SceneRow(Base):
    __tablename__ = "scenes"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    lesson_id: Mapped[str] = mapped_column(
        String, ForeignKey("lessons.id", ondelete="CASCADE"), index=True
    )
    skill_id: Mapped[str] = mapped_column(String, index=True)
    source_ref: Mapped[str] = mapped_column(String)
    body: Mapped[dict] = mapped_column(JSONType)
    size_bytes: Mapped[int] = mapped_column(Integer)
    duration_s: Mapped[float] = mapped_column(Float)
    kb_per_minute: Mapped[float] = mapped_column(Float)


class WidgetRow(Base):
    __tablename__ = "widgets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    lesson_id: Mapped[str] = mapped_column(
        String, ForeignKey("lessons.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(String)
    body: Mapped[dict] = mapped_column(JSONType)


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    role: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, unique=True)
    locale: Mapped[str] = mapped_column(String, ForeignKey("locales.code"), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    students: Mapped[list[StudentRow]] = relationship(back_populates="parent")
    classes: Mapped[list[ClassRow]] = relationship(back_populates="teacher")


class StudentRow(Base):
    __tablename__ = "students"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    parent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    display_name: Mapped[str] = mapped_column(String)
    grade: Mapped[int] = mapped_column(Integer)
    board: Mapped[str] = mapped_column(String)
    curriculum_id: Mapped[str] = mapped_column(ForeignKey("curricula.id"))
    book_id: Mapped[str] = mapped_column(ForeignKey("books.id"))
    context_key: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    home_language: Mapped[str] = mapped_column(String, ForeignKey("locales.code"))
    exam_language: Mapped[str] = mapped_column(String, ForeignKey("locales.code"))
    exam_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    current_chapter_id: Mapped[str | None] = mapped_column(String, nullable=True)
    pin_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    pin_failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    pin_locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    timezone: Mapped[str] = mapped_column(String)
    family_code: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    parent: Mapped[UserRow] = relationship(back_populates="students")
    consents: Mapped[list[ConsentRow]] = relationship(back_populates="student")


class ConsentRow(Base):
    __tablename__ = "consents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    parent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    version: Mapped[str] = mapped_column(String)
    scopes: Mapped[list[str]] = mapped_column(TextArray)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paper_ref: Mapped[str | None] = mapped_column(String, nullable=True)

    student: Mapped[StudentRow] = relationship(back_populates="consents")


class ClassRow(Base):
    __tablename__ = "classes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    teacher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String)
    board: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    teacher: Mapped[UserRow] = relationship(back_populates="classes")
    memberships: Mapped[list[ClassMembershipRow]] = relationship(back_populates="klass")


class ClassMembershipRow(Base):
    __tablename__ = "class_memberships"

    class_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("classes.id", ondelete="CASCADE"), primary_key=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), primary_key=True
    )

    klass: Mapped[ClassRow] = relationship(back_populates="memberships")


class OtpChallengeRow(Base):
    __tablename__ = "otp_challenges"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, index=True)
    code_hash: Mapped[str] = mapped_column(String)
    ip: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RateEventRow(Base):
    __tablename__ = "rate_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    bucket: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AuthSessionRow(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    token_hash: Mapped[str] = mapped_column(String, unique=True)
    role: Mapped[str] = mapped_column(String)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    student_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=True
    )
    checkpoint_id: Mapped[str | None] = mapped_column(String, nullable=True)
    checkpoint_form: Mapped[str | None] = mapped_column(String, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SessionRow(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    resumable: Mapped[bool] = mapped_column(Boolean, default=False)
    type: Mapped[str] = mapped_column(String)
    active_ms: Mapped[int] = mapped_column(Integer, default=0)
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    plan: Mapped[dict] = mapped_column(JSONType, default=dict)
    llm_called: Mapped[bool] = mapped_column(Boolean, default=False)


class EventRow(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    client_event_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, unique=True, nullable=True)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"))
    item_id: Mapped[str | None] = mapped_column(String, nullable=True)
    event_type: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSONType)
    correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    hint_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    state_before: Mapped[str | None] = mapped_column(String, nullable=True)
    state_after: Mapped[str | None] = mapped_column(String, nullable=True)
    rule_id: Mapped[str | None] = mapped_column(String, nullable=True)


class StudyParticipantRow(Base):
    __tablename__ = "study_participants"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("students.id", ondelete="SET NULL"), nullable=True
    )
    site_id: Mapped[str] = mapped_column(String, index=True)
    pseudonymous_code: Mapped[str] = mapped_column(String, unique=True)
    group: Mapped[str] = mapped_column(String)
    consent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("consents.id", ondelete="SET NULL"), nullable=True
    )
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    assignment_method: Mapped[str] = mapped_column(String, default="random")
    assignment_seed: Mapped[str] = mapped_column(String)
    pretest_form: Mapped[str] = mapped_column(String)
    posttest_form: Mapped[str | None] = mapped_column(String, nullable=True)
    household_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)


class CheckpointResultRow(Base):
    __tablename__ = "checkpoint_results"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("students.id", ondelete="SET NULL"), nullable=True
    )
    participant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("study_participants.id", ondelete="SET NULL"), nullable=True
    )
    checkpoint_id: Mapped[str] = mapped_column(String, index=True)
    form: Mapped[str] = mapped_column(String)
    score: Mapped[float] = mapped_column(Float)
    per_skill: Mapped[dict] = mapped_column(JSONType)
    occasion: Mapped[str] = mapped_column(String)
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CheckpointTokenRow(Base):
    __tablename__ = "checkpoint_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    checkpoint_id: Mapped[str] = mapped_column(String)
    form: Mapped[str] = mapped_column(String)
    token_hash: Mapped[str] = mapped_column(String, unique=True)
    consent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("consents.id", ondelete="SET NULL"), nullable=True
    )
    participant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("study_participants.id", ondelete="SET NULL"), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    occasion: Mapped[str | None] = mapped_column(String, nullable=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PaperEntryRow(Base):
    __tablename__ = "paper_entries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    participant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("study_participants.id", ondelete="CASCADE")
    )
    checkpoint_id: Mapped[str] = mapped_column(String)
    form: Mapped[str] = mapped_column(String)
    occasion: Mapped[str] = mapped_column(String)
    entry_pass: Mapped[int] = mapped_column(Integer)
    answers: Mapped[list] = mapped_column(JSONType)
    mismatches: Mapped[list] = mapped_column(JSONType, default=list)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MasteryRow(Base):
    __tablename__ = "mastery"

    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[str] = mapped_column(String, primary_key=True)
    p_known: Mapped[float] = mapped_column(Float)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    unhinted_correct: Mapped[int] = mapped_column(Integer, default=0)
    hinted_correct: Mapped[int] = mapped_column(Integer, default=0)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ladder_level: Mapped[int] = mapped_column(Integer, default=0)
    ladder_evidence: Mapped[dict] = mapped_column(JSONType, default=dict)  # level -> event ids
    flags: Mapped[dict] = mapped_column(JSONType, default=dict)
    ladder_memory: Mapped[dict] = mapped_column(JSONType, default=dict)  # incremental state


class ReviewCardRow(Base):
    __tablename__ = "review_cards"

    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[str] = mapped_column(String, primary_key=True)
    fsrs_state: Mapped[dict] = mapped_column(JSONType)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TeacherAlertRow(Base):
    """A wheel-spinning (or repeated misconception) alert; only written with `teacher_share`."""

    __tablename__ = "teacher_alerts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True
    )
    skill_id: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReviewQueueRow(Base):
    __tablename__ = "review_queue"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
