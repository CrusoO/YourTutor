"""REVIEWERS_ONLY: a reviewer-only deployment serves the desk and sign-in basics, nothing else."""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import main, operator
from app.config import (
    Settings,
    production_config_errors,
    production_flag_errors,
    production_secret_errors,
    reviewers_only_errors,
    settings,
)
from app.main import app, reviewers_only_allows
from tests.conftest import World, auth_header, seed_user

PLACEHOLDER = re.compile(r"\{[^}]+\}")
OPEN_PATHS = {
    "/health",
    "/ready",
    "/auth/me",
    "/auth/options",
    "/auth/verify-otp",
    "/agreements/me",
    "/staff/review",
}


def _helplines() -> list[str]:
    return ["tele_manas", "childline"]


def _production(**over: object) -> Settings:
    base: dict[str, object] = {
        "app_env": "production",
        "token_pepper": "p" * 40,
        "ask_enabled": True,
        "anthropic_api_key": "set",
        "cors_extra_origins": "https://app.example.org",
    }
    return Settings(_env_file=None, **{**base, **over})  # type: ignore[arg-type,call-arg]


def _routes() -> list[tuple[str, str]]:
    """Every (method, path template) the app registers, from its own OpenAPI document."""
    out: list[tuple[str, str]] = []
    for path, ops in app.openapi()["paths"].items():
        out.extend((method.upper(), path) for method in ops)
    return out


def _concrete(path: str) -> str:
    return PLACEHOLDER.sub(lambda _m: str(uuid.uuid4()), path)


def _is_open(path: str) -> bool:
    if path == "/agreements/{role}":
        return False  # only /agreements/reviewer is open; checked on its own below
    return path in OPEN_PATHS or path.startswith("/staff/review/")


@pytest.fixture
def only(world: World) -> None:
    """Switch the mode on after `world` is built (building it uses the closed sign-up route)."""
    settings.reviewer_desk_enabled = True
    settings.reviewers_only = True


def _issue_and_sign_in(
    client: TestClient, db: Session, world: World, email: str, terms: bool
) -> str:
    """The real flow: an admin issues a one-time code, the reviewer verifies it. Returns a token."""
    rev = seed_user(db, "reviewer", email, terms=terms)
    made = client.post(
        f"/staff/review/reviewers/{rev.id}/sign-in-code", headers=auth_header(world.admin_token)
    )
    assert made.status_code == 200, made.text
    signed = client.post("/auth/verify-otp", json={"email": email, "code": made.json()["code"]})
    assert signed.status_code == 200, signed.text
    return str(signed.json()["access_token"])


# ---- the guards ----------------------------------------------------------------------------


def test_the_three_learner_safety_guards_are_enforced_in_normal_mode() -> None:
    errors = production_config_errors(
        _production(smtp_host="", llm_daily_cap=0), unverified_helplines=_helplines
    )
    names = " | ".join(errors)
    assert "SMTP_HOST" in names and "LLM_DAILY_CAP" in names and "HELPLINES" in names


def test_reviewers_only_skips_exactly_those_three_and_keeps_the_rest() -> None:
    config = _production(
        smtp_host="",
        llm_daily_cap=0,
        reviewers_only=True,
        reviewer_desk_enabled=True,
        token_pepper="dev-only-change-me",
        cors_extra_origins="http://localhost:3000",
    )
    names = " | ".join(production_config_errors(config, unverified_helplines=_helplines))
    for skipped in ("SMTP_HOST", "LLM_DAILY_CAP", "HELPLINES"):
        assert skipped not in names
    assert "TOKEN_PEPPER" in names and "CORS_EXTRA_ORIGINS" in names


def test_reviewers_only_does_not_even_ask_for_the_helplines() -> None:
    def boom() -> list[str]:
        raise AssertionError("helplines must not be read in reviewers-only mode")

    config = _production(reviewers_only=True, reviewer_desk_enabled=True, smtp_host="")
    check: Callable[[], list[str]] = boom
    assert production_config_errors(config, unverified_helplines=check) == []


def test_other_production_guards_stay_on_in_reviewers_only_mode() -> None:
    dev = _production(reviewers_only=True, reviewer_desk_enabled=True, dev_tools=True)
    assert production_flag_errors(dev) == ["DEV_TOOLS"]
    default_password = _production(reviewers_only=True, reviewer_desk_enabled=True)
    assert production_secret_errors(default_password) == ["POSTGRES_PASSWORD"]


def test_the_mode_needs_the_desk() -> None:
    assert reviewers_only_errors(_production(reviewers_only=True)) != []
    assert reviewers_only_errors(_production(reviewers_only=True, reviewer_desk_enabled=True)) == []
    assert reviewers_only_errors(_production()) == []


def test_the_api_refuses_to_start_reviewers_only_without_the_desk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main.settings, "reviewers_only", True)
    monkeypatch.setattr(main.settings, "reviewer_desk_enabled", False)
    with pytest.raises(RuntimeError, match="Refusing to start.*REVIEWER_DESK_ENABLED"):
        with TestClient(main.app):
            pass


def _clean_production(monkeypatch: pytest.MonkeyPatch, **over: object) -> None:
    values: dict[str, object] = {
        "app_env": "production",
        "postgres_password": "a-real-password-for-the-test",
        "token_pepper": "p" * 40,
        "smtp_host": "",
        "llm_daily_cap": 0,
        "pilot_onboarding": False,
        "ask_enabled": False,
        "explain_enabled": False,
        "cors_extra_origins": "",
        "allow_draft_content": False,
        "database_url": "",
        **over,
    }
    for name, value in values.items():
        monkeypatch.setattr(main.settings, name, value)
    for flag in production_flag_errors(main.settings):
        monkeypatch.setattr(main.settings, flag.lower(), False)
    monkeypatch.setattr(main, "unverified_helplines", lambda: ["tele_manas"])


