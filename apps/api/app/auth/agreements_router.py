"""Routes for role agreements, adult learners and a child's limited-mode profile."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict

from app.auth import adults, agreements, children
from app.auth.deps import ActorDep, DbSession
from app.proxy import client_ip

router = APIRouter()


class AcceptIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    items: list[str]


class WithdrawIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item: str


# ---- agreements -------------------------------------------------------------------------------


@router.get("/agreements/me")
def my_agreements(db: DbSession, actor: ActorDep) -> dict[str, Any]:
    return agreements.my_agreements(db, actor)


@router.get("/agreements/{role}")
def agreement_catalog(role: str) -> dict[str, Any]:
    """The items of a role's agreement (ids and which are required). The wording is the web's."""
    return agreements.catalog(role)


@router.post("/agreements/{role}")
def accept_agreement(role: str, body: AcceptIn, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    agreements.accept(db, actor, role, body.items, body.version)
    return agreements.my_agreements(db, actor)


@router.post("/agreements/{role}/withdraw")
def withdraw_item(role: str, body: WithdrawIn, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    agreements.withdraw(db, actor, role, body.item)
    return agreements.my_agreements(db, actor)


# ---- adult learner ----------------------------------------------------------------------------


@router.post("/adult/start")
def adult_start(body: adults.AdultStartIn, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    return adults.start_adult(db, actor, body)


@router.post("/adult/session")
def adult_session(db: DbSession, actor: ActorDep) -> dict[str, str]:
    return adults.adult_session(db, actor)


# ---- a child's limited-mode profile, and the guardian's approval -------------------------------


@router.post("/children/start")
def child_start(body: children.ChildStartIn, request: Request, db: DbSession) -> dict[str, Any]:
    return children.start_child(db, body, client_ip(request))


@router.get("/children/me/status")
def child_status(db: DbSession, actor: ActorDep) -> dict[str, Any]:
    return children.child_status(db, actor)


@router.post("/children/me/resend")
def child_resend(db: DbSession, actor: ActorDep) -> dict[str, str]:
    return children.resend(db, actor)


@router.post("/approvals/lookup")
def approval_lookup(body: children.TokenIn, db: DbSession) -> dict[str, Any]:
    return children.lookup(db, body.token)


@router.post("/approvals/approve")
def approval_approve(body: children.ApproveIn, db: DbSession) -> dict[str, Any]:
    return children.approve(db, body)


@router.post("/approvals/decline")
def approval_decline(body: children.TokenIn, db: DbSession) -> dict[str, str]:
    return children.decline(db, body.token)
