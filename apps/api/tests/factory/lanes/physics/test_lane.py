"""Every variant of every model: backward construction, two methods, kernel, distractors, hints."""

import functools
import re

import pytest

from app.content.originality import ReferenceIndex
from app.factory.kernel import certificate_is_current
from app.factory.lanes.physics.build import build, parse_value
from app.factory.lanes.physics.lane import LANE
from app.factory.lanes.physics.model import FORMS
from app.factory.lanes.physics.models import ALL_MODELS
from app.factory.lanes.physics.quantities import dec, evaluate, expr_names, sig_figs
from app.factory.lanes.physics.templates import TEMPLATES
from app.factory.runner import run_item

from .helpers import all_variant_cases, first, tuples

CASES = all_variant_cases()
SHORTCUTS = re.compile(
    r"move .* (across|over)|flip the sign|change the sign of the term|transpose|cross-multiply",
    re.I,
)  # noqa: E501


@functools.cache
def _ctx_cached(model_id: str, variant: str):
    params = first(model_id, variant=variant)
    tpl = TEMPLATES[model_id]
    return LANE.render(tpl, params), params, tpl


def _ctx_for(model_id: str, variant: str):
    return _ctx_cached(model_id, variant)


def test_counts():
    assert len(ALL_MODELS) == 27 and len(CASES) >= 75
    electricity = [m for m in ALL_MODELS.values() if m.chapter.endswith("electricity")]
    light = [m for m in ALL_MODELS.values() if m.chapter.endswith("light")]
    assert len(electricity) == 15 and len(light) == 12


@pytest.mark.parametrize(("model_id", "variant"), CASES)
def test_item_is_stamped_clean_with_independent_groups(model_id, variant):
    ctx, params, tpl = _ctx_for(model_id, variant)
    ctx2, result = run_item(LANE, tpl, params, reference_index=ReferenceIndex())
    assert result.stampable, result.first_failure
    assert certificate_is_current(ctx2.certificate.body)
    groups = {m["independence_group"] for m in ctx2.certificate.body["methods"]}
    assert groups == {"kernel.exact", "closed_form", "sympy.laws"}
    assert ctx.spec["domain"] == "algebra" and ctx.lane == "physics"


@pytest.mark.parametrize(("model_id", "variant"), CASES)
def test_options_hints_and_words(model_id, variant):
    ctx, params, _ = _ctx_for(model_id, variant)
    assert len(ctx.options) == 4 and ctx.key_option == "key"
    key = ctx.options[0]
    assert key["procedure"] == "correct"
    wrongs = ctx.options[1:]
    assert len({o["text"] for o in ctx.options}) == 4  # distinct on screen
    for option in wrongs:
        assert option["value"] != key["value"]  # differs from the key
        assert option["procedure"].startswith("PHY.MC.")  # a named wrong procedure
    # the three hints: strategy, next operation, first-step lead-in; none shows the answer
    assert len(ctx.hints) == 3 and all(h.endswith((".", "?")) for h in ctx.hints)
    token = ctx.answer_tokens[0]
    for hint in ctx.hints:
        assert not re.search(rf"(?<![\d.]){re.escape(token)}(?![\d.])", hint)
        assert not SHORTCUTS.search(hint)
    v = ALL_MODELS[model_id].variants[variant]
    if v.rearr:
        assert "same operation to each side" in ctx.hints[1]
    assert ctx.steps[-1].startswith("So the") and len(ctx.steps) >= 3
    assert not any(SHORTCUTS.search(s) for s in ctx.steps)
    assert "equation" not in " ".join(ctx.hints).lower() and "both sides" not in " ".join(ctx.hints)


@pytest.mark.parametrize(("model_id", "variant"), CASES)
def test_the_key_is_clean_and_the_forward_check_agrees(model_id, variant):
    ctx, params, _ = _ctx_for(model_id, variant)
    phys = ctx.spec["physics"]
    value = ctx.answer["values"][phys["find"]]
    from fractions import Fraction

    x = Fraction(value)
    assert dec(x) is not None and sig_figs(x) <= 3  # 3 significant figures at most
    assert phys["answer_unit"] == ctx.answer["unit"]
    # constants are references, never typed
    for sym, cid in ALL_MODELS[model_id].consts.items():
        assert phys["given"][sym] == {"const": cid}
    # the variant only uses quantities it declares
    v = ALL_MODELS[model_id].variants[variant]
    assert expr_names(v.expr) <= set(v.needs) | set(ALL_MODELS[model_id].consts) | {"s"}
    assert expr_names(v.keq[0]) | expr_names(v.keq[1]) <= set(v.needs) | set(
        ALL_MODELS[model_id].consts
    ) | {"s"}  # noqa: E501
    # the declared forms are real
    assert set(v.forms) <= set(FORMS)
    _ = evaluate  # imported for the doctest of the evaluator below


def test_every_form_is_offered_somewhere_and_marks_follow_the_form():
    seen = {f for m in ALL_MODELS.values() for v in m.variants.values() for f in v.forms}
    assert seen == set(FORMS)
    ctx = LANE.render(TEMPLATES["ELEC.OHM"], first("ELEC.OHM", form="case4"))
    assert ctx.stem.startswith("Case:") and ctx.role == "transfer"
    one = LANE.render(TEMPLATES["ELEC.OHM"], first("ELEC.OHM", form="mcq1"))
    assert one.difficulty < ctx.difficulty and one.role == "procedure"


