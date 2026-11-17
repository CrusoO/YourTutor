"""Property tests for the pure consent state machine and the audit hash chain."""

from __future__ import annotations

import copy
from dataclasses import replace

from hypothesis import given, settings
from hypothesis import strategies as st

from app.auth import consent_state as cs

HASHES = ["a" * 64, "b" * 64, "c" * 64, "d" * 64]  # the pool; some are never approved
SCOPES = ["tutoring", "learning_profile", "math_check"]

approved_sets = st.frozensets(st.sampled_from(HASHES))
events = st.one_of(
    st.builds(cs.Grant, st.one_of(st.none(), st.sampled_from([*HASHES, "f" * 64]))),
    st.builds(cs.Withdraw),
    st.builds(cs.TextChanged, approved_sets),
    st.builds(cs.FlagOff),
    st.builds(cs.FlagOn),
    st.builds(cs.Expire),
    st.builds(cs.Verify),
)
sequences = st.lists(events, max_size=25)
states = st.builds(
    cs.ScopeState,
    scope=st.sampled_from(SCOPES),
    guest=st.booleans(),
    needs_text=st.booleans(),
    require_verified=st.booleans(),
    approved=approved_sets,
    flag_on=st.booleans(),
)

PROP = settings(max_examples=200, deadline=None)


@PROP
@given(states, sequences)
def test_in_force_only_after_a_grant_that_nothing_ended(
    start: cs.ScopeState, seq: list[cs.Event]
) -> None:
    """Property 1: in force means the last accepted grant is later than any withdraw, expire or
    flag-off, its hash is approved, and the flag is on."""
    state = start
    granted = False
    for event in seq:
        step = cs.apply(state, event)
        if isinstance(event, cs.Grant) and step.accepted:
            granted = True
        if isinstance(event, (cs.Withdraw, cs.Expire, cs.FlagOff)):
            granted = False
        state = step.state
        if cs.in_force(state):
            assert granted
            assert state.flag_on
            if state.needs_text:
                assert state.text_sha256 in state.approved


@PROP
@given(states, st.sampled_from(HASHES))
def test_withdraw_is_idempotent_and_a_regrant_needs_a_fresh_approved_hash(
    start: cs.ScopeState, sha: str
) -> None:
    """Property 2."""
    once = cs.apply(start, cs.Withdraw())
    twice = cs.apply(once.state, cs.Withdraw())
    assert twice.state == once.state and twice.obligations == ()
    ready = cs.ScopeState(
        scope="learning_profile",
        flag_on=True,
        approved=frozenset({HASHES[0]}),
        status=cs.WITHDRAWN,
    )
    unapproved = sha if sha != HASHES[0] else HASHES[1]
    refused = cs.apply(ready, cs.Grant(unapproved))
    assert not refused.accepted and not cs.in_force(refused.state)
    assert cs.in_force(cs.apply(ready, cs.Grant(HASHES[0])).state)


@PROP
@given(states, sequences)
def test_a_guest_never_reaches_a_non_tutoring_scope(
    start: cs.ScopeState, seq: list[cs.Event]
) -> None:
    """Property 3."""
    state = replace(start, guest=True)
    for event in seq:
        state = cs.apply(state, event).state
        if state.scope != "tutoring":
            assert not cs.in_force(state)
            assert state.status in (cs.NONE, cs.WITHDRAWN)


@PROP
@given(states, sequences)
def test_never_active_with_an_unknown_or_unapproved_hash(
    start: cs.ScopeState, seq: list[cs.Event]
) -> None:
    """Property 4."""
    state = start
    ever_approved = set(start.approved)
    for event in seq:
        if isinstance(event, cs.TextChanged):
            ever_approved |= event.approved
        state = cs.apply(state, event).state
        if state.needs_text and state.status == cs.ACTIVE:
            assert state.text_sha256 in ever_approved
            assert state.text_sha256 in state.approved


def _chain(seq: list[dict[str, str | None]]) -> list[dict[str, str | None]]:
    rows: list[dict[str, str | None]] = []
    prev = cs.GENESIS
    for i, fields in enumerate(seq):
        row = {**fields, "id": f"id{i}", "prev_hash": prev}
        row["row_hash"] = cs.row_hash(prev, row)
        rows.append(row)
        prev = str(row["row_hash"])
    return rows


event_fields = st.fixed_dictionaries(
    {
        "at": st.just("2026-11-17T10:00:00+00:00"),
        "student_id": st.uuids().map(str),
        "guardian_user_id": st.one_of(st.none(), st.uuids().map(str)),
        "scope": st.sampled_from(SCOPES),
        "action": st.sampled_from(["granted", "withdrawn", "expired"]),
        "text_sha256": st.one_of(st.none(), st.sampled_from(HASHES)),
        "method": st.one_of(st.none(), st.just("declared_otp")),
        "actor_kind": st.sampled_from(["guardian", "system", "admin"]),
    }
)


@PROP
@given(st.lists(event_fields, min_size=1, max_size=12), st.data())
def test_the_chain_verifies_and_any_edit_breaks_it(
    fields: list[dict[str, str | None]], data: st.DataObject
) -> None:
    """Property 5."""
    rows = _chain(fields)
    assert cs.verify_chain(rows)
    assert cs.verify_chain([])
    index = data.draw(st.integers(0, len(rows) - 1))
    key = data.draw(st.sampled_from(sorted(cs.HASHED_FIELDS)))
    edited = copy.deepcopy(rows)
    edited[index][key] = "tampered" if edited[index][key] != "tampered" else "other"
    assert not cs.verify_chain(edited)
    if len(rows) > 1:
        assert not cs.verify_chain(rows[1:])  # dropping the first row


@PROP
@given(states, sequences)
def test_flag_off_means_not_in_force_and_deletion_is_owed(
    start: cs.ScopeState, seq: list[cs.Event]
) -> None:
    """Property 6."""
    state, _ = cs.run(start, seq)
    step = cs.apply(state, cs.FlagOff())
    assert not cs.in_force(step.state) and not step.state.flag_on
    owed = state.status in (cs.ACTIVE, cs.STALE)
    assert step.obligations == ((f"delete_data:{state.scope}",) if owed else ())
