"""Reviewer desk slice 3: the content cache, withdraw (undo), the reviewer list, time today."""

# ruff: noqa: F811
from __future__ import annotations

import threading
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.content.signatures import item_content_hash
from app.content_review import service
from app.db.models import ContentReviewRow
from tests.conftest import World, auth_header, seed_user
from tests.content.conftest import content_root, write_yaml  # noqa: F401
from tests.content_review.test_review_api import _hash, _second_teacher, root  # noqa: F401
from tests.content_review.test_reviewer_desk import (  # noqa: F401
    YES,
    _approve,
    _card,
    _fix,
    _invite,
    _post,
    desk,
)

WITHDRAW = "withdraw"


def _withdraw(digest: str) -> dict[str, Any]:
    return {"content_hash": digest, "decision": WITHDRAW}


def _counting(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    calls: list[int] = []
    real = service.load_bundle

    def counting(path: Path) -> Any:
        calls.append(1)
        return real(path)

    monkeypatch.setattr(service, "load_bundle", counting)
    return calls


# ---- the cache ----


def test_the_second_call_does_not_reload_the_bundle(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _counting(monkeypatch)
    first, _ = service.load_items(root)
    second, _ = service.load_items(root)
    assert len(calls) == 1
    assert [i.id for i in first] == [i.id for i in second]
    assert first is not second  # callers get their own list


def test_changing_a_content_file_invalidates_the_cache_and_the_hash_follows(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _counting(monkeypatch)
    before = {i.id: item_content_hash(i) for i in service.load_items(root)[0]}
    path = root / "items" / "p0.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["stem"]["en"] = data["stem"]["en"] + " (edited, longer)"
    write_yaml(path, data)
    after = {i.id: item_content_hash(i) for i in service.load_items(root)[0]}
    assert len(calls) == 2
    assert after["ITEM.P0"] != before["ITEM.P0"]
    assert after["ITEM.Q1"] == before["ITEM.Q1"]
    service.clear_items_cache()
    service.load_items(root)
    assert len(calls) == 3


def test_concurrent_first_calls_load_once(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _counting(monkeypatch)
    threads = [threading.Thread(target=service.load_items, args=(root,)) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(calls) == 1


def test_a_decision_is_tied_to_the_current_hash_after_an_edit(
    client: TestClient, world: World, root: Path, desk: None
) -> None:
    token = world.teacher_token
    old = _hash(client, token, "ITEM.Q1")
    assert _post(client, token, _approve(old)).status_code == 200
    path = root / "items" / "q1.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["stem"]["en"] = "Does x = 5 solve the equation x + 7 = 12 exactly?"
    write_yaml(path, data)
    assert _post(client, token, _approve(old)).status_code == 409  # the cache did not hide it
    new = _hash(client, token, "ITEM.Q1")
    assert new != old
    assert _post(client, token, _approve(new)).status_code == 200


# ---- withdraw ----


def test_withdraw_removes_the_standing_decision_but_keeps_every_row(
    client: TestClient, world: World, root: Path, desk: None, db: Session
) -> None:
    token = world.teacher_token
    digest = _hash(client, token, "ITEM.Q1")
    _post(client, token, _approve(digest))
    out = _post(client, token, _withdraw(digest))
    assert out.status_code == 200, out.text
    card = out.json()
    assert card["my_decision"] is None and card["approvals"] is None  # blind again
    assert [h["decision"] for h in card["my_history"]] == ["approve", WITHDRAW]
    rows = db.scalars(select(ContentReviewRow).order_by(ContentReviewRow.created_at)).all()
    assert [r.decision for r in rows] == ["approve", WITHDRAW]
    assert rows[1].severity is None and rows[1].checks is None


def test_a_withdrawn_approval_does_not_count_and_a_withdrawn_block_stops_blocking(
    client: TestClient, world: World, sender: Any, db: Session, root: Path, desk: None
) -> None:
    first, second = world.teacher_token, _second_teacher(client, sender, db)
    digest = _hash(client, first, "ITEM.Q1")
    _post(client, first, _approve(digest))
    _post(client, second, _approve(digest))
    assert _card(client, first)["approvals"] == 2
    _post(client, second, _withdraw(digest))
    assert _card(client, first)["approvals"] == 1  # the two-approval rule is unchanged
    assert not service.tally(service.reviews_for(db, "ITEM.Q1", digest)).ready
    _post(client, second, _fix(digest))
    assert _card(client, first)["blocked"] is True
    _post(client, second, _withdraw(digest))
    assert _card(client, first)["blocked"] is False
    assert _card(client, first)["others"] == []


def test_withdraw_needs_a_standing_decision_on_the_current_hash(
    client: TestClient, world: World, root: Path, desk: None
) -> None:
    token = world.teacher_token
    digest = _hash(client, token, "ITEM.Q1")
    assert _post(client, token, _withdraw(digest)).status_code == 409  # nothing to withdraw
    _post(client, token, _approve(digest))
    assert _post(client, token, _withdraw(digest)).status_code == 200
    assert _post(client, token, _withdraw(digest)).status_code == 409  # already withdrawn
    _post(client, token, {"content_hash": digest, "decision": "skip"})
    assert _post(client, token, _withdraw(digest)).status_code == 409  # a skip is no decision
    assert _post(client, token, _withdraw("0" * 64)).status_code == 409  # not the current hash
    assert _post(client, token, _withdraw(digest), item="ITEM.NOPE").status_code == 404


def test_you_cannot_withdraw_someone_elses_decision(
    client: TestClient, world: World, sender: Any, db: Session, root: Path, desk: None
) -> None:
    other = _second_teacher(client, sender, db)
    digest = _hash(client, world.teacher_token, "ITEM.Q1")
    _post(client, other, _approve(digest))
    assert _post(client, world.teacher_token, _withdraw(digest)).status_code == 409
    assert _card(client, other)["my_decision"]["decision"] == "approve"


def test_withdraw_takes_no_severity_or_answers(
    client: TestClient, world: World, root: Path, desk: None
) -> None:
    token = world.teacher_token
    digest = _hash(client, token, "ITEM.Q1")
    _post(client, token, _approve(digest))
    res = _post(client, token, {**_withdraw(digest), "severity": "blocker", "checks": YES})
    assert res.status_code == 422
    assert _post(client, token, {**_withdraw(digest), "active_seconds": 4}).status_code == 200


def test_deciding_again_after_a_withdraw_is_flagged_changed_after_seeing(
    client: TestClient, world: World, sender: Any, db: Session, root: Path, desk: None
) -> None:
    first, second = world.teacher_token, _second_teacher(client, sender, db)
    digest = _hash(client, first, "ITEM.Q1")
    _post(client, first, _approve(digest))
    _post(client, second, _fix(digest))
    _post(client, first, _withdraw(digest))
    out = _post(client, first, _fix(digest)).json()
    history = [(h["decision"], h["changed_after_seeing"]) for h in out["my_history"]]
    assert history == [("approve", False), (WITHDRAW, False), ("fix", True)]
    late = service.changed_after_seeing(service.reviews_for(db, "ITEM.Q1", digest))
    flagged = [r.decision for r in db.scalars(select(ContentReviewRow)) if r.id in late]
    assert flagged == ["fix"]


def test_the_export_counts_withdrawals_and_late_changes(
    client: TestClient, world: World, root: Path, desk: None
) -> None:
    token = world.teacher_token
    digest = _hash(client, token, "ITEM.Q1")
    _post(client, token, _approve(digest))
    _post(client, token, _withdraw(digest))
    _post(client, token, _approve(digest))
    today = date.today()
    url = f"/staff/review/export?from={today - timedelta(days=1)}&to={today + timedelta(days=1)}"
    out = client.get(url, headers=auth_header(world.admin_token)).json()["reviewers"][0]
    assert out["decisions"]["withdraw"] == 1 and out["changed_after_seeing"] == 1


def test_withdraw_is_refused_with_the_desk_off(
    client: TestClient, world: World, root: Path
) -> None:
    digest = _hash(client, world.teacher_token, "ITEM.Q1")
    assert not settings.reviewer_desk_enabled
    assert _post(client, world.teacher_token, _withdraw(digest)).status_code == 422


# ---- reviewer list ----


def test_the_reviewer_list_is_admin_only_and_shows_activity_without_votes(
    client: TestClient, world: World, sender: Any, db: Session, root: Path, desk: None
) -> None:
    quiet_id, _ = _invite(client, world, sender, "quiet@example.com")
    busy_id, busy = _invite(client, world, sender, "busy@example.com")
    digest = _hash(client, busy, "ITEM.Q1")
    _post(client, busy, _approve(digest))
    _post(client, busy, _withdraw(digest))
    head = auth_header(world.admin_token)
    client.post(f"/staff/review/reviewers/{quiet_id}/suspend", headers=head)
    seed_user(db, "teacher", "not-a-reviewer@example.com")
    res = client.get("/staff/review/reviewers", headers=head)
    assert res.status_code == 200, res.text
    people = {r["id"]: r for r in res.json()["reviewers"]}
    assert set(people) == {quiet_id, busy_id}  # teachers and parents are not listed
    assert people[quiet_id]["suspended"] is True and people[quiet_id]["decision_count"] == 0
    assert people[quiet_id]["last_decision_at"] is None
    assert people[busy_id]["decision_count"] == 2 and people[busy_id]["last_decision_at"]
    assert people[busy_id]["email"] == "busy@example.com" and people[busy_id]["invited_at"]
    assert "approve" not in res.text
    for token in (world.teacher_token, busy):
        assert client.get("/staff/review/reviewers", headers=auth_header(token)).status_code == 403
    assert client.get("/staff/review/reviewers").status_code == 401


# ---- time today ----


def test_time_today_sums_my_active_seconds_and_shows_the_cap(
    client: TestClient, world: World, sender: Any, db: Session, root: Path, desk: None
) -> None:
    token = world.teacher_token
    digest = _hash(client, token, "ITEM.Q1")
    _post(client, token, _fix(digest, active_seconds=100))
    _post(client, token, _approve(digest, active_seconds=50))
    _post(client, _second_teacher(client, sender, db), _approve(digest, active_seconds=999))
    res = client.get("/staff/review/me/today", headers=auth_header(token))
    assert res.status_code == 200, res.text
    assert res.json() == {"active_seconds_today": 150, "daily_cap_seconds": 12600}
    # earlier days do not count
    row = db.scalars(select(ContentReviewRow).order_by(ContentReviewRow.created_at)).first()
    assert row is not None
    row.created_at = row.created_at.replace(year=2020)
    db.flush()
    again = client.get("/staff/review/me/today", headers=auth_header(token)).json()
    assert again["active_seconds_today"] == 50
    settings.reviewer_daily_cap_seconds = 600
    capped = client.get("/staff/review/me/today", headers=auth_header(token)).json()
    assert capped["daily_cap_seconds"] == 600


def test_a_reviewer_may_read_their_time_and_a_student_may_not(
    client: TestClient, world: World, sender: Any, root: Path, desk: None
) -> None:
    _, token = _invite(client, world, sender, "outside@example.com")
    assert client.get("/staff/review/me/today", headers=auth_header(token)).status_code == 200
    student = auth_header(world.student_token)
    assert client.get("/staff/review/me/today", headers=student).status_code == 403
    assert client.get("/staff/review/me/today").status_code == 401


def test_the_new_routes_do_not_exist_with_the_desk_off(
    client: TestClient, world: World, root: Path
) -> None:
    for path in ("/staff/review/reviewers", "/staff/review/me/today"):
        res = client.get(path, headers=auth_header(world.admin_token))
        assert res.status_code == 404, path