def test_no_forbidden_item_kinds_are_generated():
    for model_id, variant in CASES:
        ctx, _, _ = _ctx_for(model_id, variant)
        text = (ctx.stem + " ".join(ctx.hints)).lower()
        for banned in (
            "assertion",
            "reason:",
            "draw a",
            "diagram",
            "graph",
            "experiment",
            "explain why",
        ):  # noqa: E501
            assert banned not in text, (model_id, banned)
        assert ctx.diagram is None and ctx.facts is None


def test_rule_derived_items_are_tagged():
    tagged = {m for m, v in CASES if ALL_MODELS[m].variants[v].kind == "rule"}
    assert {"ELEC.RESIST_SCALE", "ELEC.POWER_SCALE", "LIGHT.SIGN", "LIGHT.MIRROR_NATURE"} <= tagged
    ctx = LANE.render(
        TEMPLATES["ELEC.POWER_SCALE"], first("ELEC.POWER_SCALE", variant="P_V_scaled")
    )
    assert ctx.provenance["kind"] == "rule" and ctx.role == "explain"


def test_power_doubling_voltage_gives_four():
    params = first("ELEC.POWER_SCALE", variant="P_V_scaled", k="2")
    ctx = LANE.render(TEMPLATES["ELEC.POWER_SCALE"], params)
    assert ctx.answer["values"] == {"FV": "4"} and "doubled" in ctx.stem
    assert any(o["procedure"].endswith("POWER_SCALES_LINEARLY") for o in ctx.options[1:])


def test_named_wrong_procedures_for_the_required_mistakes_exist():
    names = {mc.rsplit(".", 1)[1] for m in ALL_MODELS.values() for v in m.variants.values()
             for mc, _ in v.wrongs}  # fmt: skip
    required = {
        "SERIES_PARALLEL_SWAPPED",
        "CURRENT_NOT_SQUARED",
        "TIME_UNIT_SLIP",  # noqa: E501
        "U_SIGN_DROPPED",
        "POWER_AS_V_OVER_I",
        "VOLTAGE_NOT_SQUARED",
        "FORGOT_FINAL_RECIPROCAL",  # noqa: E501
        "MIRROR_LENS_FORMULA_MIXED",
        "PARALLEL_RESISTANCES_ADDED",
        "MAG_SIGN_DROPPED",
    }
    assert required <= names
    # milliamp slip appears automatically when the answer unit has a prefix
    params = first("ELEC.OHM", variant="I_from_VR", iu="mA")
    ctx = LANE.render(TEMPLATES["ELEC.OHM"], params)
    assert any(o["procedure"].endswith("UNIT_PREFIX_SLIP") for o in ctx.options[1:]) or any(
        o["procedure"].endswith("UNIT_PREFIX_SLIP")
        for o in LANE.render(
            TEMPLATES["ELEC.OHM"], first("ELEC.OHM", variant="R_from_VI", ru="kohm")
        ).options[1:]
    )


def test_ill_posed_tuples_are_refused_with_reasons():
    tpl = TEMPLATES["LIGHT.MIRROR_FORMULA"]
    reasons = {LANE.well_posed(tpl, p) for p in _all(tpl)}
    assert "degenerate_geometry" in reasons  # object at the focus: image at infinity
    tpl = TEMPLATES["ELEC.SERIES"]
    assert "rset_size_does_not_match_variant" in {LANE.well_posed(tpl, p) for p in _all(tpl)}
    tpl = TEMPLATES["ELEC.OHM"]
    assert "implausible_size:V" in {LANE.well_posed(tpl, p) for p in _all(tpl)}


def _all(tpl):
    import itertools

    names = sorted(tpl["box"])
    for combo in itertools.product(*[tpl["box"][n]["choices"] for n in names]):
        yield dict(zip(names, combo, strict=True))


def test_real_and_virtual_images_follow_the_sign_convention():
    ctx = LANE.render(
        TEMPLATES["LIGHT.MIRROR_NATURE"],
        first(
            "LIGHT.MIRROR_NATURE",
            variant="nature_mirror",
            device="concave_mirror",
            um="30",
            fm="10",
        ),
    )  # noqa: E501
    assert ctx.answer["nature"] == "real, inverted, diminished" and ctx.answer["values"] == {
        "v": "-15"
    }  # noqa: E501
    ctx = LANE.render(
        TEMPLATES["LIGHT.MIRROR_NATURE"],
        first(
            "LIGHT.MIRROR_NATURE", variant="nature_mirror", device="convex_mirror", um="20", fm="20"
        ),
    )  # noqa: E501
    assert ctx.answer["nature"] == "virtual, erect, diminished"
    ctx = LANE.render(
        TEMPLATES["LIGHT.MIRROR_NATURE"],
        first(
            "LIGHT.MIRROR_NATURE", variant="nature_lens", device="concave_lens", um="30", fm="10"
        ),
    )  # noqa: E501
    assert ctx.answer["nature"] == "virtual, erect, diminished"
    labels = [o["text"] for o in ctx.options]
    assert len(set(labels)) == 4


def test_student_answers_accept_unit_forms():
    ctx = LANE.render(TEMPLATES["ELEC.OHM"], first("ELEC.OHM", variant="I_from_VR", iu="mA"))
    value = ctx.answer["values"]["I"]
    assert LANE.check_student_answer(ctx, f"{value} mA")
    assert LANE.check_student_answer(ctx, value)
    assert not LANE.check_student_answer(ctx, "banana")
    assert parse_value("-15 cm") == (-15, "cm") and parse_value("2 x 10^19") is not None


def test_build_returns_text_for_a_bad_tuple_and_never_raises_on_the_box():
    tpl = TEMPLATES["ELEC.OHM"]
    assert build(tpl, {"variant": "nope", "form": "mcq1"}) == "unknown_variant"
    count = sum(1 for _ in tuples("ELEC.OHM"))
    assert count > 100
