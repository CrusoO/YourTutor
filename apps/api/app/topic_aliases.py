"""Everyday-word aliases for the browser's topic finder (config/topic_aliases.yaml).

The server publishes the table as data (inside GET /context/finder-rules); the browser matches typed
words against it on the device. Nothing a student types comes here. This module only loads and
checks the table, so a bad entry fails the tests rather than reaching a student.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.registries.paths import config_dir

# Lower-case letters and single spaces only: an alias can never hold an email, number, link or name.
_SAY = re.compile(r"^[a-z]+( [a-z]+){0,2}$")
_WORD = re.compile(r"^[a-z]{2,24}$")
_PREFIX = re.compile(r"^[A-Z][A-Z0-9_]*(\.[A-Z0-9_]+)*$")
MAX_ALIASES = 60
MAX_LIST = 24


@dataclass(frozen=True)
class TopicAlias:
    say: tuple[str, ...]
    words: tuple[str, ...]
    skill_prefixes: tuple[str, ...]

    def public(self) -> dict[str, Any]:
        return {
            "say": list(self.say),
            "words": list(self.words),
            "skill_prefixes": list(self.skill_prefixes),
        }


def _strings(
    row: dict[str, Any], key: str, pattern: re.Pattern[str], where: str
) -> tuple[str, ...]:
    raw = row.get(key, [])
    if not isinstance(raw, list) or len(raw) > MAX_LIST:
        raise ValueError(f"{where}: {key} must be a list of at most {MAX_LIST}")
    out: list[str] = []
    for item in raw:
        if not isinstance(item, str) or not pattern.match(item):
            raise ValueError(f"{where}: bad {key} entry {item!r}")
        if item in out:
            raise ValueError(f"{where}: duplicate {key} entry {item!r}")
        out.append(item)
    return tuple(out)


def parse_aliases(rows: Any, language: str) -> list[TopicAlias]:
    if rows is None:
        rows = []
    if not isinstance(rows, list) or len(rows) > MAX_ALIASES:
        raise ValueError(
            f"topic_aliases.yaml [{language}]: aliases must be a list of at most {MAX_ALIASES}"
        )
    out: list[TopicAlias] = []
    said: set[str] = set()
    for index, row in enumerate(rows):
        where = f"topic_aliases.yaml [{language}] #{index + 1}"
        if not isinstance(row, dict):
            raise ValueError(f"{where}: must be a mapping")
        say = _strings(row, "say", _SAY, where)
        words = _strings(row, "words", _WORD, where)
        prefixes = _strings(row, "skill_prefixes", _PREFIX, where)
        if not say:
            raise ValueError(f"{where}: needs at least one 'say'")
        if not words and not prefixes:
            raise ValueError(f"{where}: needs words or skill_prefixes")
        for phrase in say:
            if phrase in said:
                raise ValueError(f"{where}: {phrase!r} is already used by another entry")
            said.add(phrase)
        out.append(TopicAlias(say, words, prefixes))
    return out


def load_topic_aliases(language: str, root: Path | None = None) -> list[TopicAlias]:
    """The aliases for a language; a language with no list yet (hi, ne) uses English."""
    return list(_load((root or config_dir()).as_posix(), language))


@lru_cache(maxsize=16)
def _load(root: str, language: str) -> tuple[TopicAlias, ...]:
    data = yaml.safe_load((Path(root) / "topic_aliases.yaml").read_text(encoding="utf-8")) or {}
    default = str(data.get("default_language", "en"))
    languages = data.get("languages") or {}
    rows = (languages.get(language) or {}).get("aliases")
    if not rows:
        rows = (languages.get(default) or {}).get("aliases")
        language = default
    return tuple(parse_aliases(rows, language))
