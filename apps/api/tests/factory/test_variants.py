"""Derived templates: diagnostic, explain and checkpoint items through the real CLI."""

import copy
from pathlib import Path

import pytest
import yaml

from app.content.schema import Item
from app.factory.cli import main
from app.factory.lanes.maths_quadratic import TEMPLATE
from app.factory.variants import derive, one_per_skill

SMALL = copy.deepcopy(TEMPLATE)
SMALL["box"] = {"a": {"choices": [1, 2]}, "r1": {"min": -3, "max": 3}, "r2": {"min": -3, "max": 3}}


def test_derive_keeps_the_model_and_changes_id_and_variant() -> None:
    out = derive(SMALL, "diagnostic")
    assert out["id"] == SMALL["id"] + ".DX" and out["variant"] == "diagnostic"
    assert out["box"] == SMALL["box"] and "variant" not in SMALL


def test_derive_restricts_a_physics_style_form_axis_to_mcq() -> None:
    template = {**SMALL, "box": {**SMALL["box"], "form": {"choices": ["num2", "mcq1", "case4"]}}}
    assert derive(template, "explain")["box"]["form"]["choices"] == ["mcq1"]


def test_one_per_skill_is_stable_and_skips_variants() -> None:
    other = {**SMALL, "id": "A.FIRST", "skill_id": SMALL["skill_id"]}
    picked = one_per_skill([SMALL, other, derive(SMALL, "explain")])
    assert [t["id"] for t in picked] == ["A.FIRST"]


@pytest.mark.parametrize(
    ("kind", "pool", "role"),
    [
        ("diagnostic", "diagnostic", None),
        ("checkpoint", "checkpoint", None),
        ("explain", "practice", "explain"),
    ],
)
def test_variant_is_certified_and_stamped_into_its_pool(tmp_path: Path, kind, pool, role) -> None:
    root = tmp_path / "content"
    tpl = tmp_path / "v.yaml"
    tpl.write_text(yaml.safe_dump(derive(SMALL, kind)), encoding="utf-8")
    base = ["--root", str(root)]
    assert main([*base, "certify", str(tpl), "--no-reference-index"]) == 0
    assert main([*base, "stamp", str(tpl), "--count", "3", "--no-reference-index"]) == 0
    files = sorted((root / "items" / "factory" / "maths").glob("*.yaml"))
    assert len(files) == 3
    for path in files:
        item = Item.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        assert item.pool.value == pool and item.tier is not None and item.tier.value == "A"
        assert item.id.endswith(
            "." + ("dx" if kind == "diagnostic" else kind[:1] + ("x" if kind == "explain" else "p"))
        )
        if role:
            assert item.role.value == role
            assert "A classmate says the answer is" in item.stem.en
