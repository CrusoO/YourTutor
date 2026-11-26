"""Every variant of every model: construction, two methods, kernel, distractors, hints, wording."""

import functools
import re

import pytest

from app.content.originality import ReferenceIndex
from app.factory.kernel import certificate_is_current
from app.factory.lanes.biology.common import NO_BOARD_WORDS
from app.factory.lanes.biology.lane import LANE
from app.factory.lanes.biology.models import ALL_MODELS, MISC
from app.factory.runner import run_item

from .helpers import TEMPLATES, all_variant_cases, first, key_of

CASES = all_variant_cases()
SHORTCUTS = re.compile(
    r"move .* (across|over)|flip the sign|change the sign of the term|transpose|cross-multiply",
    re.I,
)

# Hand-computed answers, written without running the lane (a different author's check).
GOLDEN = [
    ("HERED.MONO_RATIO", {"cross": "Hh,Hh", "variant": "phen_ratio"}, "3 : 1"),
    ("HERED.MONO_RATIO", {"cross": "Hh,Hh", "variant": "gen_ratio"}, "1 : 2 : 1"),
    ("HERED.MONO_RATIO", {"cross": "Hh,hh", "variant": "phen_ratio"}, "1 : 1"),
    ("HERED.MONO_RATIO", {"cross": "HH,Hh", "variant": "gen_ratio"}, "1 : 1"),
    ("HERED.MONO_PROB", {"cross": "Hh,Hh", "variant": "p_rec"}, "1/4"),
    ("HERED.MONO_PROB", {"cross": "Hh,Hh", "variant": "p_dom"}, "3/4"),
    ("HERED.MONO_PROB", {"cross": "Hh,Hh", "variant": "p_het"}, "1/2"),
    ("HERED.MONO_PROB", {"cross": "Hh,Hh", "variant": "p_homdom"}, "1/4"),
    ("HERED.MONO_PROB", {"cross": "Hh,hh", "variant": "p_dom"}, "1/2"),
    ("HERED.DI_RATIO", {"cross": "HhGg,HhGg"}, "9 : 3 : 3 : 1"),
    ("HERED.DI_RATIO", {"cross": "HhGg,hhgg"}, "1 : 1 : 1 : 1"),
    ("HERED.DI_RATIO", {"cross": "HhGg,Hhgg"}, "3 : 3 : 1 : 1"),
    ("HERED.DI_RATIO", {"cross": "HhGg,hhGg"}, "3 : 1 : 3 : 1"),
    ("HERED.DI_RATIO", {"cross": "HHGg,hhgg"}, "1 : 1"),
    ("HERED.DI_PROB", {"cross": "HhGg,HhGg", "variant": "both_dom"}, "9/16"),
    ("HERED.DI_PROB", {"cross": "HhGg,HhGg", "variant": "dom_rec"}, "3/16"),
    ("HERED.DI_PROB", {"cross": "HhGg,HhGg", "variant": "both_rec"}, "1/16"),
    ("HERED.DI_PROB", {"cross": "HhGg,HhGg", "variant": "double_het"}, "1/4"),
    ("HERED.DI_PROB", {"cross": "HhGg,hhgg", "variant": "both_dom"}, "1/4"),
    ("HERED.TEST_CROSS", {"pair": "TR", "key": "HHGg"}, "TTRr"),
    ("HERED.TEST_CROSS", {"pair": "TR", "key": "HhGG"}, "TtRR"),
    ("HERED.COUNTS_MONO", {"cross": "Hh,Hh", "variant": "dom", "N": "200"}, "150 offspring"),
    ("HERED.COUNTS_MONO", {"cross": "Hh,Hh", "variant": "rec", "N": "200"}, "50 offspring"),
    ("HERED.COUNTS_DI", {"cross": "HhGg,HhGg", "variant": "both_dom", "N": "160"}, "90 offspring"),
    ("HERED.COUNTS_DI", {"cross": "HhGg,HhGg", "variant": "dom_rec", "N": "160"}, "30 offspring"),
    ("HERED.COUNTS_DI", {"cross": "HhGg,HhGg", "variant": "both_rec", "N": "160"}, "10 offspring"),
    ("HERED.GAMETES", {"variant": "gamete_types", "case": "HhGg", "t": "TR"}, "4"),
    ("HERED.GAMETES", {"variant": "gamete_types", "case": "HHGg", "t": "TR"}, "2"),
    ("HERED.GAMETES", {"variant": "gamete_types", "case": "Hh", "t": "T"}, "2"),
    ("HERED.GAMETES", {"variant": "grid_boxes", "case": "HhGg,HhGg", "t": "TR"}, "16"),
    ("HERED.GAMETES", {"variant": "grid_boxes", "case": "HHGg,hhgg", "t": "TR"}, "2"),
    ("HERED.GAMETES", {"variant": "phen_classes", "case": "HhGg,HhGg", "t": "TR"}, "4"),
    ("HERED.GAMETES", {"variant": "gen_classes", "case": "HhGg,HhGg", "t": "TR"}, "9"),
    ("HERED.GAMETES", {"variant": "gen_classes", "case": "Hh,Hh", "t": "T"}, "3"),
    ("HERED.SEX_SEQ", {"variant": "exactly_k", "n": "4", "k": "2"}, "3/8"),
    ("HERED.SEX_SEQ", {"variant": "exactly_k", "n": "5", "k": "1"}, "5/32"),
    ("HERED.SEX_SEQ", {"variant": "all_girls", "n": "3"}, "1/8"),
    ("HERED.SEX_SEQ", {"variant": "at_least_one_boy", "n": "4"}, "15/16"),
    ("HERED.SEX_SEQ", {"variant": "both_sexes", "n": "3"}, "3/4"),
    ("HERED.SEX_SEQ", {"variant": "next_after_run", "n": "4"}, "1/2"),
    (
        "ENV.TEN_PERCENT",
        {"variant": "level_n", "chain": "0", "e0": "20000", "n": "4", "unit": "kJ"},
        "20 kJ",
    ),
    (
        "ENV.TEN_PERCENT",
        {"variant": "next_level", "chain": "0", "e0": "2000", "n": "2", "unit": "J"},
        "200 J",
    ),
    (
        "ENV.TEN_PERCENT",
        {"variant": "producer_from_top", "chain": "0", "e0": "1000000", "n": "4", "unit": "J"},
        "1000000 J",
    ),
    (
        "ENV.TEN_PERCENT",
        {
            "variant": "level_from_level",
            "chain": "0",
            "e0": "5000",
            "n": "4",
            "m": "2",
            "unit": "J",
        },
        "50 J",
    ),
    (
        "ENV.ENERGY_LOST",
        {"variant": "lost_one_step", "chain": "0", "e0": "1000", "n": "2", "unit": "J"},
        "900 J",
    ),
    (
        "ENV.ENERGY_LOST",
        {"variant": "lost_total", "chain": "0", "e0": "20000", "n": "3", "unit": "J"},
        "19800 J",
    ),
    ("ENV.ENERGY_LOST", {"variant": "percent_reaching", "chain": "0", "n": "3"}, "1 percent"),
    ("ENV.ENERGY_LOST", {"variant": "percent_reaching", "chain": "0", "n": "4"}, "0.1 percent"),
    ("ENV.TROPHIC", {"variant": "level_of", "chain": "0", "pos": "3"}, "level 3"),
    ("ENV.TROPHIC", {"variant": "organism_at", "chain": "0", "pos": "3"}, "frog"),
    ("ENV.TROPHIC", {"variant": "kind_of", "chain": "0", "pos": "4"}, "tertiary consumer"),
    ("ENV.TROPHIC", {"variant": "n_levels", "chain": "0", "pos": "1"}, "5"),
    ("ENV.TROPHIC", {"variant": "n_consumers", "chain": "4", "pos": "1"}, "2"),
    ("ENV.TROPHIC", {"variant": "n_steps", "chain": "1", "pos": "1"}, "3"),
    (
        "ENV.CONC_CHAIN",
        {"variant": "forward", "chain": "0", "c0": "2", "f": "3", "n": "3"},
        "18 ppm",
    ),
    (
        "ENV.CONC_CHAIN",
        {"variant": "backward", "chain": "0", "c0": "2", "f": "3", "n": "3"},
        "2 ppm",
    ),
    (
        "ENV.CONC_CHAIN",
        {"variant": "forward", "chain": "0", "c0": "0.5", "f": "10", "n": "2"},
        "5 ppm",
    ),
    ("REPRO.FISSION", {"variant": "after_divisions", "n0": "3", "n": "4"}, "48 cells"),
    ("REPRO.FISSION", {"variant": "after_time", "n0": "2", "n": "3", "d": "30"}, "16 cells"),
    ("REPRO.FISSION", {"variant": "divisions_needed", "n0": "5", "n": "4"}, "4 rounds"),
    ("REPRO.FISSION", {"variant": "time_needed", "n0": "1", "n": "6", "d": "20"}, "120 minutes"),
    ("REPRO.FISSION", {"variant": "multiple_fission", "n0": "1", "n": "3", "k": "4"}, "64 cells"),
    ("REPRO.CHROMOSOMES", {"variant": "gamete_n", "m": "12"}, "6 chromosomes"),
    ("REPRO.CHROMOSOMES", {"variant": "zygote_2n", "m": "10"}, "20 chromosomes"),
    ("REPRO.CHROMOSOMES", {"variant": "after_mitosis", "m": "8"}, "16 chromosomes"),
    ("REPRO.CHROMOSOMES", {"variant": "embryo_total", "m": "10", "r": "3"}, "160 chromosomes"),
    ("REPRO.FRAGMENTS", {"variant": "pieces_from_cuts", "a": "4"}, "5 organisms"),
    ("REPRO.FRAGMENTS", {"variant": "cuts_for_pieces", "a": "6"}, "5 cuts"),
    ("REPRO.FRAGMENTS", {"variant": "after_budding", "a": "3"}, "4 hydras"),
    ("REPRO.FRAGMENTS", {"variant": "two_rounds", "a": "3", "b": "4"}, "12 organisms"),
    ("LIFE.EQUATION", {"q": "photosynthesis:C6H12O6>O2", "g": "3"}, "18 molecules"),
    ("LIFE.EQUATION", {"q": "respiration:O2>CO2", "g": "10"}, "10 molecules"),
    ("LIFE.EQUATION", {"q": "fermentation:C6H12O6>C2H5OH", "g": "5"}, "10 molecules"),
    ("LIFE.EQUATION", {"q": "respiration:C6H12O6>H2O", "g": "4"}, "24 molecules"),
    (
        "LIFE.RATES",
        {"ctx": "heart", "variant": "total", "r": "72", "t": "5", "tu": "min"},
        "360 beats",
    ),
    (
        "LIFE.RATES",
        {"ctx": "breath", "variant": "total", "r": "15", "t": "2", "tu": "h"},
        "1800 breaths",
    ),
    (
        "LIFE.RATES",
        {"ctx": "bubbles", "variant": "rate", "r": "8", "t": "10", "tu": "min"},
        "8 bubbles per minute",
    ),
    ("LIFE.RATES", {"ctx": "heart", "variant": "time", "r": "60", "t": "2", "tu": "h"}, "2 hours"),
]


