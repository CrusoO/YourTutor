"""The reviewer desk (REVIEWER_DESK_ENABLED): rules, blind cards, history, reviewer role, export."""

# ruff: noqa: F811
from __future__ import annotations

import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import now_utc
from app.config import settings
from app.content_review import service
from app.db.models import ContentReviewRow, UserRow
from tests.conftest import World, auth_header, seed_user, signup
from tests.content.conftest import content_root, loc, minimal_item, write_yaml  # noqa: F401
from tests.content_review.test_review_api import (  # noqa: F401
    LIST,
    _decision,
    _hash,
    _second_teacher,
    root,
)

YES = [True] * 5
LONG = "The wrong option is not believable"


@pytest.fixture
def desk() -> None:
    settings.reviewer_desk_enabled = True


def _approve(digest: str, **more: Any) -> dict[str, Any]:
    return {"content_hash": digest, "decision": "approve", "checks": YES, **more}


def _fix(digest: str, **more: Any) -> dict[str, Any]:
    body = {
        "content_hash": digest,
        "decision": "fix",
        "severity": "must_fix",
        "reason_code": "6",
        "checks": [True, True, True, False, True],
        "fix_notes": [{"question_index": 3, "text": LONG}],
    }
    body.update(more)
    return body


def _post(client: TestClient, token: str, body: dict[str, Any], item: str = "ITEM.Q1") -> Any:
    return client.post(_decision(item), json=body, headers=auth_header(token))


def _errors(response: Any) -> dict[str, str]:
    assert response.status_code == 422, response.text
    return {e["field"]: e["message"] for e in response.json()["detail"]["errors"]}


# ---- rules (pure) ----------------------------------------------------------------------------


def _rules(decision: str, **kw: Any) -> list[str]:
    args: dict[str, Any] = {
        "decision": decision,
        "severity": None,
        "reason_code": None,
        "checks": None,
        "fix_notes": [],
        "note": None,
    }
    args.update(kw)
    return [e.field for e in service.check_desk_decision(**args)]


def test_rules_for_approve() -> None:
    assert _rules("approve", checks=YES) == []
    assert _rules("approve", checks=None) == ["checks"]
    assert _rules("approve", checks=[True, True, None, True, True]) == ["checks"]
    assert _rules("approve", checks=[True, True, True, True, False]) == ["checks"]
    assert "severity" in _rules("approve", checks=YES, severity="blocker")
    assert "reason_code" in _rules("approve", checks=YES, reason_code="1")


def test_rules_for_fix_and_reject() -> None:
    marked = [True, False, True, True, True]
    good = {"severity": "blocker", "reason_code": "4", "checks": marked}
    for decision in ("fix", "reject"):
        assert _rules(decision, **good, fix_notes=[(1, "Use the sine rule here")]) == []
        assert _rules(decision, **good, fix_notes=[(1, "too short")]) == []  # 8 non-space chars
        assert _rules(decision, **good, fix_notes=[(1, "short")]) == ["fix_notes"]
        assert _rules(decision, **good, fix_notes=[(1, "a b c d e f g")]) == ["fix_notes"]  # 7
        assert _rules(decision, **good) == ["fix_notes"]  # a marked question needs its note
        assert _rules(decision, **{**good, "severity": None}, fix_notes=[(1, LONG)]) == ["severity"]
        no_reason = {**good, "reason_code": None}
        assert _rules(decision, **no_reason, fix_notes=[(1, LONG)]) == ["reason_code"]
        # nothing marked: the general note carries it
        plain = {"severity": "must_fix", "reason_code": "0", "checks": YES}
        assert _rules(decision, **plain, note=LONG) == []
        assert _rules(decision, **plain, note="short") == ["note"]
        assert _rules(decision, **plain) == ["note"]
        # a note for a question that is not marked is refused
        assert _rules(decision, **plain, note=LONG, fix_notes=[(2, LONG)]) == ["fix_notes"]


def test_rules_for_skip() -> None:
    assert _rules("skip") == []
    assert _rules("skip", checks=[True, False, None, None, None]) == ["fix_notes"]  # unfinished
    assert _rules("skip", checks=[True, False, None, None, None], fix_notes=[(1, LONG)]) == []
    assert "severity" in _rules("skip", severity="blocker")


