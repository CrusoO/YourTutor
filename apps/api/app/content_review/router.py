"""GET/POST /staff/review/...: the staff-only content review screen's API.

Only a signed-in teacher or admin may call it (a student, guest or parent gets 403, no token 401).
When `REVIEWER_ALLOWLIST` is set the account's label must be on it (see `reviewer_allowed`).
With `REVIEWER_DESK_ENABLED` on, an invited `reviewer` account may call it too (and nothing else),
cards are blind until the reviewer has decided, every decision is kept as history, and an admin
can invite and suspend reviewers and read the pay export.
It never returns student data and never writes repo files: decisions go to `content_reviews`, and
`python -m app.content apply-reviews` writes the YAML.
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field

from app.auth.actor import Actor
from app.auth.authz import FORBIDDEN
from app.auth.deps import ActorDep, DbSession
from app.auth.security import now_utc
from app.config import settings
from app.content.signatures import item_content_hash
from app.content_review import service, snapshot, templates
from app.registries.paths import content_root

router = APIRouter(prefix="/staff/review", tags=["staff-review"])

Status = Literal["pending", "ready", "flagged", "all", "todo"]


class FixNote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_index: int = Field(ge=0, le=service.CHECK_COUNT - 1)
    text: str = Field(max_length=2000)


class DecisionIn(BaseModel):
    """`skip`, `withdraw` and every field after `note` are for the reviewer desk
    (REVIEWER_DESK_ENABLED); with the desk off, sending any of them is a 422."""

    model_config = ConfigDict(extra="forbid")

    content_hash: str = Field(min_length=1, max_length=64)
    decision: Literal["approve", "reject", "fix", "skip", "withdraw"]
    note: str | None = Field(default=None, max_length=2000)
    severity: Literal["blocker", "must_fix", "nice_to_fix"] | None = None
    reason_code: Literal["1", "2", "3", "4", "5", "6"] | None = None
    checks: list[bool | None] | None = Field(
        default=None, min_length=service.CHECK_COUNT, max_length=service.CHECK_COUNT
    )
    fix_notes: list[FixNote] | None = Field(default=None, max_length=service.CHECK_COUNT)
    active_seconds: int | None = Field(default=None, ge=0, le=service.MAX_ACTIVE_SECONDS)

    def desk_fields_used(self) -> bool:
        extras = (self.severity, self.reason_code, self.checks, self.fix_notes, self.active_seconds)
        return self.decision in ("skip", "withdraw") or any(v is not None for v in extras)


class InviteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _reviewer(actor: Actor) -> tuple[uuid.UUID, str]:
    invited = actor.is_reviewer and settings.reviewer_desk_enabled
    if not (actor.is_teacher or actor.is_admin or invited) or actor.user_id is None:
        raise FORBIDDEN
    label = actor.email or str(actor.user_id)
    # an invited reviewer was let in by an admin, so the allowlist (for staff labels) is not asked
    if not invited and not service.reviewer_allowed(label):
        raise FORBIDDEN
    return actor.user_id, label


def _desk_admin(actor: Actor) -> uuid.UUID:
    """Admin-only desk routes. With the desk off they answer like an unknown route."""
    if not settings.reviewer_desk_enabled:
        raise HTTPException(status_code=404, detail="not found")
    if not actor.is_admin or actor.user_id is None:
        raise FORBIDDEN
    return actor.user_id


def _hindi_for(data: snapshot.ReviewData, item_id: str) -> dict[str, Any] | None:
    """The item's Hindi strings from the snapshot; None means read them from the YAML file."""
    if data.hindi is None:
        return None
    return data.hindi.get(item_id, {"stem": None, "options": {}})


