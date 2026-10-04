from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, settings
from app.main import app
from app.registries.loaders import RegistryLoadError
from app.registries.paths import config_dir, content_curricula_dir, repo_root
from app.registries.startup import (
    available_jurisdiction_profiles,
    deployment_jurisdiction_profile,
    validate_startup_config,
)


def test_default_profile_is_default_strict() -> None:
    assert Settings().jurisdiction_profile == "default_strict"
    profile = deployment_jurisdiction_profile()
    assert profile.id == "default_strict"
    assert (profile.quiet_hours.start, profile.quiet_hours.end) == ("21:00", "07:00")


def test_env_var_selects_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JURISDICTION_PROFILE", "default_strict")
    assert Settings().jurisdiction_profile == "default_strict"
    monkeypatch.setenv("JURISDICTION_PROFILE", "something_else")
    assert Settings().jurisdiction_profile == "something_else"


@pytest.mark.parametrize("bad", ["nope", "", "../default_strict", "Default_Strict"])
def test_unknown_profile_is_an_error(bad: str) -> None:
    with pytest.raises(RegistryLoadError, match="unknown JURISDICTION_PROFILE"):
        deployment_jurisdiction_profile(bad)


def test_unknown_profile_stops_app_startup() -> None:
    settings.jurisdiction_profile = "nope"
    with pytest.raises(RegistryLoadError, match="nope"):
        with TestClient(app):
            pass


def test_app_starts_with_default_profile() -> None:
    validate_startup_config()
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200


def test_env_example_documents_the_variable() -> None:
    text = (repo_root() / ".env.example").read_text(encoding="utf-8")
    assert "JURISDICTION_PROFILE=default_strict" in text
    assert "default_strict" in available_jurisdiction_profiles()


def test_config_and_content_dirs_can_be_overridden(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CONFIG_DIR", str(tmp_path / "cfg"))
    monkeypatch.setenv("CONTENT_DIR", str(tmp_path / "content"))
    assert config_dir() == tmp_path / "cfg"
    assert content_curricula_dir() == tmp_path / "content" / "curricula"
    monkeypatch.delenv("CONFIG_DIR")
    monkeypatch.delenv("CONTENT_DIR")
    assert config_dir() == repo_root() / "config"
    assert content_curricula_dir() == repo_root() / "content" / "curricula"
