from __future__ import annotations

from app.registries.loaders import LocaleSpec, load_locales_config

_PLACEHOLDER_MARKERS = ("to be filled", "<nepali", "<assamese")


def locale_text_missing(text: str | None) -> bool:
    if text is None:
        return True
    stripped = text.strip()
    if not stripped:
        return True
    lower = stripped.lower()
    return any(marker in lower for marker in _PLACEHOLDER_MARKERS)


def resolve_locale_chain(
    code: str | None,
    *,
    locales: dict[str, LocaleSpec] | None = None,
) -> tuple[str, ...]:
    _, table = load_locales_config() if locales is None else ("en", locales)
    if not code or code not in table:
        code = "en"
    seen: set[str] = set()
    chain: list[str] = []
    current: str | None = code
    while current and current not in seen:
        seen.add(current)
        chain.append(current)
        spec = table.get(current)
        if spec is None:
            break
        current = spec.fallback_chain[0] if spec.fallback_chain else None
    if "en" not in chain:
        chain.append("en")
    return tuple(chain)


def pick_localized_field(fields: dict[str, str | None], preferred: str) -> str:
    for code in resolve_locale_chain(preferred):
        value = fields.get(code)
        if not locale_text_missing(value):
            return str(value)
    return str(fields.get("en") or "")
