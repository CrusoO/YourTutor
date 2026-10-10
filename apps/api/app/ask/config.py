"""Ask settings from `config/ask.yaml` (thresholds are data, not code)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from app.registries.paths import config_dir


@dataclass(frozen=True)
class AskConfig:
    top_k: int = 4
    keyword_weight: float = 0.6
    vector_weight: float = 0.4
    answer_min: float = 0.35
    clarify_min: float = 0.25
    ambiguity_margin: float = 0.04
    choices: int = 3
    max_question_chars: int = 300


def load_ask_config(root: Path | None = None) -> AskConfig:
    data = yaml.safe_load(((root or config_dir()) / "ask.yaml").read_text(encoding="utf-8")) or {}
    search, gate, limits = data.get("search", {}), data.get("gate", {}), data.get("limits", {})
    cfg = AskConfig(
        top_k=int(search.get("top_k", 4)),
        keyword_weight=float(search.get("keyword_weight", 0.6)),
        vector_weight=float(search.get("vector_weight", 0.4)),
        answer_min=float(gate.get("answer_min", 0.35)),
        clarify_min=float(gate.get("clarify_min", 0.25)),
        ambiguity_margin=float(gate.get("ambiguity_margin", 0.04)),
        choices=int(gate.get("choices", 3)),
        max_question_chars=int(limits.get("max_question_chars", 300)),
    )
    if not 0 < cfg.clarify_min < cfg.answer_min <= 1:
        raise ValueError("ask.yaml: need 0 < clarify_min < answer_min <= 1")
    return cfg


@lru_cache(maxsize=1)
def ask_config() -> AskConfig:
    return load_ask_config()


@dataclass(frozen=True)
class SafetyLists:
    injection_patterns: tuple[str, ...]
    distress_terms: tuple[str, ...]
    solve_intent_phrases: tuple[str, ...]
    meaning_terms: tuple[str, ...] = ()
    item_reference_patterns: tuple[str, ...] = ()


def load_safety(language: str, root: Path | None = None) -> SafetyLists:
    data = yaml.safe_load(((root or config_dir()) / "ask.yaml").read_text(encoding="utf-8")) or {}
    safety = data.get("safety", {})
    by_language = safety.get("languages", {})
    row = by_language.get(language) or by_language.get(safety.get("default_language", "en")) or {}
    return SafetyLists(
        injection_patterns=tuple(row.get("injection_patterns", ())),
        distress_terms=tuple(row.get("distress_terms", ())),
        solve_intent_phrases=tuple(row.get("solve_intent_phrases", ())),
        meaning_terms=tuple(row.get("meaning_terms", ())),
        item_reference_patterns=tuple(row.get("item_reference_patterns", ())),
    )


def message(key: str, language: str, root: Path | None = None) -> str:
    """An authored Ask reply in the student's language, else the default language."""
    data = yaml.safe_load(((root or config_dir()) / "ask.yaml").read_text(encoding="utf-8")) or {}
    table = data.get("messages", {})
    default = data.get("safety", {}).get("default_language", "en")
    return str((table.get(language) or {}).get(key) or (table.get(default) or {}).get(key) or "")
