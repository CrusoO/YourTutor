from __future__ import annotations

from app.content.gate import item_is_servable, overlay_is_targetable
from app.content.locale import resolve_text
from app.content.schema import Item, LocalizedText, Overlay
from tests.content.conftest import loc, minimal_item


def test_locale_falls_back_to_english() -> None:
    text = LocalizedText.model_validate(loc("Solve"))
    assert resolve_text(text, "ne") == "Solve"
    assert resolve_text(text, "as") == "Solve"
    assert resolve_text(text, "en") == "Solve"


def test_locale_never_empty() -> None:
    text = LocalizedText.model_validate({"en": "Hello", "ne": "", "as": ""})
    assert resolve_text(text, "ne") == "Hello"


def test_draft_hidden_without_flag() -> None:
    item = Item.model_validate(minimal_item())
    assert item_is_servable(item, allow_draft=False) is False
    assert item_is_servable(item, allow_draft=True) is True


def test_approved_always_servable() -> None:
    data = minimal_item(status="approved")
    item = Item.model_validate(data)
    assert item_is_servable(item, allow_draft=False) is True


def test_non_live_overlay_not_targetable_in_prod() -> None:
    overlay = Overlay(
        id="ov",
        curriculum_id="bhutan",
        grade=9,
        chapter="linear_equations",
        skill_ids=["MATH.S1"],
        live=False,
    )
    assert overlay_is_targetable(overlay, allow_draft=False) is False
    assert overlay_is_targetable(overlay, allow_draft=True) is True
