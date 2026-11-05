"""Phrase table and the exact matcher: pure functions, no model, no I/O after the config is loaded.

A typed message becomes an action only when, once case, punctuation and filler words are removed,
it equals a configured phrase word for word. That keeps a real question ("what is practice in
physics?") from ever being taken for a command.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from app.actions.registry import REGISTRY
from app.registries.paths import config_dir


@dataclass(frozen=True)
class Phrases:
    """One language's table: normalised phrase -> (action name, argument value or None)."""

    fillers: frozenset[str]
    table: dict[str, tuple[str, str | None]]
    narration: dict[str, str]
    confirm: dict[str, str]
    denied: dict[str, str]


@dataclass(frozen=True)
class ActionConfig:
    max_chars: int
    max_words: int
    default_language: str
    languages: dict[str, Phrases]
    messages: dict[str, dict[str, str]]


@dataclass(frozen=True)
class Match:
    action: str
    value: str | None


def normalise(text: str, fillers: frozenset[str]) -> str:
    """Lower-case, strip punctuation, drop filler words, collapse spaces."""
    folded = unicodedata.normalize("NFKC", text).lower().replace("'", "").replace("’", "")
    # Drop punctuation and symbols by Unicode category, so combining marks in Indic scripts survive.
    spaced = "".join(" " if unicodedata.category(ch)[0] in "PS" else ch for ch in folded)
    return " ".join(word for word in spaced.split() if word not in fillers)


def _build_language(code: str, block: dict) -> Phrases:
    fillers = frozenset(str(word).lower() for word in block.get("fillers", ()))
    table: dict[str, tuple[str, str | None]] = {}
    narration: dict[str, str] = {}
    confirm: dict[str, str] = {}
    denied: dict[str, str] = {}

    def add(phrase: str, action: str, value: str | None) -> None:
        key = normalise(str(phrase), fillers)
        if not key:
            raise ValueError(f"actions.yaml[{code}]: phrase {phrase!r} is empty after filler words")
        if key in table and table[key] != (action, value):
            raise ValueError(f"actions.yaml[{code}]: phrase {phrase!r} is ambiguous")
        table[key] = (action, value)

    for name, row in (block.get("actions") or {}).items():
        spec = REGISTRY.get(name)
        if spec is None:
            raise ValueError(f"actions.yaml[{code}]: {name!r} is not a registered action")
        for phrase in row.get("phrases", ()):
            add(phrase, name, None)
        for value, phrases in (row.get("values") or {}).items():
            if spec.args_for(str(value)) is None:
                raise ValueError(f"actions.yaml[{code}]: {name} cannot take {value!r}")
            for phrase in phrases:
                add(phrase, name, str(value))
        if not row.get("narration"):
            raise ValueError(f"actions.yaml[{code}]: {name} has no narration")
        narration[name] = str(row["narration"])
        if row.get("confirm"):
            confirm[name] = str(row["confirm"])
        if row.get("denied"):
            denied[name] = str(row["denied"])
    return Phrases(fillers, table, narration, confirm, denied)


def load_action_config(root: Path | None = None) -> ActionConfig:
    data = (
        yaml.safe_load(((root or config_dir()) / "actions.yaml").read_text(encoding="utf-8")) or {}
    )
    default = str(data.get("default_language", "en"))
    languages = {code: _build_language(code, block) for code, block in data["languages"].items()}
    if default not in languages:
        raise ValueError("actions.yaml: the default language has no phrase block")
    missing = set(REGISTRY) - set(languages[default].narration)
    if missing:
        raise ValueError(f"actions.yaml: no default-language entry for {sorted(missing)}")
    return ActionConfig(
        max_chars=int(data.get("max_chars", 120)),
        max_words=int(data.get("max_words", 6)),
        default_language=default,
        languages=languages,
        messages={k: dict(v) for k, v in (data.get("messages") or {}).items()},
    )


@lru_cache(maxsize=1)
def action_config() -> ActionConfig:
    return load_action_config()


def phrases_for(config: ActionConfig, language: str) -> Phrases:
    return config.languages.get(language) or config.languages[config.default_language]


def match_utterance(text: str, config: ActionConfig, language: str) -> Match | None:
    """The action a message names, or None. Never guesses: no fuzzy or partial matching."""
    phrases = phrases_for(config, language)
    key = normalise(text, phrases.fillers)
    if not key or len(key.split()) > config.max_words:
        return None
    hit = phrases.table.get(key)
    return Match(*hit) if hit else None
