"""How Brownie sounds around a model reply: register, length and what it says when it cannot answer.

Pure and deterministic. The model may phrase a reply; this module decides how long it may be, what
tone to ask for, and what to say instead when there is no reply. Authored words live in
`config/conversation.yaml`; limits and tone come from the learner's grade band
(`config/grade_bands.yaml`, docs/TUTOR_CONSTITUTION.md rules 14 and 17).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.registries.grade_bands import band_for_grade
from app.registries.paths import config_dir

DEFAULT_REGISTER = "default"
FALLBACK_REASONS = ("unavailable", "ai_off", "no_consent")
# Where unavailable() reasons from the explain service land. Anything unlisted is "unavailable".
_REASON_TO_FALLBACK = {"off": "ai_off", "consent": "no_consent"}
# Without a grade there is no band: use a middle limit rather than the longest or shortest.
UNKNOWN_GRADE_MAX_WORDS = 60
SENTENCE_END = re.compile(r"(?<=[.!?।])\s+")


@dataclass(frozen=True)
class Register:
    """The tone and length one learner gets, taken from their grade band."""

    key: str  # which authored lines: "primary" or "default"
    band_id: str
    max_words: int
    style: str


@dataclass(frozen=True)
class VoiceConfig:
    default_language: str
    register_for_band: dict[str, str]
    lines: dict[
        str, dict[str, dict[str, tuple[str, ...]]]
    ]  # language -> reason -> register -> lines
    offers: dict[str, dict[str, str]]  # language -> offer id -> label
    offers_for: dict[str, dict[str, tuple[str, ...]]]  # language -> reason -> offer ids


def load_voice_config(root: Path | None = None) -> VoiceConfig:
    path = (root or config_dir()) / "conversation.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    default = str(data.get("default_language", "en"))
    languages = data.get("languages") or {}
    if default not in languages:
        raise ValueError("conversation.yaml: the default language has no block")
    lines: dict[str, dict[str, dict[str, tuple[str, ...]]]] = {}
    offers: dict[str, dict[str, str]] = {}
    offers_for: dict[str, dict[str, tuple[str, ...]]] = {}
    for code, block in languages.items():
        lines[code] = {
            reason: {reg: tuple(str(x) for x in rows) for reg, rows in (by_reg or {}).items()}
            for reason, by_reg in (block.get("lines") or {}).items()
        }
        offers[code] = {str(k): str(v) for k, v in (block.get("offers") or {}).items()}
        offers_for[code] = {
            str(reason): tuple(str(x) for x in ids)
            for reason, ids in (block.get("offers_for") or {}).items()
        }
    config = VoiceConfig(
        default_language=default,
        register_for_band={
            str(k): str(v) for k, v in (data.get("register_for_band") or {}).items()
        },
        lines=lines,
        offers=offers,
        offers_for=offers_for,
    )
    _validate(config)
    return config


def _validate(config: VoiceConfig) -> None:
    base = config.default_language
    for reason in FALLBACK_REASONS:
        rows = config.lines[base].get(reason, {})
        if not rows.get(DEFAULT_REGISTER):
            raise ValueError(f"conversation.yaml: no default-register line for {reason!r}")
        if any(not line.strip() for lines in rows.values() for line in lines):
            raise ValueError(f"conversation.yaml: an empty line under {reason!r}")
        for offer in config.offers_for[base].get(reason, ()):
            if offer not in config.offers[base]:
                raise ValueError(f"conversation.yaml: {reason!r} offers unknown {offer!r}")
    extra = set(config.lines[base]) - set(FALLBACK_REASONS)
    if extra:
        raise ValueError(f"conversation.yaml: unknown reasons {sorted(extra)}")


@lru_cache(maxsize=1)
def voice_config() -> VoiceConfig:
    return load_voice_config()


def register_for_grade(grade: int | None, config: VoiceConfig | None = None) -> Register:
    """The register for a grade; a missing grade gets the default tone and a middle word limit."""
    config = config or voice_config()
    band = band_for_grade(grade) if grade is not None else None
    if band is None:
        return Register(DEFAULT_REGISTER, "unknown", UNKNOWN_GRADE_MAX_WORDS, "")
    key = config.register_for_band.get(band.id, DEFAULT_REGISTER)
    return Register(key, band.id, band.max_words, band.style)


def trim_to_words(text: str, max_words: int) -> str:
    """At most `max_words` words, cut at the end of a sentence; never in the middle of one.

    If the first sentence alone is too long it is cut at a word and ends with an ellipsis.
    """
    cleaned = text.strip()
    if max_words <= 0 or len(cleaned.split()) <= max_words:
        return cleaned
    kept: list[str] = []
    used = 0
    for sentence in SENTENCE_END.split(cleaned):
        count = len(sentence.split())
        if used + count > max_words:
            break
        kept.append(sentence)
        used += count
    if kept:
        return " ".join(kept)
    return " ".join(cleaned.split()[:max_words]).rstrip(",;:") + "…"


def fallback_reason(unavailable_reason: str) -> str:
    """Which authored fallback fits an `unavailable` reason from the explain service."""
    return _REASON_TO_FALLBACK.get(unavailable_reason, "unavailable")


def fallback_turn(
    unavailable_reason: str,
    register: Register,
    language: str = "en",
    turn_index: int = 0,
    config: VoiceConfig | None = None,
) -> dict[str, Any]:
    """What Brownie says when it cannot answer: an honest line and the next choices.

    The line cycles with `turn_index` so it does not repeat word for word. It never names the
    student's words and never blames them.
    """
    config = config or voice_config()
    reason = fallback_reason(unavailable_reason)
    code = language if language in config.lines else config.default_language
    by_register = config.lines[code].get(reason) or config.lines[config.default_language][reason]
    rows = by_register.get(register.key) or by_register[DEFAULT_REGISTER]
    labels = config.offers.get(code) or config.offers[config.default_language]
    ids = (
        config.offers_for.get(code, {}).get(reason)
        or config.offers_for[config.default_language][reason]
    )
    return {
        "reason": reason,
        "text": rows[turn_index % len(rows)],
        "offers": [{"id": offer, "label": labels[offer]} for offer in ids if offer in labels],
    }
