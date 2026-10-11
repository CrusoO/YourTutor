"""Hardening: a production start refuses to run with a development-only switch on."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import DEV_ONLY_FLAGS, Settings, production_flag_errors


def _settings(monkeypatch: pytest.MonkeyPatch, **env: str) -> Settings:
    for name in ("APP_ENV", *(f.upper() for f in DEV_ONLY_FLAGS)):
        monkeypatch.delenv(name, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return Settings(_env_file=None)  # type: ignore[call-arg]


@pytest.mark.parametrize("flag", [f.upper() for f in DEV_ONLY_FLAGS])
def test_each_dev_only_flag_is_reported_in_production(
    monkeypatch: pytest.MonkeyPatch, flag: str
) -> None:
    assert production_flag_errors(
        _settings(monkeypatch, APP_ENV="production", **{flag: "true"})
    ) == [flag]


def test_a_clean_production_setup_and_any_development_setup_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert production_flag_errors(_settings(monkeypatch, APP_ENV="production")) == []
    everything = {f.upper(): "true" for f in DEV_ONLY_FLAGS}
    assert production_flag_errors(_settings(monkeypatch, APP_ENV="development", **everything)) == []
    assert production_flag_errors(_settings(monkeypatch, APP_ENV="Production ", DEV_TOOLS="1")) == [
        "DEV_TOOLS"
    ]


def test_the_api_refuses_to_start_with_a_clear_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main.settings, "app_env", "production")
    monkeypatch.setattr(main.settings, "allow_draft_content", True)
    monkeypatch.setattr(main.settings, "research_module", True)
    with pytest.raises(
        RuntimeError, match="Refusing to start.*ALLOW_DRAFT_CONTENT.*RESEARCH_MODULE"
    ):
        with TestClient(main.app):
            pass


def test_the_api_starts_when_production_is_clean(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main.settings, "app_env", "production")
    for name in DEV_ONLY_FLAGS:
        monkeypatch.setattr(main.settings, name, False)
    with TestClient(main.app) as client:
        assert client.get("/health").status_code == 200
