"""G6 step 1: which consent scopes exist comes from the jurisdiction profile, not from code."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.consent import active_scopes, available_scopes
from app.registries.loaders import RegistryLoadError, load_jurisdiction_profile
from app.registries.startup import deployment_jurisdiction_profile
from tests.conftest import World, auth_header

BASE = 'id: {id}\nquiet_hours: {{start: "21:00", end: "07:00"}}\nnotation_profile: default_ascii\n'


def _profile(tmp_path: Path, pid: str, extra: str) -> Path:
    (tmp_path / "jurisdictions").mkdir(exist_ok=True)
    (tmp_path / "jurisdictions" / f"{pid}.yaml").write_text(
        BASE.format(id=pid) + extra, encoding="utf-8"
    )
    return tmp_path


def test_the_default_profile_lists_every_scope_including_free_text() -> None:
    profile = deployment_jurisdiction_profile()
    assert set(profile.consent_scopes) == {
        "tutoring",
        "teacher_share",
        "ai_processing",
        "free_text",
        "research_pseudonymised",
    }
    assert profile.guest_retention_days == 90


def test_a_profile_without_a_scope_list_allows_tutoring_only(tmp_path: Path) -> None:
    root = _profile(tmp_path, "bare", "")
    assert load_jurisdiction_profile("bare", root).consent_scopes == ("tutoring",)


@pytest.mark.parametrize(
    "extra",
    ["consent_scopes: [teacher_share]\n", "consent_scopes: [tutoring, mind_reading]\n"],
)
def test_a_profile_must_include_tutoring_and_only_known_scopes(tmp_path: Path, extra: str) -> None:
    root = _profile(tmp_path, "bad", extra)
    with pytest.raises(RegistryLoadError, match="consent_scopes"):
        load_jurisdiction_profile("bad", root)


def test_retention_must_be_a_positive_number_of_days(tmp_path: Path) -> None:
    root = _profile(tmp_path, "neg", "guest_retention_days: -3\n")
    with pytest.raises(RegistryLoadError, match="guest_retention_days"):
        load_jurisdiction_profile("neg", root)


def _narrow(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, scopes: str) -> None:
    root = _profile(tmp_path, "narrow", f"consent_scopes: {scopes}\n")
    monkeypatch.setattr("app.registries.loaders.config_dir", lambda: root)
    monkeypatch.setattr(
        "app.registries.startup.available_jurisdiction_profiles", lambda: ["narrow"]
    )
    monkeypatch.setattr("app.config.settings.jurisdiction_profile", "narrow")
    monkeypatch.setattr("app.auth.consent._profile_id_for", lambda db, student: "narrow")


def test_a_scope_the_profile_does_not_offer_cannot_be_granted(
    client: TestClient, world: World, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _narrow(monkeypatch, tmp_path, "[tutoring, teacher_share]")
    response = client.post(
        f"/students/{world.student_noshare_id}/consent",
        json={"version": "v2", "scopes": ["tutoring", "ai_processing"]},
        headers=auth_header(world.parent_token),
    )
    assert response.status_code == 400 and "not available" in response.text
    ok = client.post(
        f"/students/{world.student_noshare_id}/consent",
        json={"version": "v2", "scopes": ["tutoring", "teacher_share"]},
        headers=auth_header(world.parent_token),
    )
    assert ok.status_code == 200, ok.text


def test_the_consent_options_endpoint_lists_what_a_guardian_can_grant(
    client: TestClient, world: World, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _narrow(monkeypatch, tmp_path, "[tutoring, free_text]")
    response = client.get(
        f"/students/{world.student_noshare_id}/consent/options",
        headers=auth_header(world.parent_token),
    )
    assert response.status_code == 200, response.text
    assert response.json()["scopes"] == ["free_text", "tutoring"]
    other = client.get(
        f"/students/{world.student_noshare_id}/consent/options",
        headers=auth_header(world.other_parent_token),
    )
    assert other.status_code == 403


def test_a_granted_scope_stops_working_when_the_profile_withdraws_it(
    db: Session, world: World, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    student = uuid.UUID(world.student_share_id)
    assert "ai_processing" in active_scopes(db, student)
    _narrow(monkeypatch, tmp_path, "[tutoring]")
    assert active_scopes(db, student) == {"tutoring"}
    assert available_scopes(db, student) == {"tutoring"}


def test_free_text_is_a_grantable_scope(client: TestClient, world: World) -> None:
    response = client.post(
        f"/students/{world.student_noshare_id}/consent",
        json={"version": "v2", "scopes": ["tutoring", "free_text"]},
        headers=auth_header(world.parent_token),
    )
    assert response.status_code == 200, response.text
