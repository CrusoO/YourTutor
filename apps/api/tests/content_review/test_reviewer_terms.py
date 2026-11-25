"""Reviewer terms: a versioned agreement every reviewer accepts before reviewing."""

# ruff: noqa: F811
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.auth import agreements
from app.config import settings
from app.db.models import AgreementRow
from tests.conftest import World, accept_reviewer_terms, auth_header, seed_user, signup
from tests.content.conftest import content_root, loc, minimal_item, write_yaml  # noqa: F401
from tests.content_review.test_review_api import root  # noqa: F401

BODY = {"version": agreements.REVIEWER_VERSION, "items": ["accept_reviewer_terms"]}


@pytest.fixture
def desk() -> Iterator[None]:
    before = (settings.reviewer_desk_enabled, settings.reviewer_terms_contact)
    settings.reviewer_desk_enabled = True
    yield
    settings.reviewer_desk_enabled, settings.reviewer_terms_contact = before


def _new_reviewer(client: TestClient, sender: Any, db: Any) -> tuple[Any, str]:
    user = seed_user(db, "reviewer", "rv@example.com", terms=False)
    return user, signup(client, sender, user.email)


GET_ROUTES = (
    "/staff/review/items",
    "/staff/review/items?status=todo",
    "/staff/review/chapters",
    "/staff/review/me/today",
)
REFUSED = {"code": "terms_not_accepted"}


def test_not_accepted_is_refused_on_every_review_route(
    client: TestClient, sender: Any, db: Any, root: Any, desk: None
) -> None:
    _, token = _new_reviewer(client, sender, db)
    head = auth_header(token)
    for path in GET_ROUTES:
        out = client.get(path, headers=head)
        assert out.status_code == 403, path
        assert out.json()["detail"] == REFUSED, path
    decision = client.post(
        "/staff/review/items/ITEM.Q1/decision",
        json={"content_hash": "x", "decision": "approve"},
        headers=head,
    )
    assert decision.status_code == 403
    assert decision.json()["detail"] == REFUSED
    assert client.get("/auth/me", headers=head).json()["agreements"] == ["reviewer"]


def test_accepting_opens_the_desk_and_records_who_which_version_when(
    client: TestClient, sender: Any, db: Any, root: Any, desk: None
) -> None:
    user, token = _new_reviewer(client, sender, db)
    head = auth_header(token)
    done = client.post("/agreements/reviewer", json=BODY, headers=head)
    assert done.status_code == 200, done.text
    assert client.get("/auth/me", headers=head).json()["agreements"] == []
    for path in GET_ROUTES:
        assert client.get(path, headers=head).status_code == 200, path
    db.expire_all()
    row = db.query(AgreementRow).filter_by(user_id=user.id, role="reviewer").one()
    assert row.version == agreements.REVIEWER_VERSION
    assert row.granted_at is not None and row.revoked_at is None


def test_the_terms_must_be_ticked_and_the_version_current(
    client: TestClient, sender: Any, db: Any, desk: None
) -> None:
    _, token = _new_reviewer(client, sender, db)
    head = auth_header(token)
    empty = client.post("/agreements/reviewer", json={**BODY, "items": []}, headers=head)
    assert empty.status_code == 400
    stale = client.post(
        "/agreements/reviewer", json={**BODY, "version": "agreement-v1"}, headers=head
    )
    assert stale.status_code == 409


def test_a_new_version_forces_acceptance_again(
    client: TestClient,
    sender: Any,
    db: Any,
    root: Any,
    desk: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = seed_user(db, "reviewer", "rv@example.com")  # accepted the current version
    head = auth_header(signup(client, sender, user.email))
    assert client.get("/staff/review/me/today", headers=head).status_code == 200
    monkeypatch.setattr(agreements, "REVIEWER_VERSION", "reviewer-terms-v2")
    again = client.get("/staff/review/me/today", headers=head)
    assert again.status_code == 403
    assert again.json()["detail"] == REFUSED
    assert client.get("/auth/me", headers=head).json()["agreements"] == ["reviewer"]
    ok = client.post(
        "/agreements/reviewer",
        json={"version": "reviewer-terms-v2", "items": ["accept_reviewer_terms"]},
        headers=head,
    )
    assert ok.status_code == 200
    assert client.get("/staff/review/me/today", headers=head).status_code == 200


def test_the_catalog_carries_the_contact_setting(client: TestClient, desk: None) -> None:
    out = client.get("/agreements/reviewer").json()
    assert out["version"] == agreements.REVIEWER_VERSION
    assert out["contact"] == "the Brownie team"
    settings.reviewer_terms_contact = "terms@example.org"
    assert client.get("/agreements/reviewer").json()["contact"] == "terms@example.org"


def test_desk_off_nothing_changes(client: TestClient, sender: Any, db: Any) -> None:
    assert client.get("/agreements/reviewer").status_code == 404
    user = seed_user(db, "reviewer", "rv@example.com", terms=False)
    head = auth_header(signup(client, sender, user.email))
    assert client.get("/auth/me", headers=head).json()["agreements"] == []
    assert client.get("/staff/review/items", headers=head).status_code == 403
    assert client.post("/agreements/reviewer", json=BODY, headers=head).status_code == 403


def test_a_reviewer_gets_only_the_reviewer_agreement_routes(
    client: TestClient, sender: Any, db: Any, desk: None
) -> None:
    _, token = _new_reviewer(client, sender, db)
    head = auth_header(token)
    assert client.get("/agreements/me", headers=head).status_code == 200
    assert client.post("/agreements/guardian", json=BODY, headers=head).status_code == 403
    assert client.post("/agreements/teacher", json=BODY, headers=head).status_code == 403
    assert client.post("/agreements/reviewer", json=BODY, headers=head).status_code == 200
    gone = client.post(
        "/agreements/reviewer/withdraw", json={"item": "accept_reviewer_terms"}, headers=head
    )
    assert gone.status_code == 403
    assert client.get("/children/me/status", headers=head).status_code == 403


def test_teachers_and_admins_are_not_subject_to_it(
    client: TestClient, world: World, root: Any, desk: None
) -> None:
    for token in (world.admin_token, world.teacher_token):
        assert client.get("/staff/review/me/today", headers=auth_header(token)).status_code == 200


def test_an_admin_sees_who_has_accepted(
    client: TestClient, world: World, db: Any, desk: None
) -> None:
    yes = seed_user(db, "reviewer", "yes@example.com", terms=False)
    accept_reviewer_terms(db, yes)
    no = seed_user(db, "reviewer", "no@example.com", terms=False)
    rows = client.get("/staff/review/reviewers", headers=auth_header(world.admin_token)).json()
    by_id = {r["id"]: r["terms_accepted"] for r in rows["reviewers"]}
    assert by_id == {str(yes.id): True, str(no.id): False}
