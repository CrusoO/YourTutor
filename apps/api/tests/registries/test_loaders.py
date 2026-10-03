from __future__ import annotations

from app.registries.loaders import (
    load_all_curricula,
    load_grade_bands,
    load_jurisdiction_profile,
    load_locales_config,
    load_notation_profiles,
)
from app.registries.locale_resolve import locale_text_missing, resolve_locale_chain


def test_locales_and_grade_bands_load() -> None:
    default, locales = load_locales_config()
    assert default == "en"
    assert locales["ne"].fallback_chain == ("en",)
    bands = load_grade_bands()
    assert bands[0].grades == (9, 10)


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
