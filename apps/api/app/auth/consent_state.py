"""Pure consent state machine and audit hash chain: no database, no clock, no I/O.

One `ScopeState` per (student, scope). Statuses:
    none       never granted
    active     granted, and (while the flag is on and the text hash is approved) in force
    withdrawn  the guardian withdrew, or the consent expired
    stale      the approved wording moved on, or the scope was switched off: ask again

Rules, all covered by property tests:
  1. A scope is in force only if its last grant came after its last withdraw, its text hash is
     approved, and its flag is on.
  2. Withdraw is idempotent; a grant after a withdraw needs a fresh, approved hash.
  3. A guest never reaches a non-tutoring scope.
  4. No sequence makes a scope active with an unknown or unapproved text hash.
  5. The audit chain verifies after any sequence; editing a prior event breaks `verify_chain`.
  6. Flag off means not in force, and a deletion obligation is emitted.

The wording the hashes point at is a draft until the owner approves it. Nothing here is legal
advice.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace

NONE = "none"
ACTIVE = "active"
WITHDRAWN = "withdrawn"
STALE = "stale"

GENESIS = "0" * 64
HASHED_FIELDS = (
    "id",
    "at",
    "student_id",
    "guardian_user_id",
    "scope",
    "action",
    "text_sha256",
    "method",
    "actor_kind",
)


@dataclass(frozen=True)
class ScopeState:
    scope: str
    guest: bool = False
    needs_text: bool = True  # False for scopes with no versioned text (for example tutoring)
    require_verified: bool = False  # True once guardian verification exists (a later PR)
    status: str = NONE
    text_sha256: str | None = None
    approved: frozenset[str] = field(default_factory=frozenset)
    flag_on: bool = False
    verified: bool = False


@dataclass(frozen=True)
class Grant:
    text_sha256: str | None = None


@dataclass(frozen=True)
class Withdraw:
    pass


@dataclass(frozen=True)
class TextChanged:
    approved: frozenset[str]


@dataclass(frozen=True)
class FlagOff:
    pass


@dataclass(frozen=True)
class FlagOn:
    pass


@dataclass(frozen=True)
class Expire:
    pass


@dataclass(frozen=True)
class Verify:
    pass


Event = Grant | Withdraw | TextChanged | FlagOff | FlagOn | Expire | Verify


@dataclass(frozen=True)
class Transition:
    state: ScopeState
    accepted: bool = True
    obligations: tuple[str, ...] = ()  # for example ("delete_data:learning_profile",)


def in_force(state: ScopeState) -> bool:
    """Whether the scope may be used right now."""
    if state.status != ACTIVE or not state.flag_on:
        return False
    if state.needs_text:
        return state.text_sha256 is not None and state.text_sha256 in state.approved
    return True


def _delete(state: ScopeState) -> tuple[str, ...]:
    return (f"delete_data:{state.scope}",) if state.status in (ACTIVE, STALE) else ()


def apply(state: ScopeState, event: Event) -> Transition:
    """The next state and any deletion obligation. A refused event leaves the state unchanged."""
    if isinstance(event, Grant):
        refused = Transition(state, accepted=False)
        if state.guest and state.scope != "tutoring":
            return refused
        if not state.flag_on:
            return refused
        if state.require_verified and not state.verified:
            return refused
        unapproved = event.text_sha256 is None or event.text_sha256 not in state.approved
        if state.needs_text and unapproved:
            return refused
        sha = event.text_sha256 if state.needs_text else None
        return Transition(replace(state, status=ACTIVE, text_sha256=sha))
    if isinstance(event, (Withdraw, Expire)):
        if state.status in (NONE, WITHDRAWN):
            return Transition(state)
        return Transition(replace(state, status=WITHDRAWN), obligations=_delete(state))
    if isinstance(event, TextChanged):
        moved = replace(state, approved=event.approved)
        if state.status == ACTIVE and state.needs_text and state.text_sha256 not in event.approved:
            return Transition(replace(moved, status=STALE))
        return Transition(moved)
    if isinstance(event, FlagOff):
        status = STALE if state.status == ACTIVE else state.status
        return Transition(replace(state, flag_on=False, status=status), obligations=_delete(state))
    if isinstance(event, FlagOn):
        return Transition(replace(state, flag_on=True))
    return Transition(replace(state, verified=True))  # Verify


def run(state: ScopeState, events: Sequence[Event]) -> tuple[ScopeState, tuple[str, ...]]:
    """Apply events in order; return the final state and every obligation emitted on the way."""
    obligations: list[str] = []
    for event in events:
        step = apply(state, event)
        state = step.state
        obligations.extend(step.obligations)
    return state, tuple(obligations)


def row_hash(prev_hash: str, fields: Mapping[str, str | None]) -> str:
    """Hash of one audit row, chained to the one before it. Fields are plain strings or None."""
    body = {k: fields.get(k) for k in HASHED_FIELDS}
    raw = json.dumps({"prev": prev_hash, "row": body}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def verify_chain(events: Sequence[Mapping[str, str | None]]) -> bool:
    """True when each row points at the one before and its own hash matches its fields.

    Rows are in chain order; the first row's prev_hash is GENESIS.
    """
    prev = GENESIS
    for event in events:
        if event.get("prev_hash") != prev:
            return False
        if event.get("row_hash") != row_hash(prev, event):
            return False
        prev = str(event["row_hash"])
    return True
