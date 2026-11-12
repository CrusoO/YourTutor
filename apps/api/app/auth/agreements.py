"""Role agreements: one list of tick boxes per role, shown once at sign-up (DPDP: specific,
unbundled, as easy to withdraw as to give).

The wording lives in the web app (apps/web/lib/agreement-copy.ts); this module owns what can be
agreed, which items the service cannot run without ("required") and which are the person's
choice ("optional"), and what each item switches on. An item that is a consent scope (see
scopes.py) becomes part of each learner's consent record, so the rest of the code keeps reading
`active_scopes`. A change adds a new AgreementRow and closes the old one; withdrawing is one call.

Roles: guardian (also covers each child), adult (a learner agreeing for themself), teacher, and
child (an acknowledgement in limited mode: a child cannot consent, so it is shown, checked and
never stored).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.actor import Actor
from app.auth.consent import active_consent, available_scopes
from app.auth.security import now_utc
from app.config import settings
from app.db.models import AgreementRow, StudentRow

VERSION = "agreement-v1"  # bump when the items or their meaning change: everyone is asked again
STORED_ROLES = ("guardian", "adult", "teacher")


@dataclass(frozen=True)
class Item:
    id: str
    required: bool
    scope: str | None = None  # the consent scope this item grants, if it is one

    def public(self) -> dict[str, object]:
        return {"id": self.id, "required": self.required, "scope": self.scope}


_LEARNER_ITEMS = (
    Item("tutoring", True, "tutoring"),
    Item("ai_processing", True, "ai_processing"),
    Item("teacher_share", False, "teacher_share"),
    Item("free_text", False, "free_text"),
    Item("uploads", False, "uploads"),
    Item("research_pseudonymised", False, "research_pseudonymised"),
    Item("progress_reports", False),
)

CATALOG: dict[str, tuple[Item, ...]] = {
    "guardian": (Item("confirm_guardian", True), *_LEARNER_ITEMS),
    "adult": (Item("confirm_adult", True), *_LEARNER_ITEMS),
    "teacher": (
        Item("terms_counts_only", True),
        Item("terms_no_sharing_codes", True),
        Item("terms_no_exporting_names", True),
    ),
    "child": (Item("ack_limited_mode", True), Item("ack_guardian_contact", True)),
}


def catalog(role: str) -> dict[str, object]:
    if role not in CATALOG:
        raise HTTPException(status_code=404, detail="unknown role")
    return {"role": role, "version": VERSION, "items": [i.public() for i in CATALOG[role]]}


def items_error(role: str, accepted: list[str]) -> str | None:
    """Why this selection cannot be accepted, or None. Pure: the server runs it on every accept."""
    items = CATALOG.get(role)
    if items is None:
        return "unknown role"
    known = {i.id for i in items}
    unknown = set(accepted) - known
    if unknown:
        return f"unknown items: {sorted(unknown)}"
    missing = [i.id for i in items if i.required and i.id not in accepted]
    if missing:
        return f"required items not ticked: {missing}"
    return None


def scopes_of(role: str, accepted: list[str]) -> list[str]:
    return [i.scope for i in CATALOG[role] if i.scope and i.id in accepted]


def required_present(role: str, accepted: list[str]) -> bool:
    return all(i.id in accepted for i in CATALOG[role] if i.required)


def active_agreement(session: Session, user_id: uuid.UUID, role: str) -> AgreementRow | None:
    return session.scalar(
        select(AgreementRow)
        .where(
            AgreementRow.user_id == user_id,
            AgreementRow.role == role,
            AgreementRow.revoked_at.is_(None),
        )
        .order_by(AgreementRow.granted_at.desc())
    )


def _complete(row: AgreementRow | None) -> bool:
    return (
        row is not None
        and row.version == VERSION
        and required_present(row.role, list(row.items or []))
    )


def _allowed_role(actor: Actor, role: str) -> bool:
    if role == "teacher":
        return actor.is_teacher
    if role in {"guardian", "adult"}:
        return actor.is_parent
    return False


def needed(session: Session, actor: Actor) -> list[str]:
    """The agreement roles this signed-in person still has to complete (empty: nothing to ask).
    A guardian-or-adult account is listed as both choices: either one completes it."""
    if actor.user_id is None:
        return []
    if actor.is_teacher:
        return [] if _complete(active_agreement(session, actor.user_id, "teacher")) else ["teacher"]
    if actor.is_parent:
        for role in ("guardian", "adult"):
            if _complete(active_agreement(session, actor.user_id, role)):
                return []
        return ["guardian", "adult"]
    return []


def my_agreements(session: Session, actor: Actor) -> dict[str, object]:
    rows = []
    if actor.user_id is not None:
        for role in STORED_ROLES:
            row = active_agreement(session, actor.user_id, role)
            if row is not None and _allowed_role(actor, role):
                rows.append(
                    {
                        "role": role,
                        "version": row.version,
                        "items": list(row.items or []),
                        "granted_at": row.granted_at.isoformat(),
                        "complete": _complete(row),
                    }
                )
    return {"version": VERSION, "agreements": rows, "needed": needed(session, actor)}


def _learners(session: Session, user_id: uuid.UUID, role: str) -> list[StudentRow]:
    students = session.scalars(select(StudentRow).where(StudentRow.parent_id == user_id)).all()
    if role == "adult":
        return [s for s in students if s.is_adult is True]
    return [s for s in students if s.is_adult is not True]


def apply_to_learner(
    session: Session, actor: Actor, student: StudentRow, role: str, accepted: list[str]
) -> None:
    """Make the learner's consent record say what the agreement says: grant the ticked scopes, or
    revoke when a required item is not (or no longer) agreed."""
    from app.auth.service import grant_consent, revoke_consent

    allowed = available_scopes(session, student.id)
    scopes = (
        [s for s in scopes_of(role, accepted) if s in allowed]
        if required_present(role, accepted)
        else []
    )
    current = active_consent(session, student.id)
    if not scopes:
        if current is not None:
            revoke_consent(session, actor, student.id)
        return
    if current is not None and set(current.scopes or []) == set(scopes):
        return
    grant_consent(session, actor, student.id, version=VERSION, scopes=scopes)


def store(session: Session, user_id: uuid.UUID, role: str, items: list[str]) -> AgreementRow:
    """Close the person's current agreement for this role and add the new one."""
    now = now_utc()
    previous = active_agreement(session, user_id, role)
    if previous is not None:
        previous.revoked_at = now
    row = AgreementRow(
        id=uuid.uuid4(),
        user_id=user_id,
        role=role,
        version=VERSION,
        items=list(items),
        granted_at=now,
    )
    session.add(row)
    session.flush()
    return row


