"""Every variant of every model: backward construction, two methods, kernel, distractors, hints."""

import functools
import itertools
import re
from fractions import Fraction

import pytest

from app.content.originality import ReferenceIndex
from app.factory.kernel import certificate_is_current
from app.factory.lanes.physics.model import FORMS
from app.factory.lanes.physics_c12.build import parse_value
from app.factory.lanes.physics_c12.kit import CHAPTERS, chapter_id
from app.factory.lanes.physics_c12.lane import LANE
from app.factory.lanes.physics_c12.models import ALL_MODELS
from app.factory.lanes.physics_c12.quantities import dec, expr_names, sig_figs
from app.factory.lanes.physics_c12.templates import TEMPLATES
from app.factory.runner import run_item

from .helpers import all_variant_cases, first

CASES = all_variant_cases()
SHORTCUTS = re.compile(
    r"move .* (across|over)|flip the sign|change the sign of the term|transpose|cross-multiply",
    re.I,
)


@functools.cache
def _ctx_cached(model_id: str, variant: str):
    params = first(model_id, variant=variant)
    tpl = TEMPLATES[model_id]
    return LANE.render(tpl, params), params, tpl


def test_counts_and_every_chapter_is_covered():
    assert 25 <= len(ALL_MODELS) <= 35 and len(CASES) >= 120
    for area in CHAPTERS:
        assert any(m.chapter == chapter_id(area) for m in ALL_MODELS.values()), area
    assert set(TEMPLATES) == set(ALL_MODELS)


@pytest.mark.parametrize(("model_id", "variant"), CASES)
def test_item_is_stamped_clean_with_independent_groups(model_id, variant):
    ctx, params, tpl = _ctx_cached(model_id, variant)
    ctx2, result = run_item(LANE, tpl, params, reference_index=ReferenceIndex())
    assert result.stampable, result.first_failure
    assert certificate_is_current(ctx2.certificate.body)
    groups = {m["independence_group"] for m in ctx2.certificate.body["methods"]}
    assert groups == {"kernel.exact", "closed_form", "sympy.laws"}
    assert ctx.spec["domain"] == "algebra" and ctx.lane == "physics_c12"


@pytest.mark.parametrize(("model_id", "variant"), CASES)
def test_options_hints_and_words(model_id, variant):
    ctx, _, _ = _ctx_cached(model_id, variant)
    assert len(ctx.options) == 4 and ctx.key_option == "key"
    key = ctx.options[0]
    assert key["procedure"] == "correct"
    assert len({o["text"] for o in ctx.options}) == 4  # distinct on screen
    for option in ctx.options[1:]:
        assert option["value"] != key["value"]
        assert option["procedure"].startswith("PHY.MC.C12.")  # a named wrong procedure
    assert len(ctx.hints) == 3 and all(h.endswith((".", "?")) for h in ctx.hints)
    token = ctx.answer_tokens[0]
    for hint in ctx.hints:
        assert not re.search(rf"(?<![\d.]){re.escape(token)}(?![\d.])", hint)
        assert not SHORTCUTS.search(hint)
    v = ALL_MODELS[model_id].variants[variant]
    if v.rearr:
        assert "same operation to each side" in ctx.hints[1]
    assert ctx.steps[-1].startswith("So the") and len(ctx.steps) >= 3


@pytest.mark.parametrize(("model_id", "variant"), CASES)
def test_the_key_is_clean_and_constants_are_references(model_id, variant):
    ctx, _, _ = _ctx_cached(model_id, variant)
    phys = ctx.spec["physics"]
    x = Fraction(ctx.answer["values"][phys["find"]])
    assert dec(x) is not None and sig_figs(x) <= 4
    assert phys["answer_unit"] == ctx.answer["unit"]
    model = ALL_MODELS[model_id]
    for sym, cid in model.consts.items():
        assert phys["given"][sym] == {"const": cid}
    v = model.variants[variant]
    assert expr_names(v.expr) <= set(v.needs) | set(model.consts)
    assert not set(v.needs) & set(model.consts)  # a constant is never a typed given
    assert set(v.forms) <= set(FORMS)
    for sym in expr_names(v.expr) & set(model.consts):
        assert f", {sym}, " in ctx.stem or f"{sym} " in ctx.stem  # a used constant is stated


def test_no_forbidden_item_kinds_are_generated():
    for model_id, variant in CASES:
        ctx, _, _ = _ctx_cached(model_id, variant)
        text = (ctx.stem + " ".join(ctx.hints)).lower()
        for banned in (
            "assertion",
            "reason:",
            "draw a",
            "diagram",
            "graph",
            "derive",
            "explain why",
        ):
            assert banned not in text, (model_id, banned)
        assert ctx.diagram is None and ctx.facts is None


COULOMB = {
    "variant": "F_from_q1_q2_r",
    "q1": "2",
    "q2": "3",
    "qu": "uC",
    "r": "30",
    "ru": "cm",
    "form": "mcq1",
}
KNOWN = [
    ("EF.COULOMB", COULOMB, "0.6"),
    ("CAP.CAP_COMBINE", {"variant": "Cs_from_C1_C2", "cset": "12,4", "form": "mcq1"}, "3"),
    ("AC.LCR", {"variant": "Z_from_R_XL_XC", "rxx": "30,70,30", "V": "100", "form": "mcq1"}, "50"),
    ("SEMI.GATES", {"variant": "Ro_from_n", "n": "3", "form": "mcq1"}, "7"),
    (
        "NUC.DECAY",
        {"variant": "N_from_N0_n", "N0": "640", "T": "5", "tu": "day", "n": "3", "form": "mcq1"},
        "80",
    ),
    (
        "DUAL.PHOTOELECTRIC",
        {"variant": "V0_from_Eph_phi", "Eph": "4.5", "phi": "2.5", "f": "1e15", "form": "mcq1"},
        "2",
    ),
]


@pytest.mark.parametrize(("model_id", "params", "expected"), KNOWN)
def test_known_textbook_style_values(model_id, params, expected):
    ctx = LANE.render(TEMPLATES[model_id], params)
    assert ctx.answer["values"][ctx.spec["physics"]["find"]] == expected


def test_student_answer_check_accepts_unit_changes():
    ctx = LANE.render(TEMPLATES["EF.COULOMB"], COULOMB)
    assert LANE.check_student_answer(ctx, "0.6 N") and LANE.check_student_answer(ctx, "600 mN")
    assert not LANE.check_student_answer(ctx, "6 N") and not LANE.check_student_answer(ctx, "word")
    assert parse_value("3 x 10^8 m/s") == (Fraction(3 * 10**8), "m/s")


def _all(tpl):
    names = sorted(tpl["box"])
    for combo in itertools.product(*[tpl["box"][n]["choices"] for n in names]):
        yield dict(zip(names, combo, strict=True))


def test_ill_posed_tuples_are_refused_with_reasons():
    tpl = TEMPLATES["EMI.INDUCTOR"]
    assert "answer_equals_a_given" in {LANE.well_posed(tpl, p) for p in _all(tpl)}
    tpl = TEMPLATES["CAP.CAP_PLATE"]
    reasons = {LANE.well_posed(tpl, p) for p in _all(tpl)}
    assert reasons - {None}  # some tuples of this box make a poor item and say why