def test_a_clean_reviewers_only_production_starts_without_smtp_cap_or_helplines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clean_production(monkeypatch, reviewers_only=True, reviewer_desk_enabled=True)
    with TestClient(main.app) as client:
        assert client.get("/health").status_code == 200


def test_the_same_production_settings_are_refused_in_normal_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clean_production(monkeypatch, reviewers_only=False)
    with pytest.raises(RuntimeError, match="SMTP_HOST.*HELPLINES"):
        with TestClient(main.app):
            pass


# ---- the routes ----------------------------------------------------------------------------


def test_the_allowlist_function() -> None:
    for path in (
        "/health",
        "/ready",
        "/staff/review",
        "/staff/review/chapters",
        "/auth/me",
        "/auth/options",
        "/auth/verify-otp",
        "/agreements/me",
        "/agreements/reviewer",
    ):
        assert reviewers_only_allows(path), path
    for path in (
        "/auth/request-otp",
        "/auth/student-login",
        "/agreements/parent",
        "/agreements/reviewer/withdraw",
        "/staff/reviewer-x",
        "/staff",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/guest/start",
        "/healthz",
    ):
        assert not reviewers_only_allows(path), path


def test_every_registered_route_is_classified_and_every_learner_route_is_closed(
    client: TestClient, only: None
) -> None:
    routes = _routes()
    assert len(routes) > 100  # the derivation found the app's real routes
    closed = [(m, p) for m, p in routes if not _is_open(p)]
    for prefix in ("/guest", "/students", "/parents", "/teacher", "/explain", "/doubt", "/video"):
        assert any(p.startswith(prefix) for _, p in closed), prefix
    assert ("POST", "/auth/request-otp") in closed
    for method, path in closed:
        response = client.request(method, _concrete(path))
        assert response.status_code == 404, (method, path)
        assert response.json() == {"detail": "not available"}, (method, path)
    for method, path in routes:
        if _is_open(path):
            response = client.request(method, _concrete(path))
            assert response.json() != {"detail": "not available"}, (method, path)
    # the one reviewer agreement route is open, the other roles are not
    assert client.get("/agreements/reviewer").json() != {"detail": "not available"}
    assert client.get("/agreements/parent").status_code == 404


@pytest.mark.parametrize(
    "path", ["/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect", "/", "/anything"]
)
def test_docs_and_unknown_paths_are_closed(client: TestClient, only: None, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 404
    assert response.json() == {"detail": "not available"}


def test_sign_up_and_other_sign_in_paths_are_closed(client: TestClient, only: None) -> None:
    for path, body in (
        ("/auth/request-otp", {"email": "x@example.com", "role": "parent"}),
        ("/guest/start", {}),
        ("/children/start", {}),
        ("/auth/student-login", {}),
    ):
        assert client.post(path, json=body).status_code == 404, path


def test_the_open_routes_still_work(client: TestClient, only: None) -> None:
    assert client.get("/health").json() == {"status": "ok", "service": "api"}
    assert client.get("/auth/options").status_code == 200


def test_an_admin_issues_a_code_and_the_reviewer_reaches_the_desk(
    client: TestClient, world: World, db: Session, only: None
) -> None:
    token = _issue_and_sign_in(client, db, world, "rev-only@example.com", terms=True)
    assert client.get("/staff/review/chapters", headers=auth_header(token)).status_code == 200
    admin = auth_header(world.admin_token)
    assert client.get("/staff/review/chapters", headers=admin).status_code == 200
    assert client.get("/staff/review/reviewers", headers=admin).status_code == 200
    assert client.get("/students/me/today", headers=auth_header(token)).status_code == 404


def test_a_reviewer_without_terms_still_gets_403(
    client: TestClient, world: World, db: Session, only: None
) -> None:
    token = _issue_and_sign_in(client, db, world, "no-terms@example.com", terms=False)
    blocked = client.get("/staff/review/chapters", headers=auth_header(token))
    assert blocked.status_code == 403
    assert blocked.json()["detail"] == {"code": "terms_not_accepted"}


def test_with_the_flag_off_nothing_is_hidden(client: TestClient) -> None:
    assert settings.reviewers_only is False
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/students/me/today").status_code == 401


def test_the_operator_check_marks_email_not_needed_and_prints_the_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in (("app_env", "production"), ("smtp_host", ""), ("reviewers_only", True)):
        monkeypatch.setattr(operator.settings, name, value)
    monkeypatch.setattr(operator.settings, "reviewer_desk_enabled", True)
    checks = {c.name: c for c in operator.run_checks()}
    assert checks["email for codes and reports"].ok
    assert "not needed" in checks["email for codes and reports"].detail
    assert (
        checks["reviewers-only mode"].ok
        and "REVIEWERS_ONLY is on" in checks["reviewers-only mode"].detail
    )
    monkeypatch.setattr(operator.settings, "reviewer_desk_enabled", False)
    assert not {c.name: c for c in operator.run_checks()}["reviewers-only mode"].ok
    monkeypatch.setattr(operator.settings, "reviewers_only", False)
    after = {c.name: c for c in operator.run_checks()}
    assert not after["email for codes and reports"].ok  # normal mode: still required
    assert after["reviewers-only mode"].ok


def test_a_leading_api_prefix_is_removed_before_routing(client: TestClient, only: None) -> None:
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/auth/options").status_code == 200
    assert client.get("/api/students/me/today").status_code == 404
    assert main.without_api_prefix("/apiary") == "/apiary"
    assert main.without_api_prefix("/api") == "/"
    assert main.without_api_prefix("/api/staff/review/chapters") == "/staff/review/chapters"