# ---- the endpoint with the desk on ----


def test_server_refuses_incomplete_decisions_with_clear_errors(
    client: TestClient, world: World, root: Path, desk: None
) -> None:
    digest = _hash(client, world.teacher_token, "ITEM.Q1")
    token = world.teacher_token
    assert "checks" in _errors(
        _post(client, token, {"content_hash": digest, "decision": "approve"})
    )
    bare = _errors(_post(client, token, {"content_hash": digest, "decision": "fix", "note": LONG}))
    assert set(bare) == {"severity", "reason_code"}
    no_note = _errors(
        _post(client, token, _fix(digest, fix_notes=[{"question_index": 3, "text": "no"}]))
    )
    assert "question 4" in no_note["fix_notes"]
    assert _post(client, token, _fix(digest, active_seconds=7201)).status_code == 422
    assert _post(client, token, _fix(digest, active_seconds=-1)).status_code == 422
    assert _post(client, token, _fix(digest, checks=[True, False])).status_code == 422
    assert _post(client, token, _fix(digest, severity="huge")).status_code == 422
    assert _post(client, token, _fix(digest, reason_code="10")).status_code == 422
    stale = _post(client, token, _approve("0" * 64))
    assert stale.status_code == 409  # still tied to the current content hash


def test_a_full_decision_is_stored_with_every_field(
    client: TestClient, world: World, root: Path, desk: None, db: Session
) -> None:
    digest = _hash(client, world.teacher_token, "ITEM.Q1")
    out = _post(client, world.teacher_token, _fix(digest, active_seconds=95, note="  general  "))
    assert out.status_code == 200, out.text
    row = db.scalars(select(ContentReviewRow)).one()
    assert (row.decision, row.severity, row.reason_code) == ("fix", "must_fix", "6")
    assert row.checks == [True, True, True, False, True]
    assert row.fix_notes == [{"question_index": 3, "text": LONG}]
    assert row.active_seconds == 95 and row.note == "general"
    mine = out.json()["my_decision"]
    assert mine["severity"] == "must_fix" and mine["reason_code"] == "6"


def test_skip_is_recorded_but_is_not_a_decision(
    client: TestClient, world: World, root: Path, desk: None, db: Session
) -> None:
    digest = _hash(client, world.teacher_token, "ITEM.Q1")
    skipped = _post(client, world.teacher_token, {"content_hash": digest, "decision": "skip"})
    assert skipped.status_code == 200
    assert skipped.json()["my_decision"] is None and skipped.json()["approvals"] is None
    assert db.scalars(select(ContentReviewRow)).one().decision == "skip"


# ---- blind review ----


def _card(client: TestClient, token: str) -> dict[str, Any]:
    cards = client.get(f"{LIST}?status=all&limit=50", headers=auth_header(token)).json()["items"]
    return next(c for c in cards if c["id"] == "ITEM.Q1")


def test_a_card_is_blind_until_the_reviewer_has_decided(
    client: TestClient, world: World, sender: Any, db: Session, root: Path, desk: None
) -> None:
    digest = _hash(client, world.teacher_token, "ITEM.Q1")
    second = _second_teacher(client, sender, db)
    reject = _fix(digest, decision="reject", severity="blocker", note="Option B is no trap here")
    assert _post(client, world.teacher_token, reject).status_code == 200

    before = _card(client, second)
    assert before["approvals"] is None and before["blocked"] is None
    assert before["notes"] == [] and before["others"] == [] and before["my_decision"] is None
    text = str(before)
    assert "teacher@example.com" not in text and "Option B" not in text and LONG not in text

    # a "skip" does not lift the blindfold
    _post(client, second, {"content_hash": digest, "decision": "skip"})
    assert _card(client, second)["others"] == []

    after = _post(client, second, _approve(digest)).json()
    assert after["approvals"] == 1 and after["blocked"] is True
    assert [o["reviewer"] for o in after["others"]] == ["Reviewer 1"]
    assert after["others"][0]["decision"] == "reject"
    assert after["others"][0]["severity"] == "blocker"
    assert after["notes"] == [
        {"reviewer": "Reviewer 1", "decision": "reject", "note": "Option B is no trap here"}
    ]
    assert "example.com" not in str(after) and "teacher" not in str(after["others"])


