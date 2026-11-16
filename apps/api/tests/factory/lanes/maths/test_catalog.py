# ruff: noqa: E501
"""The skill graph, templates and wording rules of the Class 10 maths lane."""

import re
from collections import defaultdict

import pytest
import yaml

from app.content.leak import hint_leaks_answer
from app.factory.kernel.certify import box_size
from app.factory.lanes.maths import catalog
from app.factory.lanes.maths.emit import render_files
from app.factory.lanes.maths.lane import FAMILIES, LANE
from app.factory.lanes.maths.misconceptions import TEXT

from .support import CONTENT, TEMPLATES, tuples

SKILLS = {s["id"]: s for s in catalog.skill_records()}
CLASS10 = {t["skill_id"] for t in TEMPLATES}


def _chapter_skills(ref: str) -> set[str]:
    return {t["skill_id"] for t in TEMPLATES if t["syllabus"]["chapter_ref"] == ref}


def test_skill_counts_per_launch_chapter():
    quad = _chapter_skills("cbse.10.maths.ch04")
    ap = _chapter_skills("cbse.10.maths.ch05")
    trig = (
        _chapter_skills("cbse.10.maths.ch09")
        | _chapter_skills("cbse.10.maths.ch10")
        | _chapter_skills("cbse.10.maths.ch11")
    )
    assert 8 <= len(quad) <= 15 and 8 <= len(ap) <= 15 and 8 <= len(trig) <= 15
    assert len(_chapter_skills("cbse.10.maths.ch11")) == 5  # honest: below 8 for the chapter alone


def test_prerequisites_exist_are_acyclic_and_reach_classes_8_and_9():
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

    def reaches_lower_grades(sid: str) -> bool:
        seen, stack = set(), [sid]
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            if max(SKILLS[node]["grade_band"]) <= 9:
                return True
            stack.extend(SKILLS[node]["prerequisites"])
        return False

    for sid in CLASS10:
        assert reaches_lower_grades(sid), f"{sid} has no Class 8-9 prerequisite"


def test_every_option_procedure_is_a_named_misconception_with_text():
    used = {m for v in catalog.used_misconceptions().values() for m in v}
    assert used <= set(TEXT)
    for sid, skill in SKILLS.items():
        assert all(m in TEXT for m in skill["misconceptions"]), sid
    for mc, (title, why) in TEXT.items():
        assert mc.startswith("MC.") and len(title) > 5 and len(why) > 15


def test_templates_are_consistent():
    ids = [t["id"] for t in TEMPLATES]
    assert len(ids) == len(set(ids)) == len(TEMPLATES)
    for t in TEMPLATES:
        assert t["schema"] == "factory-template/1" and t["lane"] == "maths_c10"
        assert FAMILIES[t["family"]].version == t["family_version"], t["id"]
        assert t["syllabus"]["allowed_methods"] and t["syllabus"]["forbidden_content"]
        assert t["syllabus"]["grade"] == 10 and t["form"]["marks"] in (1, 2, 3, 4)
        assert box_size(t["box"]) <= 200_000  # certified exhaustively, never sampled


def test_marks_forms_are_covered_per_chapter():
    marks = defaultdict(set)
    for t in TEMPLATES:
        marks[t["syllabus"]["chapter_ref"]].add(t["form"]["marks"])
    assert marks["cbse.10.maths.ch04"] == {1, 2, 3, 4}
    assert marks["cbse.10.maths.ch05"] == {1, 2, 3, 4}
    assert {1, 2, 3, 4} <= marks["cbse.10.maths.ch11"] | marks["cbse.10.maths.ch09"]


def test_files_on_disk_match_the_catalog():
    for rel, text in render_files().items():
        path = CONTENT / rel
        assert path.is_file(), f"{rel} is missing: run python -m app.factory.lanes.maths.emit"
        assert yaml.safe_load(path.read_text(encoding="utf-8")) == yaml.safe_load(text), rel


def test_overlays_are_not_live():
    for path in (CONTENT / "overlays").glob("*.yaml"):
        assert yaml.safe_load(path.read_text(encoding="utf-8"))["live"] is False


SHORTCUT = re.compile(r"across|flip|change the sign|changes sign|transpos|swap sides|cross", re.I)


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda t: t["short"])
def test_wording_rules_on_sampled_items(template):
    """Hint ladder: inverse operations, no shortcut, answer never revealed."""
    for params in tuples(template, 6):
        built = LANE._build(template, params)
        assert len(built.hints) == 3 and len(built.steps) >= 2
        for text in [*built.hints, *built.steps]:
            assert not SHORTCUT.search(text), f"shortcut wording: {text}"
        for hint in built.hints:
            for token in built.tokens:
                assert not hint_leaks_answer(hint, token), f"hint reveals {token}: {hint}"
        ctx = LANE.render(template, params)
        wrong = [o for o in ctx.options if o["id"] != "key"]
        assert len(wrong) == 3 and all(o["procedure"] in TEXT for o in wrong)
        assert len({str(o["value"]) for o in ctx.options}) == 4


def test_hint_one_varies_within_every_skill():
    by_skill = defaultdict(set)
    for t in TEMPLATES:
        for params in tuples(t, 12):
            by_skill[t["skill_id"]].add(LANE._build(t, params).hints[0])
    assert all(len(v) >= 3 for v in by_skill.values()), {
        k: len(v) for k, v in by_skill.items() if len(v) < 3
    }


def test_checking_a_typed_answer():
    t = next(x for x in TEMPLATES if x["short"] == "C10.QUAD.FACTOR_MONIC")
    ctx = LANE.render(t, {"a": 1, "p1": -2, "q1": 1, "p2": 3, "q2": 1})
    assert LANE.check_student_answer(ctx, "3, -2") and LANE.check_student_answer(
        ctx, "x = -2 or x = 3"
    )
    assert not LANE.check_student_answer(ctx, "3") and not LANE.check_student_answer(ctx, "abc")
    t = next(x for x in TEMPLATES if x["short"] == "C10.TRIG.HD_HEIGHT")
    ctx = LANE.render(t, {"ang": 60, "k": 10, "kind": "surd", "ctx": 0})
    assert ctx.answer["value"] == "10√3"
    assert LANE.check_student_answer(ctx, "10 sqrt3") and not LANE.check_student_answer(ctx, "10")
