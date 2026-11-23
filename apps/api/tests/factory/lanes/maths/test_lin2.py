# ruff: noqa: E501
"""Pair of Linear Equations in Two Variables lane: misconception table, reference solvers, families."""

from fractions import Fraction

import pytest

from app.content.language import lint_item_texts
from app.content.leak import hint_leaks_answer
from app.factory.kernel.exact import chash
from app.factory.lanes.maths.lane import FAMILIES, LANE
from app.factory.lanes.maths.misconceptions import TEXT
from app.factory.lanes.maths.misconceptions_pair import PAIR_TEXT
from app.factory.lanes.maths.reference import lin2 as ref

from .support import TEMPLATES, tuples

F = Fraction


def test_pair_table_is_merged_and_well_formed():
    assert len(PAIR_TEXT) >= 30
    assert set(PAIR_TEXT) <= set(TEXT)
    for mc, (title, why) in PAIR_TEXT.items():
        assert mc.startswith("MC.PAIR.") and mc == mc.upper()
        assert len(title) > 5 and len(why) > 15
        for word in ("CBSE", "NCERT"):
            assert word not in title + why


def test_the_required_slips_are_named():
    names = " ".join(PAIR_TEXT)
    for idea in (
        "ELIM_SIGN_SLIP",  # sign slip when eliminating
        "ELIM_ADD_NOT_SUBTRACT",  # adding instead of subtracting
        "ONE_VARIABLE_ONLY",  # solving for only one variable
        "XY_SWAPPED",  # mixing up x and y
        "ELIM_DIVIDED_ONE_TERM",  # dividing only one term
        "WORD_",  # mis-set word-problem equation
    ):
        assert idea in names


# ---------------------------------------------------------------- reference solvers


@pytest.mark.parametrize(
    "raw, want",
    [
        ([[2, 3, 12], [1, -1, 1]], (F(3), F(2))),
        ([[1, 0, 4], [2, 1, 3]], (F(4), F(-5))),  # a zero coefficient
        ([[0, 2, 6], [3, -1, 0]], (F(1), F(3))),
        ([[2, 4, 3], [4, -2, 1]], (F(1, 2), F(1, 2))),  # simple fractions
    ],
)
def test_every_solver_agrees_with_hand_values(raw, want):
    pair = ref.eqs(raw)
    for name, solver in ref.SOLVERS.items():
        assert solver(pair) == want, name


def test_solvers_refuse_a_singular_pair():
    pair = ref.eqs([[1, 2, 3], [2, 4, 6]])
    for name, solver in ref.SOLVERS.items():
        with pytest.raises(ValueError):
            solver(pair)
        assert name


@pytest.mark.parametrize(
    "raw, kind",
    [
        ([[1, 2, 3], [3, 7, 4]], "one"),
        ([[1, 2, 3], [2, 4, 9]], "none"),
        ([[1, 2, 3], [3, 6, 9]], "infinite"),
        ([[2, -3, 5], [-4, 6, -10]], "infinite"),
        ([[2, -3, 5], [-4, 6, 7]], "none"),
    ],
)
def test_three_classifiers_agree(raw, kind):
    pair = ref.eqs(raw)
    assert ref.kind_ratios(pair) == ref.kind_sympy(pair) == ref.kind_gauss(pair) == kind


def test_determinants_two_ways():
    for a, b, c, d in [(1, 2, 3, 4), (0, 5, 2, 7), (0, 0, 1, 1), (3, -2, -6, 4)]:
        vals = [F(v) for v in (a, b, c, d)]
        assert ref.det2(*vals) == ref.det2_sympy(*vals) == a * d - b * c


def test_scan_needs_exactly_one_grid_point():
    with pytest.raises(ValueError):
        ref.scan_pair(ref.eqs([[1, 0, 1000], [0, 1, 2]]))  # solution outside the grid


# ---------------------------------------------------------------- the families

PAIR_TEMPLATES = [t for t in TEMPLATES if t["syllabus"]["chapter_ref"] == "cbse.10.maths.ch03"]


def test_chapter_has_between_14_and_20_item_models():
    assert 14 <= len(PAIR_TEMPLATES) <= 20
    assert all(t["family"] in FAMILIES for t in PAIR_TEMPLATES)
    assert {t["form"]["marks"] for t in PAIR_TEMPLATES} == {1, 2, 3, 4} or len(PAIR_TEMPLATES) < 19


@pytest.mark.parametrize("template", PAIR_TEMPLATES, ids=lambda t: t["short"])
def test_options_are_named_pair_slips_and_methods_agree(template):
    got = tuples(template, 8)
    assert got, "no well-posed tuple"
    for params in got:
        built = LANE._build(template, params)
        assert len(built.methods) == 3 and len({m.independence_group for m in built.methods}) == 3
        for m in built.methods:  # three independent methods give the key, exactly
            assert chash(m.solve(built.spec)) == chash(built.answer)
        ctx = LANE.render(template, params)
        wrong = [o for o in ctx.options if o["id"] != "key"]
        assert len(wrong) == 3 and all(o["procedure"] in PAIR_TEXT for o in wrong)
        for text in (*built.hints, built.stem, *built.steps):
            assert "CBSE" not in text and "NCERT" not in text
        for hint in built.hints[:2]:
            assert not any(ch.isdigit() for ch in hint), hint


def _pick(short, params):
    template = next(t for t in PAIR_TEMPLATES if t["short"] == short)
    return LANE.render(template, params), LANE._build(template, params)


