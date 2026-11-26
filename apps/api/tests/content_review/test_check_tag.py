"""The check tag on review cards: Machine-checked or Needs a person to check."""

# ruff: noqa: F811
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient

from app.config import settings
from app.content.schema import Item, VerificationTier
from app.content_review import service
from tests.conftest import World, auth_header
from tests.content.conftest import content_root  # noqa: F401
from tests.content_review.test_review_api import LIST, root  # noqa: F401

REAL = Path(__file__).resolve().parents[4] / "content"


def _factory_item() -> Item:
    path = next((REAL / "cbse/10/maths/items/factory").rglob("*.yaml"))
    return Item.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def test_labels_are_student_neutral() -> None:
    assert service.CHECK_LABELS == {
        "machine_checked": "Machine-checked",
        "needs_person": "Needs a person to check",
    }
    text = " ".join(service.CHECK_LABELS.values()).lower()
    assert not any(word in text for word in ("cbse", "ncert", "board", "publisher"))


def test_an_intact_factory_item_is_machine_checked() -> None:
    assert service.check_tag(_factory_item()) == "machine_checked"


def test_a_hand_edit_or_missing_record_needs_a_person() -> None:
    item = _factory_item()
    edited = item.model_copy(update={"stem": item.stem.model_copy(update={"en": "Changed?"})})
    assert service.check_tag(edited) == "needs_person"  # record names other content
    assert service.check_tag(item.model_copy(update={"verification": None})) == "needs_person"
    assert service.check_tag(item.model_copy(update={"tier": None})) == "needs_person"


def test_a_model_draft_is_never_machine_checked() -> None:
    item = _factory_item().model_copy(update={"tier": VerificationTier.c, "verification": None})
    assert service.check_tag(item) == "needs_person"
    assert service.tag_counts([item, _factory_item()]) == {"machine_checked": 1, "needs_person": 1}


def test_cards_carry_the_tag_and_the_filter_narrows(
    client: TestClient, world: World, root: Path
) -> None:
    head = auth_header(world.teacher_token)
    cards = client.get(f"{LIST}?status=all&limit=50", headers=head).json()["items"]
    assert cards and all(c["check_tag"] == "needs_person" for c in cards)
    assert {c["check_label"] for c in cards} == {"Needs a person to check"}
    assert "diagram_note" in cards[0]
    both = client.get(f"{LIST}?status=all&limit=50&check=needs_person", headers=head).json()
    assert both["total"] == len(cards)
    none = client.get(f"{LIST}?status=all&limit=50&check=machine_checked", headers=head).json()
    assert none["total"] == 0 and none["items"] == []
    assert client.get(f"{LIST}?check=bogus", headers=head).status_code == 422


@pytest.fixture
def desk() -> Any:
    before = settings.reviewer_desk_enabled
    settings.reviewer_desk_enabled = True
    yield
    settings.reviewer_desk_enabled = before


def test_admin_summary_counts_and_chapter_groups(
    client: TestClient, world: World, root: Path, desk: None
) -> None:
    out = client.get("/staff/review/check-tags", headers=auth_header(world.admin_token))
    assert out.status_code == 200, out.text
    body = out.json()
    assert body["total"]["machine_checked"] == 0 and body["total"]["needs_person"] >= 1
    assert body["labels"]["needs_person"] == "Needs a person to check"
    assert (
        client.get("/staff/review/check-tags", headers=auth_header(world.teacher_token)).status_code
        == 403
    )
    groups = client.get("/staff/review/chapters", headers=auth_header(world.teacher_token)).json()
    assert all(set(g["by_check"]) == {"machine_checked", "needs_person"} for g in groups["groups"])


def test_the_summary_is_closed_when_the_desk_is_off(
    client: TestClient, world: World, root: Path
) -> None:
    settings.reviewer_desk_enabled = False
    res = client.get("/staff/review/check-tags", headers=auth_header(world.admin_token))
    assert res.status_code == 404
