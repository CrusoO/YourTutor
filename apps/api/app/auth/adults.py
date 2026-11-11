"""An adult learner (a college student, or anyone else 18 or over) agreeing for themself.

The adult signs in as an account (phone or email, role `parent`), answers the age question, ticks
the `adult` agreement (the same itemised list a guardian sees, plus "I am 18 or over"), and gets
a learner profile that belongs to them. Their consent record is made from their own ticks. A
birth year or a plain declaration is the age input; only `is_adult` (and the year, if given) is
kept. A person whose answer says under 18 is refused here and pointed at the guardian route.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import agreements
from app.auth.actor import Actor
from app.auth.age import resolve_is_adult
from app.auth.authz import require
from app.auth.service import create_student, issue_auth_token
from app.db.models import StudentRow


class AdultStartIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    accepted: list[str]
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    declared_adult: bool | None = None
    display_name: str = Field(default="Me", min_length=1, max_length=60)
    grade: int = Field(ge=1, le=12)
    board: str
    home_language: str = "en"
    exam_language: str = "en"


def _own_learner(db: Session, actor: Actor) -> StudentRow | None:
    assert actor.user_id is not None
    return db.scalar(
        select(StudentRow).where(
            StudentRow.parent_id == actor.user_id, StudentRow.is_adult.is_(True)
        )
    )


def start_adult(db: Session, actor: Actor, body: AdultStartIn) -> dict[str, Any]:
    require(actor.is_parent and actor.user_id is not None)
    if _own_learner(db, actor) is not None:
        raise HTTPException(status_code=409, detail="already_started")
    try:
        adult = resolve_is_adult(body.birth_year, body.declared_adult)
    except ValueError as problem:
        raise HTTPException(status_code=400, detail=str(problem)) from None
    if not adult:
        raise HTTPException(status_code=403, detail="not_adult")
    # Validate the ticks before anything is created.
    if body.version != agreements.VERSION:
        raise HTTPException(status_code=409, detail="agreement_version_changed")
    refusal = agreements.items_error("adult", body.accepted)
    if refusal:
        raise HTTPException(status_code=400, detail=refusal)
    assert actor.user_id is not None
    student = create_student(
        db,
        actor,
        display_name=body.display_name.strip(),
        grade=body.grade,
        board=body.board,
        home_language=body.home_language,
        exam_language=body.exam_language,
    )
    student.is_adult = True
    student.birth_year = body.birth_year
    agreements.store(db, actor.user_id, "adult", body.accepted)
    agreements.apply_to_learner(db, actor, student, "adult", body.accepted)
    token = issue_auth_token(db, role="student", student_id=student.id)
    return {"student_id": str(student.id), "token": token, "scopes_from": "adult"}


def adult_session(db: Session, actor: Actor) -> dict[str, str]:
    """A returning adult: a learner session for their own profile."""
    require(actor.is_parent and actor.user_id is not None)
    student = _own_learner(db, actor)
    if student is None:
        raise HTTPException(status_code=404, detail="no adult profile")
    return {
        "student_id": str(student.id),
        "token": issue_auth_token(db, role="student", student_id=student.id),
    }
