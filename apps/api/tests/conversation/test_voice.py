"""C1: the conversation layer's voice. Register, length and the authored fallback. No model."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.conversation.voice import (
    FALLBACK_REASONS,
    Register,
    fallback_reason,
    fallback_turn,
    load_voice_config,
    register_for_grade,
    trim_to_words,
)
from app.registries.paths import config_dir

CONFIG = load_voice_config()
SHAMING = (
    "wrong",
    "fail",
    "weak",
    "lazy",
    "stupid",
    "dumb",
    "bad at",
    "should have",
    "great question",
)


def _all_lines() -> list[tuple[str, str, str]]:
    return [
        (reason, reg, line)
        for reason, by_reg in CONFIG.lines["en"].items()
        for reg, lines in by_reg.items()
        for line in lines
    ]


# -- the authored words follow the constitution ---------------------------------------------------


def test_every_reason_has_lines_for_the_default_register() -> None:
    for reason in FALLBACK_REASONS:
        assert CONFIG.lines["en"][reason]["default"], reason


def test_no_line_shames_or_gushes() -> None:
    for reason, reg, line in _all_lines():
        assert not any(word in line.lower() for word in SHAMING), (reason, reg, line)


def test_one_idea_and_at_most_one_question_per_line() -> None:
    for reason, reg, line in _all_lines():
        assert line.count("?") <= 1, (reason, reg, line)


def test_primary_lines_fit_the_primary_band_word_limit() -> None:
    limit = register_for_grade(3).max_words
    for reason, reg, line in _all_lines():
        if reg == "primary":
            assert len(line.split()) <= limit, (reason, line, limit)


def test_default_lines_fit_the_smallest_non_primary_band() -> None:
    limit = register_for_grade(7).max_words  # the middle band is the shortest of the others
    for reason, reg, line in _all_lines():
        if reg == "default":
            assert len(line.split()) <= limit, (reason, line, limit)


# -- register -------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("grade", "key", "words"),
    [(3, "primary", 25), (7, "default", 40), (10, "default", 60), (12, "default", 80)],
)
def test_register_comes_from_the_grade_band(grade: int, key: str, words: int) -> None:
    reg = register_for_grade(grade)
    assert (reg.key, reg.max_words) == (key, words) and reg.style


def test_an_unknown_grade_gets_the_default_tone_and_a_middle_limit() -> None:
    reg = register_for_grade(None)
    assert reg.key == "default" and reg.max_words == 60 and reg.band_id == "unknown"


# -- trimming -------------------------------------------------------------------------------------


def test_a_short_reply_is_left_alone() -> None:
    assert trim_to_words("You have the direction right. What happens next?", 25) == (
        "You have the direction right. What happens next?"
    )


def test_a_long_reply_is_cut_at_a_sentence_end() -> None:
    text = "One two three four five. Six seven eight nine ten. Eleven twelve thirteen."
    assert trim_to_words(text, 10) == "One two three four five. Six seven eight nine ten."
    assert trim_to_words(text, 7) == "One two three four five."


def test_a_first_sentence_that_is_too_long_is_cut_at_a_word() -> None:
    out = trim_to_words("one two three four five six seven eight nine ten", 4)
    assert out == "one two three four\u2026"


def test_trim_understands_the_hindi_full_stop() -> None:
    text = "यह पहला वाक्य है। यह दूसरा वाक्य है। यह तीसरा है।"
    assert trim_to_words(text, 8) == "यह पहला वाक्य है। यह दूसरा वाक्य है।"


def test_a_zero_limit_means_no_trimming() -> None:
    assert trim_to_words("a b c d", 0) == "a b c d"


# -- the fallback turn ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("unavailable", "expected"),
    [
        ("off", "ai_off"),
        ("consent", "no_consent"),
        ("no_key", "unavailable"),
        ("provider_error", "unavailable"),
        ("checks", "unavailable"),
        ("anything", "unavailable"),
    ],
)
def test_unavailable_reasons_map_to_an_honest_fallback(unavailable: str, expected: str) -> None:
    assert fallback_reason(unavailable) == expected


def test_the_fallback_uses_the_register_and_offers_choices() -> None:
    little = fallback_turn("provider_error", register_for_grade(3))
    older = fallback_turn("provider_error", register_for_grade(10))
    assert little["text"] in CONFIG.lines["en"]["unavailable"]["primary"]
    assert older["text"] in CONFIG.lines["en"]["unavailable"]["default"]
    assert [o["id"] for o in older["offers"]] == ["ask_again", "practice"]


def test_asking_again_is_not_offered_when_it_cannot_help() -> None:
    for unavailable in ("off", "consent"):
        offers = fallback_turn(unavailable, register_for_grade(10))["offers"]
        assert [o["id"] for o in offers] == ["practice"], unavailable


def test_the_fallback_line_changes_from_turn_to_turn_but_is_deterministic() -> None:
    reg = register_for_grade(10)
    first = fallback_turn("provider_error", reg, turn_index=0)["text"]
    second = fallback_turn("provider_error", reg, turn_index=1)["text"]
    assert first != second
    assert fallback_turn("provider_error", reg, turn_index=2)["text"] == first
    assert fallback_turn("provider_error", reg, turn_index=0)["text"] == first


def test_an_unknown_language_uses_the_english_block() -> None:
    assert fallback_turn("off", register_for_grade(10), language="xx")["text"]


def test_the_fallback_never_echoes_the_student() -> None:
    out = fallback_turn("provider_error", Register("default", "x", 60, ""))
    assert set(out) == {"reason", "text", "offers"}


# -- the config refuses a bad file ----------------------------------------------------------------


def _write(tmp_path: Path, mutate: Callable[[dict[str, Any]], object]) -> Path:
    data = yaml.safe_load((config_dir() / "conversation.yaml").read_text(encoding="utf-8"))
    mutate(data)
    (tmp_path / "conversation.yaml").write_text(
        yaml.safe_dump(data, allow_unicode=True), encoding="utf-8"
    )
    return tmp_path


def test_a_missing_default_register_line_is_refused(tmp_path: Path) -> None:
    root = _write(tmp_path, lambda d: d["languages"]["en"]["lines"]["ai_off"].pop("default"))
    with pytest.raises(ValueError, match="no default-register line"):
        load_voice_config(root)


def test_an_unknown_offer_is_refused(tmp_path: Path) -> None:
    root = _write(tmp_path, lambda d: d["languages"]["en"]["offers_for"]["ai_off"].append("sing"))
    with pytest.raises(ValueError, match="unknown 'sing'"):
        load_voice_config(root)


def test_an_unknown_reason_is_refused(tmp_path: Path) -> None:
    root = _write(
        tmp_path, lambda d: d["languages"]["en"]["lines"].update(scold={"default": ["Try harder."]})
    )
    with pytest.raises(ValueError, match="unknown reasons"):
        load_voice_config(root)


def test_an_empty_line_is_refused(tmp_path: Path) -> None:
    root = _write(
        tmp_path, lambda d: d["languages"]["en"]["lines"]["ai_off"]["default"].append("  ")
    )
    with pytest.raises(ValueError, match="empty line"):
        load_voice_config(root)