def test_pseudonyms_are_stable_and_the_list_filter_does_not_leak(
    client: TestClient, world: World, sender: Any, db: Session, root: Path, desk: None
) -> None:
    digest = _hash(client, world.teacher_token, "ITEM.Q1")
    second = _second_teacher(client, sender, db)
    _post(client, world.teacher_token, _approve(digest))
    _post(client, second, _approve(digest))
    # two approvals exist, yet a third reviewer who has not decided still sees it as pending
    pending = client.get(LIST, headers=auth_header(world.admin_token)).json()["items"]
    assert "ITEM.Q1" in {c["id"] for c in pending}
    for status in ("ready", "flagged"):
        listed = client.get(f"{LIST}?status={status}", headers=auth_header(world.admin_token))
        assert "ITEM.Q1" not in {c["id"] for c in listed.json()["items"]}
    third = _post(client, world.admin_token, _approve(digest)).json()
    assert [o["reviewer"] for o in third["others"]] == ["Reviewer 1", "Reviewer 2"]
    first_view = _card(client, world.teacher_token)
    assert [o["reviewer"] for o in first_view["others"]] == ["Reviewer 1", "Reviewer 2"]
    ready = client.get(f"{LIST}?status=ready", headers=auth_header(world.admin_token)).json()
    assert [c["id"] for c in ready["items"]] == ["ITEM.Q1"]


def test_with_the_desk_off_the_old_card_and_rules_are_unchanged(
    client: TestClient, world: World, sender: Any, db: Session, root: Path
) -> None:
    assert settings.reviewer_desk_enabled is False
    digest = _hash(client, world.teacher_token, "ITEM.Q1")
    second = _second_teacher(client, sender, db)
    note = "Option B is not a trap"
    old = {"content_hash": digest, "decision": "reject", "note": note}
    assert _post(client, world.teacher_token, old).status_code == 200
    seen = _card(client, second)  # not blind: other notes and emails show, as they always did
    assert seen["blocked"] is True and seen["approvals"] == 1 - 1
    assert seen["notes"] == [
        {"reviewer": "teacher@example.com", "decision": "reject", "note": note}
    ]
    assert "others" not in seen and "my_history" not in seen
    assert set(seen) >= {"approvals", "approvals_needed", "blocked", "notes", "my_decision"}
    # a note-only decision is enough, and desk-only input is refused
    assert _post(client, second, {"content_hash": digest, "decision": "approve"}).status_code == 200
    assert _post(client, second, {"content_hash": digest, "decision": "skip"}).status_code == 422
    assert _post(client, second, _approve(digest)).status_code == 422
    # replacement in place: still one row per reviewer
    assert len(db.scalars(select(ContentReviewRow)).all()) == 2
    for path in ("/staff/review/export?from=2026-01-01&to=2026-12-31", "/staff/review/reviewers"):
        method = client.get if "export" in path else client.post
        kwargs = {} if "export" in path else {"json": {"email": "r@example.com"}}
        assert method(path, headers=auth_header(world.admin_token), **kwargs).status_code == 404


# ---- append-only history ----


def test_every_decision_is_a_new_row_and_the_latest_stands(
    client: TestClient, world: World, root: Path, desk: None, db: Session
) -> None:
    digest = _hash(client, world.teacher_token, "ITEM.Q1")
    token = world.teacher_token
    assert _post(client, token, _fix(digest)).json()["blocked"] is True
    out = _post(client, token, _approve(digest)).json()
    assert out["blocked"] is False and out["approvals"] == 1
    assert out["my_decision"]["decision"] == "approve"
    assert [h["decision"] for h in out["my_history"]] == ["fix", "approve"]
    rows = db.scalars(select(ContentReviewRow).order_by(ContentReviewRow.created_at)).all()
    assert [r.decision for r in rows] == ["fix", "approve"]
    assert rows[0].fix_notes and rows[0].severity == "must_fix"  # the earlier row is untouched
    # a later skip does not withdraw the standing approval
    _post(client, token, {"content_hash": digest, "decision": "skip"})
    assert _card(client, token)["approvals"] == 1


