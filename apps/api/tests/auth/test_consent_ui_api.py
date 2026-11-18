"""Consent UI support: the text endpoint, the guardian's offer list and the export's text hashes."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth import consent_texts as ct
from app.auth.consent import active_scopes
from app.auth.scopes import NEW_SCOPES, SCOPE_REGISTRY
from app.config import settings
from tests.conftest import World, auth_header

SHOWN = sorted(NEW_SCOPES | {"learning_profile"})


def _flag(monkeypatch: pytest.MonkeyPatch, scope: str, on: bool) -> None:
    flag = SCOPE_REGISTRY[scope].flag_setting
    assert flag
    monkeypatch.setattr(settings, flag, on)


def test_the_default_profile_offers_the_four_scopes_but_every_flag_is_off() -> None:
    from app.registries.startup import deployment_jurisdiction_profile

    assert set(SHOWN) <= set(deployment_jurisdiction_profile().consent_scopes)
    for scope in SHOWN:
        flag = SCOPE_REGISTRY[scope].flag_setting
        assert flag and getattr(settings, flag) is False, scope


@pytest.mark.parametrize("scope", SHOWN)
def test_no_text_is_served_while_the_flag_is_off(client: TestClient, scope: str) -> None:
    assert client.get(f"/consent/texts/{scope}").status_code == 404


@pytest.mark.parametrize("scope", SHOWN)
def test_the_approved_text_and_hashes_are_served_when_the_flag_is_on(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, scope: str
) -> None:
    _flag(monkeypatch, scope, True)
    body = client.get(f"/consent/texts/{scope}").json()
    expected = ct.current_manifest(scope)
    assert expected
    assert body["scope"] == scope and body["version"] == expected["version"]
    for audience in ct.AUDIENCES:
        assert body[audience]["sha256"] == expected["sha256"][audience]
        assert body[audience]["text"].strip()
        path = ct.texts_root() / scope / f"{body['version']}.en.{audience}.md"
        assert body[audience]["text"] == path.read_text(encoding="utf-8").strip()


@pytest.mark.parametrize("scope", ["tutoring", "free_text", "uploads", "mind_reading", "..%2F"])
def test_scopes_without_wording_or_unknown_ones_are_404(client: TestClient, scope: str) -> None:
    assert client.get(f"/consent/texts/{scope}").status_code == 404


def test_no_text_is_served_when_the_files_do_not_match_the_manifest(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _flag(monkeypatch, "math_check", True)
    monkeypatch.setattr(ct, "current_manifest", lambda *a, **k: None)
    assert client.get("/consent/texts/math_check").status_code == 404


def test_the_agreement_offers_a_scope_only_when_its_flag_is_on(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def offered() -> set[str]:
        return {i["id"] for i in client.get("/agreements/guardian").json()["items"]}

    assert not offered() & set(SHOWN)
    _flag(monkeypatch, "math_check", True)
    assert "math_check" in offered() and "photo_check" not in offered()


def test_a_guardian_can_grant_a_scope_and_the_export_carries_the_hash(
    client: TestClient, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    _flag(monkeypatch, "math_check", True)
    head = auth_header(world.parent_token)
    student = world.student_noshare_id
    res = client.post(
        f"/students/{student}/consent",
        json={"version": "v1", "scopes": ["tutoring", "math_check"]},
        headers=head,
    )
    assert res.status_code == 200, res.text
    consents = client.get("/parents/me/export", headers=head).json()["consents"]
    mine = [c for c in consents if c["student_id"] == student and c["revoked_at"] is None]
    assert len(mine) == 1
    shown = mine[0]["text_manifest"]["math_check"]
    expected = ct.current_manifest("math_check")
    assert expected and shown["sha256"]["guardian"] == expected["sha256"]["guardian"]
    assert shown["version"] == "v1" and "granted_at" in mine[0]
    # with the flag off again a grant is refused, so nothing switches on by itself
    _flag(monkeypatch, "math_check", False)
    again = client.post(
        f"/students/{student}/consent",
        json={"version": "v1", "scopes": ["tutoring", "math_check"]},
        headers=head,
    )
    assert again.status_code == 400


def test_an_old_scope_name_does_not_switch_on_its_replacement_while_the_flag_is_off(
    client: TestClient, world: World, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    head = auth_header(world.parent_token)
    student = world.student_noshare_id
    res = client.post(
        f"/students/{student}/consent",
        json={"version": "v1", "scopes": ["tutoring", "uploads", "free_text"]},
        headers=head,
    )
    assert res.status_code == 200, res.text
    sid = uuid.UUID(student)
    active = active_scopes(db, sid)
    assert {"uploads", "free_text"} <= active
    assert not active & {"photo_check", "ai_help_typed"}
    _flag(monkeypatch, "photo_check", True)
    assert "photo_check" in active_scopes(db, sid)
