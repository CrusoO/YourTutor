from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from app.auth.deps import ActorDep, DbSession
from app.classes import service

router = APIRouter()


class JoinIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(max_length=40)
    label: str | None = Field(default=None, max_length=100)


class CodeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expires_in_days: int | None = None


@router.post("/classes/join")
def join(body: JoinIn, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    return service.join_class(db, actor, body.code, body.label)


@router.get("/students/me/classes")
def my_classes(db: DbSession, actor: ActorDep) -> dict[str, Any]:
    return service.my_classes(db, actor)


@router.delete("/students/me/classes/{class_id}")
def leave(class_id: uuid.UUID, db: DbSession, actor: ActorDep) -> dict[str, str]:
    service.leave_class(db, actor, class_id)
    return {"status": "left"}


@router.post("/classes/{class_id}/join-code")
def set_code(class_id: uuid.UUID, body: CodeIn, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    return service.set_join_code(db, actor, class_id, body.expires_in_days)


@router.delete("/classes/{class_id}/join-code")
def disable_code(class_id: uuid.UUID, db: DbSession, actor: ActorDep) -> dict[str, str]:
    service.disable_join_code(db, actor, class_id)
    return {"status": "disabled"}


@router.get("/classes/{class_id}/join-code")
def code_status(class_id: uuid.UUID, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    return service.join_code_status(db, actor, class_id)


@router.get("/classes/{class_id}/join-requests")
def join_requests(class_id: uuid.UUID, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    return service.join_requests(db, actor, class_id)


@router.delete("/classes/{class_id}/members/{student_id}")
def remove_member(
    class_id: uuid.UUID, student_id: uuid.UUID, db: DbSession, actor: ActorDep
) -> dict[str, str]:
    service.remove_member(db, actor, class_id, student_id)
    return {"status": "removed"}


@router.get("/parents/me/class-requests")
def guardian_requests(db: DbSession, actor: ActorDep) -> dict[str, Any]:
    return service.guardian_requests(db, actor)


@router.post("/parents/me/class-requests/{class_id}/{student_id}/accept")
def accept(
    class_id: uuid.UUID, student_id: uuid.UUID, db: DbSession, actor: ActorDep
) -> dict[str, str]:
    return service.accept_request(db, actor, class_id, student_id)


@router.post("/parents/me/class-requests/{class_id}/{student_id}/decline")
def decline(
    class_id: uuid.UUID, student_id: uuid.UUID, db: DbSession, actor: ActorDep
) -> dict[str, str]:
    return service.decline_request(db, actor, class_id, student_id)