@router.get("/items")
def list_items(
    db: DbSession,
    actor: ActorDep,
    status: Status = "pending",
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    grade: Annotated[int | None, Query(alias="class", ge=1, le=12)] = None,
    subject: Annotated[str | None, Query(max_length=40)] = None,
    chapter: Annotated[str | None, Query(max_length=120)] = None,
    check: Annotated[Literal["needs_person", "machine_checked"] | None, Query()] = None,
) -> dict[str, Any]:
    """Draft items, in id order, one page at a time (each card runs the solver).

    pending: draft, not yet two approvals, nothing blocking. ready: two approvals, waiting for
    `apply-reviews`. flagged: a reject or fix stands. all: every draft. With the reviewer desk on,
    an item you have not decided yet always counts as pending (so a filter cannot show how others
    voted). todo (desk on only): the drafts you have no standing decision on for their current
    content (a withdrawn decision is undecided again, a skip is not a decision), whatever others
    voted: the same rule as the `pending` count in `/chapters`. Desk on only: `class`, `subject`
    and `chapter` (from `/chapters`) narrow the list. `check` (needs_person or machine_checked;
    default both) narrows by how the answer was checked."""
    me, _ = _reviewer(actor)
    if not settings.reviewer_desk_enabled and (grade, subject, chapter) != (None, None, None):
        raise HTTPException(status_code=422, detail="the reviewer desk is not switched on")
    if status == "todo" and not settings.reviewer_desk_enabled:
        raise HTTPException(status_code=422, detail="the reviewer desk is not switched on")
    root = content_root()
    data = service.load_review_data(root)
    drafts = [
        item
        for item in data.items
        if service.is_draft(item)
        and service.in_group(data, item, grade, subject, chapter)
        and (check is None or service.check_tag(item) == check)
    ]
    mode = templates.template_mode()
    chosen = []
    if mode and status == "todo":
        # template mode: the samples of question types you still owe and all items of blocked ones
        todo = templates.analyse(db, data).todo_ids(me)
        chosen = [item for item in drafts if item.id in todo]
    else:
        pairs = {item.id: (item.id, item_content_hash(item)) for item in drafts}
        reviews = service.reviews_for_items(db, list(pairs.values()))
        for item in drafts:
            rows = reviews[pairs[item.id]]
            if status == "todo":
                if not service.has_decided(rows, me):
                    chosen.append(item)
                continue
            state = service.list_state(rows, me)
            if status in ("all", state):
                chosen.append(item)
    page = chosen[offset : offset + limit]
    info = templates.sample_info(templates.build_versions(data)) if mode else {}
    out: dict[str, Any] = {
        "total": len(chosen),
        "offset": offset,
        "items": [
            service.card(
                db,
                root,
                item,
                data.labels,
                me,
                _hindi_for(data, item.id),
                data.explanations,
                {"template": info.get(item.id)} if mode else None,
            )
            for item in page
        ],
    }
    if mode:
        out["template_mode"] = True
    return out


@router.get("/check-tags")
def check_tag_summary(actor: ActorDep) -> dict[str, Any]:
    """Admin only, read-only: how many draft items carry each check tag, in total and per class
    and subject. Records only; nothing a learner is served depends on it."""
    _desk_admin(actor)
    data = service.load_review_data(content_root())
    drafts = [item for item in data.items if service.is_draft(item)]
    per: dict[str, dict[str, int]] = {}
    for item in drafts:
        chapter = data.chapters.get(data.item_chapter.get(item.id, snapshot.UNMAPPED_ID))
        key = f"{chapter.grade}/{chapter.subject}" if chapter else "unmapped"
        per.setdefault(key, dict.fromkeys(service.CHECK_TAGS, 0))[service.check_tag(item)] += 1
    return {
        "labels": service.CHECK_LABELS,
        "total": service.tag_counts(drafts),
        "by_class_subject": dict(sorted(per.items())),
    }


@router.get("/chapters")
def list_chapters(db: DbSession, actor: ActorDep) -> dict[str, Any]:
    """Desk on only: the class / subject / chapter groups that have draft items, each with its
    item count and how many are still to do for the caller (the `todo` list filter).
    Only content that exists is listed. `unmapped_chapters` names groups with no curriculum entry
    (their title comes from the overlay) so the gap is visible."""
    if not settings.reviewer_desk_enabled:
        raise HTTPException(status_code=404, detail="not found")
    me, _ = _reviewer(actor)
    data = service.load_review_data(content_root())
    groups, gaps = service.chapter_groups(db, data, me)
    out: dict[str, Any] = {"groups": groups, "chapters_without_curriculum_entry": gaps}
    if templates.template_mode():
        out["groups"] = templates.apply_to_groups(templates.analyse(db, data), data, groups, me)
        out["template_mode"] = True
    return out


