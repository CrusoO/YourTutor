"""Authored tutor copy that is not an item: encouragement (G2b).

`content/copy/encouragement.yaml` holds one text per variant id the policy can pick
(`app.orchestrator.encouragement.VARIANTS`). The validator checks that every variant exists, sits
under its trigger, stays within the smallest grade-band word limit and contains no person-praise
or filler. Texts are drafts; other languages fall back to English until a reviewer fills them.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from app.content.locale import is_missing_translation
from app.content.schema import LocalizedText
from app.orchestrator.encouragement import VARIANTS
from app.registries.grade_bands import _cached_bands

# Praise that targets the person, not the strategy or effort (TUTOR_CONSTITUTION rule 16).
BANNED_PRAISE_WORDS = (
    "smart",
    "clever",
    "genius",
    "gifted",
    "talented",
    "brilliant",
    "so good at",
    "natural at",
    "intelligent",
)

FILE = Path("copy") / "encouragement.yaml"


@dataclass(frozen=True)
class Encouragement:
    id: str
    trigger: str
    status: str
    text: LocalizedText


def load_encouragement(root: Path) -> dict[str, Encouragement]:
    path = root / FILE
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out: dict[str, Encouragement] = {}
    for row in raw.get("variants") or []:
        out[str(row["id"])] = Encouragement(
            id=str(row["id"]),
            trigger=str(row["trigger"]),
            status=str(row.get("status") or "draft"),
            text=LocalizedText.model_validate(row["text"]),
        )
    return out


def copy_errors(root: Path) -> list[str]:
    path = root / FILE
    if not (root / FILE.parent).is_dir():
        return []  # content roots without tutor copy (small test trees) have nothing to check
    if not path.is_file():
        return [f"{FILE.as_posix()} is missing"]
    try:
        copy = load_encouragement(root)
    except Exception as exc:  # noqa: BLE001
        return [f"{FILE.as_posix()} could not be read: {exc}"]
    limit = min(band.max_words for band in _cached_bands())
    errors: list[str] = []
    for trigger, ids in VARIANTS.items():
        for variant in ids:
            entry = copy.get(variant)
            if entry is None:
                errors.append(f"{FILE.as_posix()}: variant {variant!r} for {trigger} is missing")
                continue
            if entry.trigger != trigger:
                errors.append(
                    f"{variant}: trigger is {entry.trigger!r}, the policy uses {trigger!r}"
                )
            text = entry.text.en
            if len(text.split()) > limit:
                errors.append(
                    f"{variant}: {len(text.split())} words, the smallest band allows {limit}"
                )
            if "!" in text:
                errors.append(f"{variant}: no exclamation marks (filler praise)")
            lowered = text.lower()
            for word in BANNED_PRAISE_WORDS:
                if word in lowered:
                    errors.append(f"{variant}: person praise ({word!r}); name the strategy instead")
    return errors


@lru_cache(maxsize=1)
def _seed_copy() -> dict[str, Encouragement]:
    from app.registries.paths import content_root

    return load_encouragement(content_root())


def with_encouragement_text(extras: dict[str, object], locale: str) -> dict[str, object]:
    """Copy of an action's extras with the authored text added to `encouragement`, if any."""
    praise = extras.get("encouragement")
    if not isinstance(praise, dict):
        return extras
    text = resolve_encouragement(str(praise.get("trigger")), str(praise.get("variant")), locale)
    return {**extras, "encouragement": {**praise, "text": text}}


def resolve_encouragement(trigger: str, variant: str, locale: str) -> str | None:
    """The authored text for a variant in the student's language (English when not translated)."""
    entry = _seed_copy().get(variant)
    if entry is None or entry.trigger != trigger:
        return None
    wanted = (
        getattr(entry.text, "as_" if locale == "as" else locale, None)
        if locale in {"ne", "as"}
        else None
    )
    if wanted and not is_missing_translation(wanted):
        return str(wanted)
    return entry.text.en