def test_editing_the_item_voids_earlier_decisions(
    client: TestClient, world: World, root: Path, desk: None
) -> None:
    digest = _hash(client, world.teacher_token, "ITEM.Q1")
    _post(client, world.teacher_token, _approve(digest))
    path = root / "items" / "q1.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("x = 5", "x = 5 exactly"), "utf-8")
    new = _card(client, world.teacher_token)
    assert new["content_hash"] != digest and new["my_decision"] is None
    assert _post(client, world.teacher_token, _approve(digest)).status_code == 409


def test_apply_reviews_names_only_standing_approvers(db: Session) -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    t0 = now_utc()
    for who, label, decision, minutes in (
        (a, "a@x", "fix", 0),
        (a, "a@x", "approve", 1),
        (b, "b@x", "approve", 2),
    ):
        db.add(
            ContentReviewRow(
                id=uuid.uuid4(),
                item_id="I",
                content_hash="h",
                reviewer_id=who,
                reviewer_label=label,
                decision=decision,
                created_at=t0 + timedelta(minutes=minutes),
            )
        )
    db.flush()
    rows = service.reviews_for(db, "I", "h")
    assert service.tally(rows).ready is True
    assert sorted(r.reviewer_label for r in service.standing(rows).values()) == ["a@x", "b@x"]


# ---- reviewer role and suspension ----


def _invite(client: TestClient, world: World, sender: Any, email: str) -> tuple[str, str]:
    made = client.post(
        "/staff/review/reviewers", json={"email": email}, headers=auth_header(world.admin_token)
    )
    assert made.status_code == 200, made.text
    return made.json()["id"], signup(client, sender, email)


def test_an_invited_reviewer_can_review_but_not_see_anything_else(
    client: TestClient, world: World, sender: Any, root: Path, desk: None
) -> None:
    rid, token = _invite(client, world, sender, "outside@example.com")
    assert client.get("/auth/me", headers=auth_header(token)).json()["role"] == "reviewer"
    digest = _hash(client, token, "ITEM.Q1")
    assert _post(client, token, _approve(digest)).status_code == 200
    head = auth_header(token)
    for method, path in (
        ("GET", f"/teacher/classes/{world.class_id}/heatmap"),
        ("GET", "/teacher/classes"),
        ("GET", "/teacher/review-queue"),
        ("GET", f"/students/{world.student_share_id}/progress"),
        ("GET", f"/parents/{world.parent_id}/export"),
        ("GET", "/parents/me/export"),
        ("GET", "/analytics/export"),
        ("POST", "/sessions"),
        ("POST", "/students"),
        ("POST", "/classes"),
    ):
        assert client.request(method, path, headers=head, json={}).status_code == 403, path
    made = client.post(
        "/students",
        json={"display_name": "X", "grade": 9, "board": "bhutan", "parent_id": world.parent_id},
        headers=head,
    )
    assert made.status_code == 403
    # a reviewer cannot invite or export
    assert (
        client.post("/staff/review/reviewers", json={"email": "a@b.co"}, headers=head).status_code
        == 403
    )
    assert (
        client.get("/staff/review/export?from=2026-01-01&to=2026-01-02", headers=head).status_code
        == 403
    )
    assert rid


def test_reviewers_are_invite_only(
    client: TestClient, world: World, sender: Any, db: Session, desk: None
) -> None:
    # public sign-up makes a parent, never a reviewer
    token = signup(client, sender, "stranger@example.com")
    assert client.get("/auth/me", headers=auth_header(token)).json()["role"] == "parent"
    assert client.get(LIST, headers=auth_header(token)).status_code == 403
    for who in (world.teacher_token, world.parent_token, world.student_token):
        bad = client.post(
            "/staff/review/reviewers", json={"email": "z@example.com"}, headers=auth_header(who)
        )
        assert bad.status_code == 403
    assert (
        client.post("/staff/review/reviewers", json={"email": "z@example.com"}).status_code == 401
    )
    # an existing account is never converted
    again = client.post(
        "/staff/review/reviewers",
        json={"email": "teacher@example.com"},
        headers=auth_header(world.admin_token),
    )
    assert again.status_code == 409
    assert (
        db.scalar(select(UserRow).where(UserRow.email == "teacher@example.com")).role == "teacher"
    )