def accept(
    session: Session, actor: Actor, role: str, items: list[str], version: str
) -> AgreementRow:
    """Record this person's ticks for their role and make their learners' consents match."""
    if role not in STORED_ROLES or not _allowed_role(actor, role) or actor.user_id is None:
        raise HTTPException(status_code=403, detail="forbidden")
    if version != VERSION:
        raise HTTPException(status_code=409, detail="agreement_version_changed")
    error = items_error(role, items)
    if error:
        raise HTTPException(status_code=400, detail=error)
    row = store(session, actor.user_id, role, items)
    for student in _learners(session, actor.user_id, role):
        apply_to_learner(session, actor, student, role, items)
    return row


def withdraw(session: Session, actor: Actor, role: str, item_id: str) -> AgreementRow:
    """Take one item back. It is effective at once; if it is one the service cannot run without,
    every consent under this agreement is closed too (the person can agree again any time)."""
    if role not in STORED_ROLES or not _allowed_role(actor, role) or actor.user_id is None:
        raise HTTPException(status_code=403, detail="forbidden")
    current = active_agreement(session, actor.user_id, role)
    if current is None or item_id not in (current.items or []):
        raise HTTPException(status_code=404, detail="not agreed")
    remaining = [i for i in current.items if i != item_id]
    row = store(session, actor.user_id, role, remaining)
    for student in _learners(session, actor.user_id, role):
        apply_to_learner(session, actor, student, role, remaining)
    return row


def apply_to_new_child(session: Session, actor: Actor, student: StudentRow) -> bool:
    """A guardian who already agreed does not tick again for the next child: the same items
    become that child's consent. Returns whether a consent was recorded."""
    if actor.user_id is None or not actor.is_parent:
        return False
    row = active_agreement(session, actor.user_id, "guardian")
    if row is None or not _complete(row):
        return False
    apply_to_learner(session, actor, student, "guardian", list(row.items))
    return True


def require_teacher_terms(session: Session, actor: Actor) -> None:
    """With ROLE_AGREEMENTS_REQUIRED on, a teacher without the teacher terms gets a 403."""
    if not settings.role_agreements_required or not actor.is_teacher or actor.user_id is None:
        return
    if not _complete(active_agreement(session, actor.user_id, "teacher")):
        raise HTTPException(status_code=403, detail="agreement_required")
