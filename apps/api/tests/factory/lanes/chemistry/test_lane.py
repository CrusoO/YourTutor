"""Lane behaviour: every family renders items that the whole checker stack stamps."""

from __future__ import annotations

import copy
import itertools
import random

import pytest

from app.content.originality import ReferenceIndex
from app.factory.kernel.certify import box_axes
from app.factory.kernel.exact import chash
from app.factory.lanes.chemistry import catalog
from app.factory.lanes.chemistry.core import distinct_wrong
from app.factory.lanes.chemistry.lane import FAMILIES, LANE
from app.factory.lanes.chemistry.misconceptions import TEXT, remedial_skill
from app.factory.pipeline import run
from app.factory.registry import REGISTRY

TEMPLATES = catalog.template_records()


def sample(tpl, n=3, seed=5):
    axes = box_axes(tpl["box"])
    combos = list(itertools.product(*[v for _, v in axes]))
    random.Random(seed).shuffle(combos)
    out = []
    for combo in combos:
        params = {k: c for (k, _), c in zip(axes, combo, strict=True)}
        if LANE.well_posed(tpl, params) is None:
            out.append(params)
            if len(out) == n:
                break
    return out


def test_the_lane_is_registered_and_every_template_names_a_known_family():
    assert REGISTRY.lanes["chemistry"] is LANE
    assert len(TEMPLATES) >= 15
    for tpl in TEMPLATES:
        assert tpl["family"] in FAMILIES and tpl["lane"] == "chemistry"
        assert tpl["family_version"] == FAMILIES[tpl["family"]].version
        assert tpl["syllabus"]["grade"] == 10
        assert tpl["syllabus"]["chapter_ref"].startswith("cbse.10.chemistry.")


@pytest.mark.parametrize("tpl", TEMPLATES, ids=lambda t: t["id"])
def test_sampled_items_pass_every_checker(tpl):
    found = sample(tpl)
    assert found, "no well-posed tuple"
    for params in found:
        ctx = LANE.render(tpl, params)
        ctx.reference_index = ReferenceIndex()
        result = run(ctx)
        assert result.stampable, (params, result.first_failure)
        assert len(ctx.hints) == 3 and len(ctx.options) == 4
        texts = [o["text"] for o in ctx.options]
        assert len(set(texts)) == 4
        assert all(o["procedure"] for o in ctx.options)
        assert LANE.check_student_answer(ctx, ctx.options[0]["text"])
        assert not LANE.check_student_answer(ctx, ctx.options[1]["text"])


def test_a_lane_that_lies_about_the_key_is_refused():
    tpl = next(t for t in TEMPLATES if t["id"] == "TPL.CHEM.PH_CONVERSION")
    ctx = LANE.render(tpl, sample(tpl, 1)[0])
    ctx.reference_index = ReferenceIndex()
    wrong = copy.deepcopy(ctx.options[1]["value"])
    ctx.answer = wrong
    ctx.options[0]["value"] = wrong
    assert run(ctx).rejected


def test_no_student_text_names_a_board_or_a_publisher():
    banned = ("cbse", "ncert", "board", "textbook", "chapter")
    for tpl in TEMPLATES:
        for params in sample(tpl, 4, seed=11):
            ctx = LANE.render(tpl, params)
            blob = " ".join([ctx.stem, *ctx.hints, *ctx.steps, *(o["text"] for o in ctx.options)])
            assert not any(word in blob.lower() for word in banned), blob


@pytest.fixture(scope="module")
def used():
    from app.factory.lanes.chemistry.emit import used_misconceptions

    return used_misconceptions()


def test_every_named_wrong_procedure_has_text_and_a_remedial_skill(used):
    skills = {s for s, _, _ in catalog.SKILLS}
    for skill, mcs in used.items():
        assert skill in skills
        for mc in mcs:
            assert mc in TEXT, mc
            assert remedial_skill(mc) in skills
    assert {mc for mcs in used.values() for mc in mcs} <= set(TEXT)


def test_every_skill_has_a_template_and_the_graph_reaches_class_8_9():
    owned = {t["skill_id"] for t in TEMPLATES}
    ids = {s for s, _, _ in catalog.SKILLS}
    assert owned == ids
    low = {s for s, _, _ in catalog.PREREQS}
    parents = {s: set(p) for s, _, p in catalog.SKILLS}
    for sid in ids:
        seen, stack = set(), [sid]
        while stack:
            for p in parents.get(stack.pop(), ()):
                if p not in seen:
                    seen.add(p)
                    stack.append(p)
        assert seen & low, f"{sid} has no Class 8-9 prerequisite"


def test_options_are_distinct_by_value_and_by_text_for_a_wide_sample():
    for tpl in TEMPLATES:
        for params in sample(tpl, 6, seed=2):
            built = LANE._build(tpl, params)
            picked = distinct_wrong(built.answer, built.key_text, built.wrong, chash)
            assert len(picked) == 3
            assert len({chash(r) for _, r, _ in picked} | {chash(built.answer)}) == 4
