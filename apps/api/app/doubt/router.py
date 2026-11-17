"""POST /doubt/solve: a structured, confirmed maths expression in, a kernel-checked trace out.

ADR 0005. Never free text, never a model, never stored. The expression is not written anywhere:
the only trace of a call is one log line with a salted hash and the outcome class. Every refusal
carries a stable `code` and never echoes the request.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError

from app.ask.guard import EMAIL, PHONE, URL
from app.auth.consent import has_scope, is_guest
from app.auth.deps import ActorDep, DbSession
from app.config import settings
from app.doubt.limits import student_window
from app.doubt.schema import MAX_BODY_BYTES, DoubtExpr
from app.doubt.solver import solve_doubt
from app.safety import is_paused

logger = logging.getLogger("app.doubt")
router = APIRouter(prefix="/doubt", tags=["doubt"])

SCOPE = "math_check"
# Changes on every start, so a logged hash cannot be matched across restarts or to a guess table.
_SALT = secrets.token_bytes(16)


def refuse(status: int, code: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code})


def pii_found(req: DoubtExpr) -> bool:
    """The existing PII patterns (phone, email, link) over the request's numbers.

    The schema already caps a number at nine digits; a nine-digit number still reads as a phone
    number to the shared pattern, so it is refused too. Numbers are joined with a comma, which no
    pattern treats as part of a number, so two coefficients are never read as one.
    """
    text = ",".join(req.numbers())
    return bool(PHONE.search(text) or EMAIL.search(text) or URL.search(text))


def _log(req: DoubtExpr | None, outcome: str) -> None:
    digest = hashlib.sha256(_SALT + (req.canonical() if req else "").encode()).hexdigest()[:12]
    logger.info("doubt outcome=%s h=%s", outcome, digest if req else "-")


@router.post("/solve")
async def solve(request: Request, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    if not settings.scope_math_check_enabled:
        raise refuse(404, "doubt_server_disabled")
    if not actor.is_student or actor.student_id is None:
        raise refuse(403, "doubt_students_only")
    student_id = actor.student_id
    if is_guest(db, student_id) or not has_scope(db, student_id, SCOPE):
        raise refuse(403, "math_check_consent_required")
    if is_paused(db, student_id):
        raise refuse(403, "doubt_paused")
    if not student_window.allow(student_id):
        _log(None, "rate_limited")
        raise refuse(429, "doubt_rate_limited")
    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        _log(None, "rejected")
        raise refuse(413, "doubt_too_large")
    try:
        req = DoubtExpr.model_validate_json(body)
    except ValidationError:  # never echo `input`
        _log(None, "rejected")
        raise refuse(422, "doubt_invalid") from None
    if pii_found(req):
        _log(None, "rejected")
        raise refuse(422, "doubt_pii")
    result = await run_in_threadpool(solve_doubt, req)
    _log(req, "verified" if result["verified"] else "not_verified")
    return result
