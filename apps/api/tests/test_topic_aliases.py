"""config/topic_aliases.yaml: checked on load, no personal data, no invented translations."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from app.registries.paths import config_dir
from app.topic_aliases import load_topic_aliases, parse_aliases


def test_the_shipped_table_loads_and_has_the_everyday_words() -> None:
    aliases = load_topic_aliases("en")
    said = {phrase for a in aliases for phrase in a.say}
    assert {
        "algebra",
        "equations",
        "linear equations",
        "quadratic",
        "polynomial",
        "maths",
        "math",
        "numbers",
        "geometry",
        "trigonometry",
        "trig",
        "progression",
        "ap",
    } <= said
    assert len(said) == sum(len(a.say) for a in aliases)  # no phrase in two entries


def test_the_shipped_table_has_no_personal_data_shapes() -> None:
    blob = " ".join([*(p for a in load_topic_aliases("en") for p in (*a.say, *a.words))])
    assert not re.search(r"[@/\d]", blob)  # no email, link or number can ride in an alias


def test_hindi_and_nepali_lists_are_empty_with_a_todo_not_invented() -> None:
    text = (config_dir() / "topic_aliases.yaml").read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    assert data["languages"]["hi"]["aliases"] == []
    assert data["languages"]["ne"]["aliases"] == []
    assert "TODO" in text


@pytest.mark.parametrize(
    "row",
    [
        {"say": ["Algebra"], "words": ["algebra"]},  # upper case
        {"say": ["a@b.co"], "words": ["algebra"]},  # an email shape
        {"say": ["call 98765"], "words": ["algebra"]},  # digits
        {"say": ["one two three four"], "words": ["algebra"]},  # too many words
        {"say": [], "words": ["algebra"]},  # nothing to say
        {"say": ["algebra"]},  # points at nothing
        {"say": ["algebra"], "skill_prefixes": ["math.alg"]},  # prefix must be a skill id shape
        {"say": ["algebra"], "words": ["algebra", "algebra"]},  # duplicate
        {"say": ["algebra"], "words": ["x" * 40]},  # too long
    ],
)
def test_bad_entries_are_refused(row: dict) -> None:
    with pytest.raises(ValueError):
        parse_aliases([row], "en")


def test_the_same_phrase_in_two_entries_is_refused() -> None:
    rows = [{"say": ["algebra"], "words": ["algebra"]}, {"say": ["algebra"], "words": ["equation"]}]
    with pytest.raises(ValueError):
        parse_aliases(rows, "en")


def test_an_alias_table_in_another_folder_is_read_from_there(tmp_path: Path) -> None:
    (tmp_path / "topic_aliases.yaml").write_text(
        "default_language: en\nlanguages:\n  en:\n    aliases:\n"
        "      - {say: [shapes], words: [geometry]}\n",
        encoding="utf-8",
    )
    got = load_topic_aliases("en", root=tmp_path)
    assert [a.say for a in got] == [("shapes",)]
