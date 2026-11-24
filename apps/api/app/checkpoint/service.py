"""Checkpoint tokens, the checkpoint form and entering a paper checkpoint.

Moved out of app.auth.service unchanged: the identity code (OTP, tokens, consent) stays there and
this feature code sits with the checkpoint package. It calls issue_auth_token for the session
token a redeemed checkpoint token earns."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.actor import Actor
from app.auth.authz import require
from app.auth.service import issue_auth_token
from app.checkpoint.study import (
    consume_token,
    enter_paper_answers,
    form_payload,
    issue_comparison_tokens,
    lookup_checkpoint_token,
    persist_checkpoint_result,
    score_submitted_answers,
)
from app.db.models import CheckpointTokenRow, StudyParticipantRow


def issue_checkpoint_token(
    session: Session,
    actor: Actor,
    *,
    checkpoint_id: str,
    participant_id: uuid.UUID | None,
    form: str | None = None,
    consent_id: uuid.UUID | None = None,
) -> dict:
    require(actor.is_admin)
    if participant_id is None:
        raise HTTPException(status_code=400, detail="participant_id required")
    if consent_id is not None:
        participant = session.get(StudyParticipantRow, participant_id)
        if participant is None or participant.consent_id != consent_id:
            raise HTTPException(status_code=400, detail="consent_ref required")
    return issue_comparison_tokens(
        session,
        checkpoint_id=checkpoint_id,
        participant_id=participant_id,
        form=form,
    )


def redeem_checkpoint_token(session: Session, raw: str) -> str:
    row = lookup_checkpoint_token(session, raw)
    return issue_auth_token(
        session,
        role="comparison",
        checkpoint_id=row.checkpoint_id,
        checkpoint_form=row.form,
    )


def actor_from_checkpoint_cookie(session: Session, raw: str | None) -> Actor | None:
    if not raw:
        return None
    row = lookup_checkpoint_token(session, raw)
    return Actor(
        role="comparison",
        checkpoint_id=row.checkpoint_id,
        checkpoint_form=row.form,
    )


def load_checkpoint_form(session: Session, actor: Actor, checkpoint_id: str, form: str) -> dict:
    if actor.is_comparison:
        require(actor.checkpoint_id == checkpoint_id and actor.checkpoint_form == form)
        payload = form_payload(session, checkpoint_id, form)
        payload["checkpoint_id"] = checkpoint_id
        payload["form"] = form
        return payload
    raise HTTPException(status_code=403, detail="forbidden")


def submit_checkpoint_form(
    session: Session,
    actor: Actor,
    *,
    checkpoint_id: str,
    form: str,
    answers: list[dict[str, Any]],
    occasion: str = "pretest",
    raw_token: str | None = None,
) -> dict[str, Any]:
    if actor.is_comparison:
        require(actor.checkpoint_id == checkpoint_id and actor.checkpoint_form == form)
    elif not (actor.is_admin or actor.is_student):
        raise HTTPException(status_code=403, detail="forbidden")
    result, _ = score_submitted_answers(session, answers)
    participant_id = None
    token_row = None
    if raw_token:
        token_row = lookup_checkpoint_token(session, raw_token)
    elif actor.is_comparison:
        token_row = session.scalar(
            select(CheckpointTokenRow)
            .where(
                CheckpointTokenRow.checkpoint_id == checkpoint_id,
                CheckpointTokenRow.form == form,
                CheckpointTokenRow.used_at.is_(None),
            )
            .order_by(CheckpointTokenRow.issued_at.desc())
        )
        if token_row is None:
            used = session.scalar(
                select(CheckpointTokenRow).where(
                    CheckpointTokenRow.checkpoint_id == checkpoint_id,
                    CheckpointTokenRow.form == form,
                )
            )
            if used is not None:
                raise HTTPException(status_code=409, detail="token already used")
    if token_row is not None:
        consume_token(session, token_row)
        participant_id = token_row.participant_id
        if token_row.occasion:
            occasion = token_row.occasion
    persist_checkpoint_result(
        session,
        checkpoint_id=checkpoint_id,
        form=form,
        score=result,
        occasion=occasion,
        student_id=actor.student_id,
        participant_id=participant_id,
    )
    return result


def enter_paper_checkpoint(
    session: Session,
    actor: Actor,
    *,
    pseudonym: str,
    form: str,
    occasion: str,
    answers: list[dict[str, Any]],
    entry_pass: int,
    checkpoint_id: str,
) -> dict[str, Any]:
    require(actor.is_admin)
    return enter_paper_answers(
        session,
        pseudonym=pseudonym,
        form=form,
        occasion=occasion,
        answers=answers,
        entry_pass=entry_pass,
        checkpoint_id=checkpoint_id,
    )
