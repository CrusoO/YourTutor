from __future__ import annotations

from app.content.schema import LocalizedText

_PLACEHOLDER_MARKERS = (
    "to be filled by reviewer",
    "<Nepali",
    "<Assamese",
)


def is_missing_translation(value: str | None) -> bool:
    if value is None:
        return True
    stripped = value.strip()
    if not stripped:
        return True
    return any(marker.lower() in stripped.lower() for marker in _PLACEHOLDER_MARKERS)


def resolve_text(text: LocalizedText, locale: str) -> str:
    table = {"en": text.en, "ne": text.ne, "as": text.as_}
    requested = table.get(locale, text.en)
    if locale != "en" and is_missing_translation(requested):
        return text.en
    if is_missing_translation(requested):
        return text.en
    return requested or text.en
