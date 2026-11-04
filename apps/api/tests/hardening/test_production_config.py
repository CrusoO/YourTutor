"""Hardening: a production start refuses unsafe secrets and settings (P0-B)."""

from __future__ import annotations

import inspect

import pytest

from app.auth import admin
from app.config import Settings, production_config_errors, production_flag_errors

GOOD = {
    "app_env": "production",
    "token_pepper": "p" * 40,
    "pilot_onboarding": True,
    "pilot_key": "k" * 40,
    "smtp_host": "smtp.example.org",
    "ask_enabled": True,
    "anthropic_api_key": "set",
    "cors_extra_origins": "https://app.example.org",
}


def _s(**over: object) -> Settings:
    return Settings(_env_file=None, **{**GOOD, **over})  # type: ignore[arg-type,call-arg]


def test_a_good_production_config_passes() -> None:
    assert production_config_errors(_s()) == []


def test_development_is_never_refused() -> None:
    dev = Settings(_env_file=None, app_env="development")  # type: ignore[call-arg]
    assert production_config_errors(dev) == []


@pytest.mark.parametrize(
    ("over", "name"),
    [
        ({"token_pepper": "dev-only-change-me"}, "TOKEN_PEPPER"),
        ({"token_pepper": "short"}, "TOKEN_PEPPER"),
        ({"pilot_key": "dev-pilot"}, "PILOT_KEY"),
        ({"pilot_key": "short"}, "PILOT_KEY"),
        ({"smtp_host": ""}, "SMTP_HOST"),
        ({"anthropic_api_key": ""}, "ANTHROPIC_API_KEY"),
        (
            {"anthropic_api_key": "", "ask_enabled": False, "explain_enabled": True},
            "ANTHROPIC_API_KEY",
        ),
        ({"cors_extra_origins": "http://localhost:3000"}, "CORS_EXTRA_ORIGINS"),
        (
            {"cors_extra_origins": "https://ok.example.org, http://127.0.0.1:3000"},
            "CORS_EXTRA_ORIGINS",
        ),
    ],
)
def test_each_unsafe_setting_is_refused(over: dict[str, object], name: str) -> None:
    errors = production_config_errors(_s(**over))
    assert len(errors) == 1 and errors[0].startswith(name)


def test_pilot_key_is_only_checked_while_pilot_onboarding_is_on() -> None:
    assert production_config_errors(_s(pilot_onboarding=False, pilot_key="dev-pilot")) == []


def test_no_llm_key_is_fine_when_no_llm_route_is_enabled() -> None:
    assert production_config_errors(_s(anthropic_api_key="", ask_enabled=False)) == []


def test_unverified_helplines_are_refused_through_the_injected_hook() -> None:
    errors = production_config_errors(_s(), unverified_helplines=lambda: ["IN-1"])
    assert len(errors) == 1 and errors[0].startswith("HELPLINES")
    assert production_config_errors(_s(), unverified_helplines=lambda: []) == []


@pytest.mark.xfail(reason="TODO(lead): wire app.safety.unverified_helplines in main", strict=True)
def test_lifespan_passes_the_safety_helpline_check() -> None:
    from app import main

    assert "unverified_helplines=" in inspect.getsource(main.lifespan)


def test_the_dev_flag_is_still_refused() -> None:
    assert production_flag_errors(_s(allow_draft_content=True)) == ["ALLOW_DRAFT_CONTENT"]


def test_pilot_key_compare_is_constant_time() -> None:
    assert "compare_digest" in inspect.getsource(admin._pilot_admin)


def test_production_origins_leave_out_localhost() -> None:
    from app.main import allowed_origins

    assert allowed_origins("https://app.example.org", production=True) == [
        "https://app.example.org"
    ]
    assert "http://localhost:3000" in allowed_origins("")