@functools.cache
def _ctx_cached(model_id: str, variant: str):
    fixed = {"variant": variant} if variant else {}
    params = first(model_id, **fixed)
    tpl = TEMPLATES[model_id]
    return LANE.render(tpl, params), params, tpl


def test_counts():
    assert len(ALL_MODELS) == 18 and len(CASES) >= 50
    chapters = {m.chapter for m in ALL_MODELS.values()}
    assert chapters == {
        "cbse.10.biology.heredity",
        "cbse.10.biology.environment",
        "cbse.10.biology.reproduction",
        "cbse.10.biology.life_processes",
    }
    assert set(TEMPLATES) == set(ALL_MODELS)


@pytest.mark.parametrize(
    ("model_id", "params", "key"), GOLDEN, ids=[f"{g[0]}-{i}" for i, g in enumerate(GOLDEN)]
)
def test_hand_computed_answers(model_id, params, key):
    assert key_of(model_id, **params) == key


@pytest.mark.parametrize(("model_id", "variant"), CASES)
def test_item_is_stampable_with_independent_groups(model_id, variant):
    ctx, params, tpl = _ctx_cached(model_id, variant)
    ctx2, result = run_item(LANE, tpl, params, reference_index=ReferenceIndex())
    assert result.stampable, result.first_failure
    assert certificate_is_current(ctx2.certificate.body)
    groups = {m["independence_group"] for m in ctx2.certificate.body["methods"]}
    model = ALL_MODELS[model_id]
    assert groups == {"kernel.exact", model.group_a, model.group_b}
    assert len(groups) == 3
    assert ctx.spec["domain"] in ("genetics", "algebra") and ctx.lane == "biology"