def test_the_role_does_nothing_with_the_desk_off(
    client: TestClient, world: World, sender: Any, db: Session, root: Path
) -> None:
    user = seed_user(db, "reviewer", "r@example.com")
    token = signup(client, sender, user.email)
    assert client.get(LIST, headers=auth_header(token)).status_code == 403


def test_suspending_blocks_a_reviewer_at_once_and_reinstating_restores(
    client: TestClient, world: World, sender: Any, db: Session, root: Path, desk: None
) -> None:
    rid, token = _invite(client, world, sender, "outside@example.com")
    assert client.get(LIST, headers=auth_header(token)).status_code == 200
    out = client.post(
        f"/staff/review/reviewers/{rid}/suspend", headers=auth_header(world.admin_token)
    )
    assert out.status_code == 200 and out.json()["suspended"] is True
    for path in (LIST, "/auth/me"):  # the same token, no new sign-in needed to be refused
        assert client.get(path, headers=auth_header(token)).status_code == 403
    again = signup(client, sender, "outside@example.com")  # a fresh sign-in is refused too
    assert client.get(LIST, headers=auth_header(again)).status_code == 403
    for who in (world.teacher_token, token):
        denied = client.post(f"/staff/review/reviewers/{rid}/reinstate", headers=auth_header(who))
        assert denied.status_code == 403
    back = client.post(
        f"/staff/review/reviewers/{rid}/reinstate", headers=auth_header(world.admin_token)
    )
    assert back.json()["suspended"] is False
    assert client.get(LIST, headers=auth_header(token)).status_code == 200
    # only reviewers can be suspended this way
    teacher = db.scalar(select(UserRow).where(UserRow.email == "teacher@example.com"))
    missing = client.post(
        f"/staff/review/reviewers/{teacher.id}/suspend", headers=auth_header(world.admin_token)
    )
    assert missing.status_code == 404


def test_teachers_and_admins_still_review_under_the_allowlist(
    client: TestClient, world: World, root: Path, desk: None
) -> None:
    settings.reviewer_allowlist = "teacher"
    assert client.get(LIST, headers=auth_header(world.teacher_token)).status_code == 200
    assert client.get(LIST, headers=auth_header(world.admin_token)).status_code == 403


# ---- pay export ----


def test_the_export_counts_decisions_and_seconds_without_identities(
    client: TestClient, world: World, sender: Any, db: Session, root: Path, desk: None
) -> None:
    digest = _hash(client, world.teacher_token, "ITEM.Q1")
    _post(client, world.teacher_token, _fix(digest, active_seconds=100))
    _post(client, world.teacher_token, _approve(digest, active_seconds=50))
    _post(
        client,
        world.teacher_token,
        {"content_hash": digest, "decision": "skip", "active_seconds": 5},
    )
    _, outside = _invite(client, world, sender, "outside@example.com")
    _post(client, outside, _approve(digest, active_seconds=30))
    today = date.today()
    url = f"/staff/review/export?from={today - timedelta(days=1)}&to={today + timedelta(days=1)}"
    out = client.get(url, headers=auth_header(world.admin_token))
    assert out.status_code == 200, out.text
    people = {r["label"]: r for r in out.json()["reviewers"]}
    assert len(people) == 2
    totals = sorted(
        (
            r["decisions"]["approve"],
            r["decisions"]["fix"],
            r["decisions"]["skip"],
            r["active_seconds"],
        )
        for r in people.values()
    )
    assert totals == [(1, 0, 0, 30), (1, 1, 1, 155)]
    text = out.text
    assert "example.com" not in text and "@" not in text
    assert all(label.startswith("R-") for label in people)
    # outside the range nothing is counted; bad ranges are refused; non-admins are refused
    old = client.get(
        "/staff/review/export?from=2020-01-01&to=2020-01-31", headers=auth_header(world.admin_token)
    )
    assert old.json()["reviewers"] == []
    reversed_ = client.get(
        "/staff/review/export?from=2026-02-01&to=2026-01-01", headers=auth_header(world.admin_token)
    )
    assert reversed_.status_code == 422
    assert client.get(url, headers=auth_header(world.teacher_token)).status_code == 403
    assert client.get(url).status_code == 401
    assert service.reviewer_export(db, today, today)[0]["reviewer_id"]
