from __future__ import annotations

from sqlalchemy import JSON, Boolean, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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