@pytest.mark.parametrize(("model_id", "variant"), CASES)
def test_options_hints_and_words(model_id, variant):
    ctx, _, _ = _ctx_cached(model_id, variant)
    assert len(ctx.options) == 4 and ctx.key_option == "key"
    assert ctx.options[0]["procedure"] == "correct"
    for option in ctx.options[1:]:
        assert re.fullmatch(r"BIO\.MC\.(HERED|ENV|REPRO|LIFE)\.[A-Z0-9_]+", option["procedure"])
        area_key, name = option["procedure"].split(".")[2:]
        assert name in MISC[area_key]
    assert len({o["text"] for o in ctx.options}) == 4
    assert len(ctx.hints) == 3 and all(len(h) > 20 for h in ctx.hints)
    assert not any(SHORTCUTS.search(h) for h in ctx.hints + ctx.steps)
    text = " ".join(
        [ctx.stem, *ctx.hints, *ctx.steps, ctx.prediction, *(o["text"] for o in ctx.options)]
    ).lower()
    assert not [w for w in NO_BOARD_WORDS if re.search(rf"\b{w}\b", text)]
    assert "assertion" not in text and "reason:" not in text
    assert "?" in ctx.stem


@pytest.mark.parametrize("model_id", list(ALL_MODELS))
def test_each_model_has_two_distinct_methods_and_techniques(model_id):
    model = ALL_MODELS[model_id]
    assert model.technique and model.technique_b and model.group_a != model.group_b
    assert model.group_a != "kernel.exact" and model.group_b != "kernel.exact"
    assert model.solve_a is not model.solve_b


def test_the_stamped_type_is_always_multiple_choice_with_no_free_text():
    for model_id in ALL_MODELS:
        ctx, _, tpl = _ctx_cached(model_id, (ALL_MODELS[model_id].box.get("variant") or ("",))[0])
        assert ctx.item_type in ("", "mcq") and ctx.facts is None and ctx.diagram is None
        assert "free_text" in tpl["syllabus"]["forbidden_content"]


def test_student_answer_check_accepts_the_key_and_equivalent_numbers():
    ctx, _, _ = _ctx_cached("HERED.MONO_PROB", "p_rec")
    key = ctx.options[0]["text"]
    assert LANE.check_student_answer(ctx, key)
    assert LANE.check_student_answer(ctx, " " + key + " ")
    assert not LANE.check_student_answer(ctx, ctx.options[1]["text"])
    sex, _, _ = _ctx_cached("HERED.SEX_SEQ", "all_girls")
    assert LANE.check_student_answer(sex, "0.125") == (sex.options[0]["text"] == "1/8")
    amount, _, _ = _ctx_cached("ENV.TEN_PERCENT", "level_n")
    number = amount.options[0]["text"].split()[0]
    assert LANE.check_student_answer(amount, number)
    assert not LANE.check_student_answer(amount, "banana")
