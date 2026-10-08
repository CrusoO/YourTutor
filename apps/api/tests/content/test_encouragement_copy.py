"""G2b: authored encouragement copy: process praise only, within the band word limits."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.content.copy import (
    BANNED_PRAISE_WORDS,
    copy_errors,
    load_encouragement,
    resolve_encouragement,
)
from app.orchestrator.encouragement import TRIGGERS, VARIANTS, pick_variant
from app.registries.loaders import load_grade_bands
from app.registries.paths import content_root

SMALLEST_BAND = min(b.max_words for b in load_grade_bands())


def _words(text: str) -> int:
    return len(text.split())


def test_every_variant_has_authored_english_copy_under_the_smallest_band_limit() -> None:
    copy = load_encouragement(content_root())
    for trigger, ids in VARIANTS.items():
        for variant in ids:
            entry = copy[variant]
            assert entry.trigger == trigger
            assert entry.text.en.strip().endswith(".")
            assert _words(entry.text.en) <= SMALLEST_BAND, variant


def test_no_person_praise_and_no_filler_in_any_variant() -> None:
    for entry in load_encouragement(content_root()).values():
        lowered = entry.text.en.lower()
        for word in BANNED_PRAISE_WORDS:
            assert word not in lowered, (entry.id, word)
        assert "!" not in entry.text.en, entry.id


def test_every_variant_is_a_draft_with_reviewer_placeholders() -> None:
    for entry in load_encouragement(content_root()).values():
        assert entry.status == "draft"
        assert "to be filled" in (entry.text.ne or "")


def test_the_seed_copy_validates() -> None:
    assert copy_errors(content_root()) == []


def test_pick_variant_cycles_deterministically() -> None:
    for trigger in TRIGGERS:
        ids = VARIANTS[trigger]
        assert [pick_variant(trigger, n) for n in range(len(ids) * 2)] == list(ids) * 2


def test_resolve_uses_the_students_language_and_falls_back_to_english() -> None:
    en = resolve_encouragement("hard_success", "checked_the_answer", "en")
    assert en and en == resolve_encouragement("hard_success", "checked_the_answer", "ne")
    assert resolve_encouragement("hard_success", "no_such_variant", "en") is None


def _write(tmp_path: Path, body: str) -> Path:
    folder = tmp_path / "copy"
    folder.mkdir()
    (folder / "encouragement.yaml").write_text(body, encoding="utf-8")
    return tmp_path


def _variant(variant: str, trigger: str, text: str) -> str:
    return (
        f"  - id: {variant}\n    trigger: {trigger}\n    status: draft\n"
        f'    text: {{en: "{text}", ne: "<Nepali - to be filled by reviewer>"}}\n'
    )


def _full(missing: str | None = None, override: dict[str, str] | None = None) -> str:
    out = "variants:\n"
    for trigger, ids in VARIANTS.items():
        for variant in ids:
            if variant == missing:
                continue
            text = (override or {}).get(variant, "You kept going and it worked.")
            out += _variant(variant, trigger, text)
    return out


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"kept_trying": "You are so smart."}, "smart"),
        ({"kept_trying": "You are a genius at this."}, "genius"),
        ({"kept_trying": "Well done!"}, "exclamation"),
        ({"kept_trying": "word " * 40}, "words"),
    ],
)
def test_the_validator_rejects_person_praise_filler_and_long_text(
    tmp_path: Path, override: dict[str, str], message: str
) -> None:
    errors = copy_errors(_write(tmp_path, _full(override=override)))
    assert any(message in e for e in errors), errors


def test_the_validator_requires_every_variant_the_policy_can_pick(tmp_path: Path) -> None:
    errors = copy_errors(_write(tmp_path, _full(missing="steady_work")))
    assert any("steady_work" in e for e in errors), errors


def test_the_validator_rejects_a_variant_under_the_wrong_trigger(tmp_path: Path) -> None:
    body = _full().replace("trigger: recovery", "trigger: session_end", 1)
    errors = copy_errors(_write(tmp_path, body))
    assert any("trigger" in e for e in errors), errors


def test_a_copy_folder_without_the_file_is_an_error_but_no_folder_is_fine(tmp_path: Path) -> None:
    assert copy_errors(tmp_path) == []
    (tmp_path / "copy").mkdir()
    assert any("encouragement.yaml" in e for e in copy_errors(tmp_path))


def test_action_extras_get_the_authored_text() -> None:
    from app.content.copy import with_encouragement_text

    extras = {"encouragement": {"trigger": "recovery", "variant": "kept_trying"}, "other": 1}
    out = with_encouragement_text(extras, "en")
    praise = out["encouragement"]
    assert isinstance(praise, dict)
    assert praise["text"] == "You kept going after a tough one, and it paid off."
    original = extras["encouragement"]
    assert isinstance(original, dict) and "text" not in original
    assert out["other"] == 1
    assert with_encouragement_text({"x": 1}, "en") == {"x": 1}
