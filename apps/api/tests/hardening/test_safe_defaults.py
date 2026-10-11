"""Integration gate: a bare install (no environment) ships with every risky feature off."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.config import Settings
from app.llm.gateway import Gate, skip_reason

ROOT = Path(__file__).resolve().parents[4]
RISKY = (
    "ASK_ENABLED",
    "ASK_GUESTS_ENABLED",
    "RESEARCH_MODULE",
    "ALLOW_DRAFT_CONTENT",
    "DEV_TOOLS",
    "LLM_API_KEY",
    "SMTP_HOST",
    "OTEL_ENABLED",
    "APP_ENV",
)


@pytest.fixture
def bare(monkeypatch: pytest.MonkeyPatch) -> Settings:
    for name in RISKY:
        monkeypatch.delenv(name, raising=False)
    return Settings(_env_file=None)  # type: ignore[call-arg]


def test_risky_features_are_off_without_configuration(bare: Settings) -> None:
    assert bare.ask_enabled is False and bare.ask_guests_enabled is False
    assert bare.research_module is False
    assert bare.allow_draft_content is False and bare.dev_tools is False
    assert bare.otel_enabled is False
    assert bare.llm_api_key == "" and bare.smtp_host == ""


def test_no_model_call_without_a_key_and_ai_processing(bare: Settings) -> None:
    assert skip_reason(Gate("practice", True, bool(bare.llm_api_key))) == "no_key"
    assert skip_reason(Gate("practice", False, True)) == "consent"
    assert skip_reason(Gate("practice", True, True)) is None


def test_the_compose_file_does_not_default_draft_content_on() -> None:
    text = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    match = re.search(r"ALLOW_DRAFT_CONTENT:\s*\$\{ALLOW_DRAFT_CONTENT:-(\w+)\}", text)
    assert match and match.group(1) == "false"


def test_the_web_app_carries_no_tracking_sdk() -> None:
    package = (ROOT / "apps/web/package.json").read_text(encoding="utf-8").lower()
    for name in ("analytics", "sentry", "posthog", "mixpanel", "gtag", "segment", "hotjar"):
        assert name not in package
