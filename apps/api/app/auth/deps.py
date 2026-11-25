from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth import agreements
from app.auth.actor import Actor
from app.auth.sender import OtpSender, get_otp_sender, get_sms_otp_sender
from app.auth.service import resolve_token
from app.db.session import get_db

DbSession = Annotated[Session, Depends(get_db)]
OtpDep = Annotated[OtpSender, Depends(get_otp_sender)]
SmsOtpDep = Annotated[OtpSender, Depends(get_sms_otp_sender)]


# An invited reviewer may call only the content-review routes and the sign-in basics. Deny by
# default here, so no route (present or future) can hand a reviewer learner or class data.
REVIEWER_PATHS = (
    "/staff/review",
    "/auth/me",
    "/auth/options",
    "/auth/request-otp",
    "/auth/verify-otp",
    "/agreements/me",  # a reviewer may read and accept their own terms, and nothing else here
    "/agreements/reviewer",
)


def optional_actor(
    request: Request,
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> Actor | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="invalid authorization")
    actor = resolve_token(db, token)
    if actor.is_reviewer and not request.url.path.startswith(REVIEWER_PATHS):
        raise HTTPException(status_code=403, detail="forbidden")
    if actor.is_reviewer and request.url.path.startswith("/staff/review"):
        agreements.require_reviewer_terms(db, actor)  # every review route, now and later
    return actor


def require_actor(actor: Annotated[Actor | None, Depends(optional_actor)]) -> Actor:
    if actor is None:
        raise HTTPException(status_code=401, detail="authentication required")
    return actor


ActorDep = Annotated[Actor, Depends(require_actor)]
OptionalActorDep = Annotated[Actor | None, Depends(optional_actor)]