@router.post("/items/{item_id}/decision")
def decide(item_id: str, body: DecisionIn, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    me, label = _reviewer(actor)
    root = content_root()
    data = service.load_review_data(root)
    item = next((i for i in data.items if i.id == item_id), None)
    if item is None or not service.is_draft(item):
        raise HTTPException(status_code=404, detail="item not found")
    if body.content_hash != item_content_hash(item):
        raise HTTPException(status_code=409, detail="the item changed; reload and review again")
    note = (body.note or "").strip() or None
    if body.decision == "withdraw" and settings.reviewer_desk_enabled:
        rows = service.reviews_for(db, item_id, body.content_hash)
        if me not in service.standing(rows):
            raise HTTPException(status_code=409, detail="you have no decision to withdraw")
    desk = settings.reviewer_desk_enabled
    if not desk and body.desk_fields_used():
        raise HTTPException(status_code=422, detail="the reviewer desk is not switched on")
    extra: dict[str, Any] = {}
    if desk:
        written = [(n.question_index, n.text.strip()) for n in body.fix_notes or []]
        errors = service.check_desk_decision(
            decision=body.decision,
            severity=body.severity,
            reason_code=body.reason_code,
            checks=body.checks,
            fix_notes=written,
            note=note,
        )
        if errors:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "invalid_decision",
                    "errors": [{"field": e.field, "message": e.message} for e in errors],
                },
            )
        extra = {
            "severity": body.severity,
            "reason_code": body.reason_code,
            "checks": body.checks,
            "fix_notes": [{"question_index": i, "text": t} for i, t in written] or None,
            "active_seconds": body.active_seconds,
        }
    elif body.decision in ("reject", "fix") and note is None:
        raise HTTPException(status_code=422, detail="a note is required to reject or ask for a fix")
    service.record_decision(
        db,
        item_id=item_id,
        content_hash=body.content_hash,
        reviewer_id=me,
        reviewer_label=label,
        decision=body.decision,
        note=note,
        now=now_utc(),
        template_key=service.template_key_of(item),
        **extra,
    )
    shown = None
    if templates.template_mode():
        shown = {"template": templates.sample_info(templates.build_versions(data)).get(item.id)}
    return service.card(
        db, root, item, data.labels, me, _hindi_for(data, item.id), data.explanations, shown
    )


def _reviewer_out(user: Any) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "suspended": user.suspended_at is not None,
    }


