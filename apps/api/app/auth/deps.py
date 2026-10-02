from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth.actor import Actor
from app.auth.sender import OtpSender, get_otp_sender
from app.auth.service import resolve_token
from app.db.session import get_db

DbSession = Annotated[Session, Depends(get_db)]
OtpDep = Annotated[OtpSender, Depends(get_otp_sender)]


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def optional_actor(
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> Actor | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="invalid authorization")
    return resolve_token(db, token)


def require_actor(actor: Annotated[Actor | None, Depends(optional_actor)]) -> Actor:
    if actor is None:
        raise HTTPException(status_code=401, detail="authentication required")
    return actor


ActorDep = Annotated[Actor, Depends(require_actor)]
OptionalActorDep = Annotated[Actor | None, Depends(optional_actor)]
