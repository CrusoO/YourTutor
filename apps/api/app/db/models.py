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
    stem: Mapped[dict] = mapped_column(JSONType)
    verify: Mapped[dict | str | None] = mapped_column(JSONType, nullable=True)
    options: Mapped[list] = mapped_column(JSONType, default=list)
    answer: Mapped[dict] = mapped_column(JSONType)
    solution_steps: Mapped[list] = mapped_column(JSONType)
    hints: Mapped[list] = mapped_column(JSONType)
    prediction_prompt: Mapped[dict] = mapped_column(JSONType)
    misconception_rules: Mapped[list] = mapped_column(JSONType)
    status: Mapped[str] = mapped_column(String, index=True)
    reviewed_by: Mapped[str | None] = mapped_column(String, nullable=True)


class MisconceptionRow(Base):
    __tablename__ = "misconceptions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[dict] = mapped_column(JSONType)
    explanation: Mapped[dict] = mapped_column(JSONType)
    remedial_skill: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)


class OverlayRow(Base):
    __tablename__ = "overlays"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    board: Mapped[str] = mapped_column(String)
    grade: Mapped[int] = mapped_column(Integer)
    chapter: Mapped[str] = mapped_column(String)
    skill_ids: Mapped[list] = mapped_column(JSONType)
    live: Mapped[bool] = mapped_column(Boolean, default=False)


class GlossaryTermRow(Base):
    __tablename__ = "glossary_terms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    language: Mapped[str] = mapped_column(String)
    term: Mapped[str] = mapped_column(String)
    translation: Mapped[str] = mapped_column(String)


class CheckpointFormRow(Base):
    __tablename__ = "checkpoint_forms"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    checkpoint_id: Mapped[str] = mapped_column(String)
    form_a: Mapped[list] = mapped_column(JSONType)
    form_b: Mapped[list] = mapped_column(JSONType)
    match_map: Mapped[dict] = mapped_column(JSONType)


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    role: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, unique=True)
    locale: Mapped[str] = mapped_column(String, default="en")
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
    home_language: Mapped[str] = mapped_column(String)
    exam_language: Mapped[str] = mapped_column(String)
    exam_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    current_chapter_id: Mapped[str | None] = mapped_column(String, nullable=True)
    pin_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    pin_failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    pin_locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    timezone: Mapped[str] = mapped_column(String)
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


class CheckpointTokenRow(Base):
    __tablename__ = "checkpoint_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    checkpoint_id: Mapped[str] = mapped_column(String)
    form: Mapped[str] = mapped_column(String)
    token_hash: Mapped[str] = mapped_column(String, unique=True)
    consent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("consents.id", ondelete="SET NULL"), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


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


class ReviewCardRow(Base):
    __tablename__ = "review_cards"

    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[str] = mapped_column(String, primary_key=True)
    fsrs_state: Mapped[dict] = mapped_column(JSONType)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ReviewQueueRow(Base):
    __tablename__ = "review_queue"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
