"""POST /practice/check-steps: the student's written lines for one equation, checked by code.

Same gates and privacy rule as /doubt/solve (ADR 0005): flag, signed-in non-guest student, the
math_check consent scope, a per-student window, a PII screen, and no storage. The lines are never
written anywhere and never echoed: the only trace of a call is one log line with a salted hash and
the outcome. Every refusal carries a stable `code`.
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
from app.doubt.limits import StudentWindow
from app.practice.schema import MAX_BODY_BYTES, StepCheckRequest
from app.safety import is_paused
from app.verifier.steps import check_steps

logger = logging.getLogger("app.practice")
router = APIRouter(prefix="/practice", tags=["practice"])

SCOPE = "math_check"
# Same numbers as the doubt route (30 an hour, 150 a day), kept in a window of its own.
step_window = StudentWindow()
_SALT = secrets.token_bytes(16)  # new on every start: a logged hash cannot be matched later


def refuse(status: int, code: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code})


def pii_found(req: StepCheckRequest) -> bool:
    text = "\n".join(req.lines)
    return bool(PHONE.search(text) or EMAIL.search(text) or URL.search(text))


def _log(req: StepCheckRequest | None, outcome: str) -> None:
    digest = hashlib.sha256(_SALT + (req.canonical() if req else "").encode()).hexdigest()[:12]
    logger.info("steps outcome=%s h=%s", outcome, digest if req else "-")


@router.post("/check-steps")
async def check_steps_route(request: Request, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    if not settings.step_check_enabled or not settings.scope_math_check_enabled:
        raise refuse(404, "step_check_disabled")
    if not actor.is_student or actor.student_id is None:
        raise refuse(403, "step_check_students_only")
    student_id = actor.student_id
    if is_guest(db, student_id) or not has_scope(db, student_id, SCOPE):
        raise refuse(403, "math_check_consent_required")
    if is_paused(db, student_id):
        raise refuse(403, "step_check_paused")
    if not step_window.allow(student_id):
        _log(None, "rate_limited")
        raise refuse(429, "step_check_rate_limited")
    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        _log(None, "rejected")
        raise refuse(413, "step_check_too_large")
    try:
        req = StepCheckRequest.model_validate_json(body)
    except ValidationError:  # never echo `input`
        _log(None, "rejected")
        raise refuse(422, "step_check_invalid") from None
    if pii_found(req):
        _log(None, "rejected")
        raise refuse(422, "step_check_pii")
    report = await run_in_threadpool(check_steps, req.question, list(req.lines))
    _log(req, report.verdict)
    out = report.as_dict()
    out["label"] = "checked_by_code"
    return out
