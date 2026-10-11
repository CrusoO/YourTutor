"""Hardening: the server decides which consent scopes a request may grant."""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.scopes import CONSENT_SCOPES, GUARDIAN_ONLY_SCOPES, scope_error
from app.auth.service import check_scopes
from tests.conftest import World, auth_header

GUARDIAN_SCOPES = sorted(GUARDIAN_ONLY_SCOPES)


def test_uploads_is_a_known_guardian_only_scope() -> None:
    assert "uploads" in CONSENT_SCOPES and "uploads" in GUARDIAN_ONLY_SCOPES
    assert "tutoring" in CONSENT_SCOPES and "tutoring" not in GUARDIAN_ONLY_SCOPES


@pytest.mark.parametrize("scope", GUARDIAN_SCOPES)
def test_a_guest_cannot_grant_a_scope_that_needs_a_guardian(scope: str) -> None:
    assert scope_error(["tutoring", scope], guest=True, available=CONSENT_SCOPES)
    assert scope_error(["tutoring", scope], guest=False, available=CONSENT_SCOPES) is None


def test_unknown_scopes_are_rejected_for_everyone() -> None:
    for guest in (True, False):
        assert "unknown" in str(
            scope_error(["tutoring", "mind_reading"], guest=guest, available=CONSENT_SCOPES)
        )


def test_a_guardian_gets_only_what_the_profile_allows() -> None:
    narrow = {"tutoring", "teacher_share"}
    assert scope_error(["tutoring", "teacher_share"], guest=False, available=narrow) is None
    assert "not available" in str(
        scope_error(["tutoring", "uploads"], guest=False, available=narrow)
    )


@pytest.mark.parametrize("scope", GUARDIAN_SCOPES)
def test_the_server_refuses_a_guest_students_request_for_each_guardian_scope(
    client: TestClient, db: Session, scope: str
) -> None:
    guest = client.post("/guest/start", json={"curriculum_id": "bhutan", "grade": 9}).json()
    with pytest.raises(HTTPException) as err:
        check_scopes(db, uuid.UUID(guest["student_id"]), ["tutoring", scope])
    assert err.value.status_code == 400 and "guests cannot grant" in str(err.value.detail)


@pytest.mark.parametrize("scope", [*GUARDIAN_SCOPES, "tutoring"])
def test_a_guest_token_cannot_call_the_consent_endpoint(client: TestClient, scope: str) -> None:
    guest = client.post("/guest/start", json={"curriculum_id": "bhutan", "grade": 9}).json()
    res = client.post(
        f"/students/{guest['student_id']}/consent",
        json={"version": "v1", "scopes": ["tutoring", scope]},
        headers=auth_header(guest["token"]),
    )
    assert res.status_code in (401, 403)


@pytest.mark.parametrize("scope", GUARDIAN_SCOPES)
def test_a_guardian_can_grant_each_scope_the_default_profile_allows(
    client: TestClient, world: World, scope: str
) -> None:
    res = client.post(
        f"/students/{world.student_noshare_id}/consent",
        json={"version": "v1", "scopes": ["tutoring", scope]},
        headers=auth_header(world.parent_token),
    )
    assert res.status_code == 200, res.text
