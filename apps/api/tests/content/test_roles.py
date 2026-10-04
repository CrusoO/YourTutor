from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.content.loader import load_path
from app.content.schema import Item, ItemRole
from app.content.templates import load_templates
from app.content.validator import load_bundle, validate_path
from app.db.models import ItemRow
from app.db.session import session_factory
from app.orchestrator.types import CatalogItem
from app.registries.paths import repo_root
from tests.content.conftest import minimal_item, write_yaml

CONTENT = repo_root() / "content"
WORD_SKILL = "MATH.ALG.LIN1.WORD_PROBLEMS"


def test_role_values_follow_architecture_9_5() -> None:
    assert [role.value for role in ItemRole] == [
        "recall",
        "explain",
        "procedure",
        "apply",
        "transfer",
    ]


def test_item_requires_a_role() -> None:
    data = minimal_item()
    data.pop("role", None)
    with pytest.raises(ValidationError, match="role"):
        Item.model_validate(data)


def test_item_rejects_unknown_role() -> None:
    data = minimal_item()
    data["role"] = "memorise"
    with pytest.raises(ValidationError):
        Item.model_validate(data)


def test_validator_reports_item_without_role(content_root: Path) -> None:
    bad = minimal_item("ITEM.NOROLE")
    bad.pop("role")
    write_yaml(content_root / "items" / "norole.yaml", bad)
    report = validate_path(content_root)
    assert any("role" in error for error in report.errors), report.errors


def test_seed_items_all_have_a_role_and_word_problems_are_apply() -> None:
    bundle = load_bundle(CONTENT)
    legacy = [item for item in bundle.items if not item.id.startswith("ITEM.LIN1.R.")]
    assert len(legacy) >= 370
    for item in legacy:
        expected = ItemRole.apply if item.primary_skill == WORD_SKILL else ItemRole.procedure
        assert item.role == expected, item.id


def test_templates_declare_a_role_and_generated_items_inherit_it() -> None:
    templates = {tpl.id: tpl for tpl in load_templates(CONTENT)}
    assert templates
    for tpl in templates.values():
        expected = ItemRole.apply if tpl.skill_id == WORD_SKILL else ItemRole.procedure
        assert tpl.role == expected, tpl.id
    bundle = load_bundle(CONTENT)
    generated = [item for item in bundle.items if item.template_id]
    assert generated
    for item in generated:
        assert item.role == templates[str(item.template_id)].role, item.id


def test_catalog_item_carries_role() -> None:
    row = CatalogItem(
        id="I",
        skill_ids=("S",),
        difficulty=0.3,
        pool="practice",
        status="approved",
        role="apply",
    )
    assert row.role == "apply"
    assert (
        CatalogItem(
            id="J", skill_ids=("S",), difficulty=0.3, pool="practice", status="approved"
        ).role
        == "procedure"
    )


def test_loader_persists_role(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'roles.db'}"
    load_path(CONTENT, database_url=url)
    with session_factory(url)() as session:
        legacy_words = (
            session.query(ItemRow)
            .filter(ItemRow.primary_skill == WORD_SKILL, ~ItemRow.id.like("ITEM.LIN1.R.%"))
            .all()
        )
        assert legacy_words
        assert {row.role for row in legacy_words} == {"apply"}
        all_words = session.query(ItemRow).filter(ItemRow.primary_skill == WORD_SKILL).all()
        assert {row.role for row in all_words} == {"apply", "explain", "transfer"}
        legacy_other = (
            session.query(ItemRow)
            .filter(ItemRow.primary_skill != WORD_SKILL, ~ItemRow.id.like("ITEM.LIN1.R.%"))
            .all()
        )
        assert {row.role for row in legacy_other} == {"procedure"}