@router.post("/reviewers")
def invite_reviewer(body: InviteIn, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    """Admin only: invite an outside reviewer by email. They then sign in with the usual email
    code. Never turns an existing teacher, parent or admin account into a reviewer."""
    _desk_admin(actor)
    user = service.invite_reviewer(db, body.email, now_utc())
    if user.role != "reviewer":
        raise HTTPException(status_code=409, detail="that email already belongs to another account")
    return _reviewer_out(user)


@router.post("/reviewers/{reviewer_id}/suspend")
def suspend_reviewer(reviewer_id: uuid.UUID, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    _desk_admin(actor)
    user = service.set_reviewer_suspended(db, reviewer_id, True, now_utc())
    if user is None:
        raise HTTPException(status_code=404, detail="reviewer not found")
    return _reviewer_out(user)


@router.post("/reviewers/{reviewer_id}/reinstate")
def reinstate_reviewer(reviewer_id: uuid.UUID, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    _desk_admin(actor)
    user = service.set_reviewer_suspended(db, reviewer_id, False, now_utc())
    if user is None:
        raise HTTPException(status_code=404, detail="reviewer not found")
    return _reviewer_out(user)


@router.post("/reviewers/{reviewer_id}/sign-in-code")
def reviewer_sign_in_code(reviewer_id: uuid.UUID, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    """Admin only: make a one-time sign-in code for an invited reviewer, to hand over by hand (no
    email needed). The reviewer signs in at /staff/login with their email and this code. The code
    is in this response only: it is stored hashed, never logged and never shown again."""
    admin_id = _desk_admin(actor)
    try:
        issued = service.issue_reviewer_signin_code(db, reviewer_id, admin_id)
    except service.SignInCodeRefused as refused:
        raise HTTPException(status_code=refused.status_code, detail=refused.detail) from None
    if issued is None:
        raise HTTPException(status_code=404, detail="reviewer not found")
    code, expires = issued
    return {"code": code, "expires_at": expires.isoformat()}


@router.get("/reviewers")
def list_reviewers(db: DbSession, actor: ActorDep) -> dict[str, Any]:
    """Admin only: every invited reviewer with suspended, invited at, last decision time and
    decision count. Account and activity facts only; no learner data, no votes."""
    _desk_admin(actor)
    return {"reviewers": service.list_reviewers(db)}


@router.get("/me/today")
def my_time_today(db: DbSession, actor: ActorDep) -> dict[str, Any]:
    """The caller's active review seconds today (UTC) and the daily cap, for the "time today"
    display. Desk on only."""
    if not settings.reviewer_desk_enabled:
        raise HTTPException(status_code=404, detail="not found")
    me, _ = _reviewer(actor)
    return {
        "active_seconds_today": service.seconds_today(db, me, now_utc()),
        "daily_cap_seconds": settings.reviewer_daily_cap_seconds,
    }


@router.get("/export")
def pay_export(
    db: DbSession,
    actor: ActorDep,
    start: Annotated[date, Query(alias="from")],
    end: Annotated[date, Query(alias="to")],
) -> dict[str, Any]:
    """Admin only, read-only: per reviewer, decisions by type and total active seconds between two
    dates (both included, UTC). Ids and pseudonymous labels only; no email, no learner data."""
    _desk_admin(actor)
    if end < start:
        raise HTTPException(status_code=422, detail="`to` is before `from`")
    return {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "reviewers": service.reviewer_export(db, start, end),
    }


def _template_admin(actor: Actor) -> None:
    """Admin only, desk and template approval both on; otherwise like an unknown route."""
    if not templates.template_mode():
        raise HTTPException(status_code=404, detail="not found")
    _desk_admin(actor)


@router.get("/templates/summary")
def templates_summary(db: DbSession, actor: ActorDep) -> dict[str, Any]:
    """Admin only, read-only (template approval on): question types (templates) by state, in total
    and per chapter, and the blocked or escalated ones with their ids. States: in_review, ready
    (enough reviewers approved all its samples, nothing blocking), blocked, escalated (a fix or
    reject stands on a sample and its other questions go to reviewers one by one). No reviewer
    identities. Records only: nothing a learner is served depends on it."""
    _template_admin(actor)
    data = service.load_review_data(content_root())
    return templates.summary(templates.analyse(db, data), data)


@router.get("/templates/{template_id}")
def template_detail(template_id: str, db: DbSession, actor: ActorDep) -> dict[str, Any]:
    """Admin only (template approval on): every version of one template with its sample questions
    and each reviewer's progress, by pseudonymous label only."""
    _template_admin(actor)
    data = service.load_review_data(content_root())
    found = templates.detail(templates.analyse(db, data), template_id)
    if not found:
        raise HTTPException(status_code=404, detail="template not found")
    return {"versions": found}


_CSV_COLUMNS = (
    "label",
    "reviewer_id",
    "email",
    "paid_decisions",
    "approve",
    "fix",
    "reject",
    "active_seconds",
    "changed_after_seeing",
    "rate_inr",
    "amount_before_cap_inr",
    "amount_inr",
    "cap_applied",
)


@router.get("/pay-statement", response_model=None)
def pay_statement(
    db: DbSession,
    actor: ActorDep,
    start: Annotated[date, Query(alias="from")],
    end: Annotated[date, Query(alias="to")],
    rate: Annotated[Decimal | None, Query(ge=0, le=100000, decimal_places=2)] = None,
    format: Literal["json", "csv"] = "json",
) -> Any:
    """Admin only, read-only: what to pay each reviewer for decisions from `from` to `to` (both
    included, UTC). Paid decisions = each reviewer's standing approve / fix / reject per item and
    content hash, counted once (skip and withdraw are not paid). amount = paid x rate, where rate is
    `REVIEW_RATE_PER_DECISION_INR` unless `rate` overrides it for this request (teachers and
    students can be paid differently). The monthly cap `REVIEW_MONTHLY_CAP_INR` applies to the
    calendar month of `to`. No quality multiplier yet (planted checks are not built). Holds the
    reviewer's email and pseudonymous label so the owner can pay by hand; it stores and returns no
    payment or UPI details. `format=csv` returns the same rows as a CSV file."""
    _desk_admin(actor)
    if end < start:
        raise HTTPException(status_code=422, detail="`to` is before `from`")
    statement = service.pay_statement(
        db,
        start,
        end,
        rate=rate if rate is not None else Decimal(settings.review_rate_per_decision_inr),
        monthly_cap=Decimal(settings.review_monthly_cap_inr),
    )
    if format == "json":
        return statement
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(_CSV_COLUMNS)
    for r in statement["reviewers"]:
        writer.writerow(
            [
                r["label"],
                r["reviewer_id"],
                r["email"] or "",
                r["paid_decisions"],
                r["decisions"]["approve"],
                r["decisions"]["fix"],
                r["decisions"]["reject"],
                r["active_seconds"],
                r["changed_after_seeing"],
                r["rate_inr"],
                r["amount_before_cap_inr"],
                r["amount_inr"],
                r["cap_applied"],
            ]
        )
    name = f"pay-statement-{start.isoformat()}-{end.isoformat()}.csv"
    return Response(
        out.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )
