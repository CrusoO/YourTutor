import os
from pathlib import Path

import pytest

from app.content.bundle_merge import load_content_bundle, merge_bundles
from app.content.validator import load_bundle

REPO_CONTENT = Path(__file__).resolve().parents[4] / "content"


def test_merge_adds_mini_skills_and_items() -> None:
    primary = load_bundle(REPO_CONTENT)
    mini = load_bundle(REPO_CONTENT / "e2e_mini")
    merged = merge_bundles(primary, mini)
    assert any(s.id == "MATH.E2E.ONE" for s in merged.skills)
    assert any(i.id == "ITEM.E2E.D.01" for i in merged.items)
    assert any(o.id == "OV.E2E.MINI" for o in merged.overlays)


def test_load_content_bundle_includes_mini_when_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("E2E_MINI_CONTENT", "true")
    bundle = load_content_bundle(REPO_CONTENT)
    assert any(i.id == "ITEM.E2E.D.06" for i in bundle.items)


def test_load_content_bundle_omits_mini_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("E2E_MINI_CONTENT", raising=False)
    os.environ.pop("E2E_MINI_CONTENT", None)
    from app.config import settings

    settings.e2e_mini_content = False
    bundle = load_content_bundle(REPO_CONTENT)
    assert not any(i.id.startswith("ITEM.E2E.") for i in bundle.items)
