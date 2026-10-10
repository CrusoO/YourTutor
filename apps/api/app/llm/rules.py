"""Tone and moderation word lists, from `config/llm_rules.yaml`."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from app.registries.paths import config_dir


@dataclass(frozen=True)
class LlmRules:
    shaming_phrases: tuple[str, ...]
    blocked_terms: tuple[str, ...]


def load_llm_rules(root: Path | None = None) -> LlmRules:
    data = yaml.safe_load(((root or config_dir()) / "llm_rules.yaml").read_text(encoding="utf-8"))
    return LlmRules(
        shaming_phrases=tuple(str(x).lower() for x in data.get("shaming_phrases") or ()),
        blocked_terms=tuple(str(x).lower() for x in data.get("blocked_terms") or ()),
    )


@lru_cache(maxsize=1)
def default_rules() -> LlmRules:
    return load_llm_rules()
