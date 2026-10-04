from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.auth import service
from app.auth.deps import ActorDep, DbSession, OptionalActorDep
from app.auth.router import CheckpointAnswersIn, RedeemIn, StudyIn, TokenIn, _token_body
from app.checkpoint.study import COOKIE_NAME, REFERRER_POLICY
from app.config import settings
from app.research.deps import require_research_module

router = APIRouter(dependencies=[Depends(require_research_module)])


@router.get("/analytics/export")
def analytics(db: DbSession, actor: ActorDep) -> dict[str, Any]:
    return service.analytics_export(db, actor)


@router.post("/study/participants")
def enrol_participant(body: StudyIn, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    row = service.enrol_study_participant(
        db,
        actor,
        site_id=body.site_id,
        group=body.group,
        consent_id=body.consent_id,
        student_id=body.student_id,
        household_id=body.household_id,
    )
    return {
        "id": str(row.id),
        "group": row.group,
        "site_id": row.site_id,
        "household_id": row.household_id,
        "pretest_form": row.pretest_form,
        "posttest_form": row.posttest_form,
        "assignment_method": row.assignment_method,
        "assignment_seed": row.assignment_seed,
        "pseudonym": row.pseudonymous_code,
    }


@router.post("/checkpoints/{checkpoint_id}/tokens")
def issue_token(
    checkpoint_id: str, body: TokenIn, db: DbSession, actor: ActorDep
) -> dict[str, Any]:
    return service.issue_checkpoint_token(
        db,
        actor,
        checkpoint_id=checkpoint_id,
        participant_id=body.participant_id,
        form=body.form,
        consent_id=body.consent_id,
    )


@router.post("/checkpoints/redeem")
def redeem(body: RedeemIn, db: DbSession) -> dict[str, str]:
    return _token_body(service.redeem_checkpoint_token(db, body.token))


@router.get("/checkpoints/{checkpoint_id}/forms/{form}")
def load_form(
    checkpoint_id: str,
    form: str,
    request: Request,
    db: DbSession,
    actor: OptionalActorDep,
    token: str | None = Query(default=None),
) -> Any:
    if token:
        service.lookup_checkpoint_token(db, token)
        redirect = RedirectResponse(url=str(request.url.replace(query="")), status_code=302)
        redirect.set_cookie(
            COOKIE_NAME,
            token,
            httponly=True,
            max_age=settings.session_ttl_seconds,
            samesite="lax",
            path="/",
        )
        redirect.headers["Referrer-Policy"] = REFERRER_POLICY
        return redirect
    resolved = actor or service.actor_from_checkpoint_cookie(db, request.cookies.get(COOKIE_NAME))
    if resolved is None:
        raise HTTPException(status_code=401, detail="authentication required")
    payload = service.load_checkpoint_form(db, resolved, checkpoint_id, form)
    return JSONResponse(payload, headers={"Referrer-Policy": REFERRER_POLICY})


@router.post("/checkpoints/{checkpoint_id}/forms/{form}/submit")
def submit_form(
    checkpoint_id: str,
    form: str,
    body: CheckpointAnswersIn,
    request: Request,
    actor: OptionalActorDep,
    db: DbSession,
) -> dict[str, Any]:
    raw = request.cookies.get(COOKIE_NAME)
    resolved = actor or service.actor_from_checkpoint_cookie(db, raw)
    if resolved is None:
        raise HTTPException(status_code=401, detail="authentication required")
    return service.submit_checkpoint_form(
        db,
        resolved,
        checkpoint_id=checkpoint_id,
        form=form,
        answers=body.answers,
        occasion=body.occasion,
        raw_token=raw,
    )