def test_golden_graph_point_and_type():
    ctx, built = _pick(
        "C10.PAIR.GRAPH_POINT", {"x": 2, "y": 1, "ma": 1, "mb": -1, "wide": 0, "first": 0}
    )
    assert ctx.answer["value"] == "(2, 1)"
    assert (
        "(0, -1)" in built.stem
        and "(3, 2)" in built.stem
        and "(1, 2)" in built.stem
        and "(4, -1)" in built.stem
    )
    types = {"one": "exactly one", "none": "parallel", "infinite": "same line"}
    for kind, word in types.items():
        ctx, _ = _pick(
            "C10.PAIR.GRAPH_TYPE", {"kind": kind, "a1": 2, "b1": 3, "c1": 3, "m": 2, "d": 1}
        )
        assert word in ctx.answer["value"]


def test_golden_substitution_elimination_and_ratio_formula():
    ctx, _ = _pick("C10.PAIR.SUBST_FORM", {"x": 3, "y": 3, "m": 2, "a": 3, "b": 2, "ask": "pair"})
    assert ctx.answer["value"] == "x = 3, y = 3" and "y = 2x - 3" in ctx.stem
    ctx, _ = _pick(
        "C10.PAIR.ELIM_BOTH", {"x": 3, "y": 2, "e": 0, "a1": 2, "a2": 3, "q1": 3, "q2": -4}
    )
    assert ctx.answer["value"] == "x = 3, y = 2" and "2x + 3y = 12" in ctx.stem
    ctx, _ = _pick("C10.PAIR.CROSS_SOLVE", {"x": 2, "y": 1, "a1": 1, "b1": 2, "a2": 3, "b2": 1})
    assert ctx.answer["value"] == "x = 2, y = 1" and "x + 2y - 4 = 0" in ctx.stem
    ctx, _ = _pick(
        "C10.PAIR.CROSS_SETUP",
        {"which": "r", "a1": 2, "b1": 3, "c1": -5, "a2": 3, "b2": 1, "c2": 2},
    )
    assert ctx.answer["value"] == "-7"  # 2*1 - 3*3


def test_a_wrong_option_really_is_what_its_tag_says():
    # adding two equations whose x terms have the same sign: 3x + 2y = 13, 3x - 4y = 1
    ctx, _ = _pick(
        "C10.PAIR.ELIM_DIRECT", {"x": 3, "y": 2, "e": 0, "pe": 3, "sgn": 1, "q1": 2, "q2": -4}
    )
    by_tag = {o["procedure"]: o["value"]["value"] for o in ctx.options}
    assert ctx.answer["value"] == "x = 3, y = 2"
    # added: (2 + -4) y = 13 + 1 -> y = -7, then x from the first equation: (13 + 14) / 3 = 9
    assert by_tag["MC.PAIR.ELIM_ADD_NOT_SUBTRACT"] == "x = 9, y = -7"


def test_hint_does_not_leak():
    for template in PAIR_TEMPLATES:
        for params in tuples(template, 4):
            built = LANE._build(template, params)
            for hint in built.hints[:2]:
                for token in built.tokens:
                    assert not hint_leaks_answer(hint, token)


@pytest.mark.parametrize("template", PAIR_TEMPLATES, ids=lambda t: t["short"])
def test_language_lint_is_clean_on_sampled_items(template):
    for params in tuples(template, 12):
        built = LANE._build(template, params)
        errors, _ = lint_item_texts(stem=built.stem, hints=built.hints)
        assert errors == [], (built.stem, errors)


def test_golden_k_word_and_reciprocal_items():
    ctx, built = _pick(
        "C10.PAIR.K_NONE", {"p": 1, "q": 2, "s1": 1, "s2": 3, "cc": 2, "d": 1, "pos": "a"}
    )
    assert ctx.answer["value"] == "3" and "kx + 6y = 7" in built.stem
    ctx, _ = _pick("C10.PAIR.K_INFINITE", {"p": 1, "q": 2, "s1": 1, "s2": 3, "cc": 2, "pos": "c"})
    assert ctx.answer["value"] == "6"  # second constant is 3 * 2
    ctx, _ = _pick(
        "C10.PAIR.WORD_AGES", {"y": 10, "k": 2, "t": 4, "when": "later", "ask": "A", "who": 0}
    )
    assert ctx.answer["value"] == "24 years"
    ctx, _ = _pick(
        "C10.PAIR.WORD_STREAM", {"x": 10, "y": 2, "t1": 3, "t2": 2, "ask": "stream", "ctx": 0}
    )
    assert ctx.answer["value"] == "2 km/h"
    ctx, _ = _pick("C10.PAIR.WORD_RECT", {"w": 4, "k": 2, "e": 2, "ask": "area", "ctx": 0})
    assert ctx.answer["value"] == "40 square metres"  # 10 by 4
    ctx, _ = _pick("C10.PAIR.RECIP_PAIR", {"x": 2, "y": 3, "a": 1, "b": 3, "d": 2, "e": 1})
    assert ctx.answer["value"] == "x = 2, y = 3" and ctx.answer["values"] == {
        "u": "1/2",
        "v": "1/3",
    }
    ctx, _ = _pick("C10.PAIR.RECIP_SUMDIFF", {"x": 4, "y": 1, "a": 1, "b": 2, "d": 2, "e": 1})
    assert ctx.answer["value"] == "x = 4, y = 1"


def test_a_tuple_is_thrown_away_when_two_methods_disagree():
    from app.factory.lanes.maths.core import FnMethod, IllPosed
    from app.factory.lanes.maths.lin2_core import agree

    good = {"values": {"x": "1", "y": "2"}, "value": "x = 1, y = 2"}
    bad = FnMethod("bad", "other", "", lambda spec: {**good, "value": "x = 2, y = 1"})
    ok = FnMethod("ok", "closed", "", lambda spec: good)
    agree({}, [ok], good)
    with pytest.raises(IllPosed):
        agree({}, [ok, bad], good)
