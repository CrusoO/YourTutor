# ruff: noqa: E501
"""Skill graph, templates and wording rules of the Class 12 maths lane."""

import re

import pytest
import yaml

from app.content.leak import hint_leaks_answer
from app.factory.kernel.certify import box_size
from app.factory.lanes.maths_c12 import catalog
from app.factory.lanes.maths_c12.core import FAMILIES
from app.factory.lanes.maths_c12.emit import render_files
from app.factory.lanes.maths_c12.lane import LANE

from .support import CONTENT, TEMPLATES, tuples

SKILLS = {s["id"]: s for s in catalog.skill_records()}


def test_model_and_chapter_counts():
    assert 20 <= len(TEMPLATES) <= 30
    assert {t["syllabus"]["chapter_ref"] for t in TEMPLATES} == set(catalog.CHAPTERS)


def test_prerequisites_exist_and_are_acyclic():
    for sid, skill in SKILLS.items():
        for pre in skill["prerequisites"]:
            assert pre in SKILLS, f"{sid} needs unknown {pre}"
    state: dict[str, int] = {}

    def visit(node: str) -> None:
        assert state.get(node) != 1, f"cycle at {node}"
        if state.get(node) == 2:
            return
        state[node] = 1
        for pre in SKILLS[node]["prerequisites"]:
            visit(pre)
        state[node] = 2

    for sid in SKILLS:
        visit(sid)


def test_templates_are_consistent():
    ids = [t["id"] for t in TEMPLATES]
    assert len(ids) == len(set(ids))
    for t in TEMPLATES:
        assert t["schema"] == "factory-template/1" and t["lane"] == "maths_c12"
        assert FAMILIES[t["family"]].version == t["family_version"]
        assert t["syllabus"]["allowed_methods"] and t["syllabus"]["grade"] == 12
        assert box_size(t["box"]) <= 200_000


def test_files_on_disk_match_the_catalog():
    for rel, text in render_files().items():
        path = CONTENT / rel
        assert path.is_file(), f"{rel} missing: run python -m app.factory.lanes.maths_c12.emit"
        assert yaml.safe_load(path.read_text(encoding="utf-8")) == yaml.safe_load(text), rel


def test_overlays_are_not_live():
    for path in (CONTENT / "overlays").glob("*.yaml"):
        assert yaml.safe_load(path.read_text(encoding="utf-8"))["live"] is False


SHORTCUT = re.compile(r"across|flip|change the sign|changes sign|swap sides", re.I)
BANNED_NAMES = re.compile(r"ncert|cbse|\bboard\b|publisher|textbook", re.I)


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda t: t["short"])
def test_wording_rules_on_sampled_items(template):
    for params in tuples(template, 8):
        built = LANE._build(template, params)
        assert len(built.hints) == 3 and len(built.steps) >= 2
        for text in [built.stem, *built.hints, *built.steps]:
            assert not BANNED_NAMES.search(text), text
        for (
            text
        ) in built.hints:  # the equation shortcut rule is about hints; matrices may "change signs"
            assert not SHORTCUT.search(text), text
        for hint in built.hints[:2]:
            for token in built.tokens:
                assert not hint_leaks_answer(hint, token), f"hint reveals {token}: {hint}"
        ctx = LANE.render(template, params)
        wrong = [o for o in ctx.options if o["id"] != "key"]
        assert len(wrong) == 3 and all(o["procedure"].startswith("MC.C12.") for o in wrong)
        assert len({str(o["value"]) for o in ctx.options}) == 4
        assert len({o["text"] for o in ctx.options}) == 4


def test_typed_answer_check():
    t = next(x for x in TEMPLATES if x["short"] == "C12.DET.VALUE")
    ctx = LANE.render(t, tuples(t, 1)[0])
    key = next(o["text"] for o in ctx.options if o["id"] == "key")
    assert LANE.check_student_answer(ctx, key) and not LANE.check_student_answer(ctx, "zzz")
