from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.loader import load_path
from app.db.models import LocaleRow, OverlayRow, SectionRow
from app.db.session import session_factory
from app.registries.loaders import (
    RegistryLoadError,
    load_all_curricula,
    load_grade_bands,
    load_jurisdiction_profile,
    load_locales_config,
    load_notation_profiles,
)
from app.registries.locale_resolve import locale_text_missing, resolve_locale_chain
from app.registries.paths import repo_root


def test_locales_and_grade_bands_load() -> None:
    default, locales = load_locales_config()
    assert default == "en"
    assert locales["ne"].fallback_chain == ("en",)
    bands = load_grade_bands()
    assert {b.id: b.grades for b in bands}["lower_secondary"] == (9, 10)  # G2b: four bands now


def test_jurisdiction_and_notation_profiles() -> None:
    profile = load_jurisdiction_profile("default_strict")
    assert profile.quiet_hours.start == "21:00"
    profiles = load_notation_profiles()
    assert profiles["decimal_comma"].decimal_separator == ","


def test_curricula_registry_entries() -> None:
    curricula = load_all_curricula()
    assert set(curricula) >= {"bhutan", "seba", "sample_board"}
    assert curricula["bhutan"].books[0].default_chapter_id == "bhutan_class9"


def test_locale_chain_and_missing_text() -> None:
    assert resolve_locale_chain("ne") == ("ne", "en")
    assert locale_text_missing("<Nepali — to be filled by reviewer>")
    assert locale_text_missing("")
    assert not locale_text_missing("Solve for x")


def test_locale_metadata_loaded_from_registry() -> None:
    _, locales = load_locales_config()
    assert (locales["en"].name, locales["en"].script, locales["en"].status) == (
        "English",
        "Latn",
        "active",
    )
    assert locales["ne"].script == "Deva"
    assert locales["as"].status == "draft"


def test_locale_without_metadata_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "locales.yaml").write_text(
        "default: en\nlocales:\n  - code: en\n    fallback_chain: []\n", encoding="utf-8"
    )
    with pytest.raises(RegistryLoadError, match="missing name, script, status"):
        load_locales_config(tmp_path)


def test_locale_with_unknown_status_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "locales.yaml").write_text(
        "default: en\nlocales:\n  - {code: en, name: English, script: Latn, status: live}\n",
        encoding="utf-8",
    )
    with pytest.raises(RegistryLoadError, match="unknown status"):
        load_locales_config(tmp_path)


def test_locale_rows_seeded_with_metadata(db: Session) -> None:
    row = db.get(LocaleRow, "as")
    assert row is not None
    assert (row.name, row.script, row.status) == ("Assamese", "Beng", "draft")


def test_content_load_syncs_registry_and_overlay_sections(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'sync.db'}"
    load_path(repo_root() / "content", database_url=url)
    with session_factory(url)() as session:
        assert len(session.scalars(select(SectionRow)).all()) == 9
        assert session.get(LocaleRow, "ne") is not None
        overlay = session.get(OverlayRow, "bhutan_class9")
        assert overlay is not None
        assert sorted(overlay.section_map) == ["s1", "s2", "s3"]
