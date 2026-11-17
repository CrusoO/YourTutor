"""Seeded simulation tests. Small in CI; PROBE_SIM_LONG=1 runs many more students."""

from __future__ import annotations

import csv
import io
import math
import os
import random
from contextlib import redirect_stdout
from dataclasses import replace

import pytest

from app.learner.probe import sim
from app.learner.probe.sim import SCENARIOS, SplitMix, cell_stats, run_probe, standard_graphs
from app.learner.probe.space import build_space
from app.learner.probe.types import Space
from tests.learner.probe.legacy_planner import run_legacy
from tests.learner.probe.probe_helpers import CFG

LONG = os.environ.get("PROBE_SIM_LONG") == "1"
N = 1500 if LONG else 150
SEED = 20261117
GRAPHS = standard_graphs()


def space_for(name: str) -> tuple[Space, dict[str, list[str]]]:
    skills, pre = GRAPHS[name]
    return build_space(skills, pre, max_states=CFG.max_states), pre


BLEND_GUESS = 0.15  # the spec's typed-and-MCQ blend; real typed items guess at 0.05
BUDGET_CFG = replace(CFG, min_gain_bits=0.0)  # spend the whole question budget


def compare(
    name: str, scenario: str, seed: int = SEED, guess: float | None = BLEND_GUESS
) -> tuple[sim.CellStats, sim.CellStats]:
    """Paired students: the same truths go through the legacy planner, then the probe with the
    legacy planner's mean length (rounded up) as its question budget (equal questions)."""
    space, pre = space_for(name)
    base, viol = SCENARIOS[scenario]
    items = sim.make_items(space, CFG)
    if guess is not None:
        items = [replace(it, guess=guess) for it in items]
    rng = random.Random(seed)
    truths = [sim.draw_truth(space, CFG, rng, base=base, violation=viol) for _ in range(N)]
    leg = cell_stats([run_legacy(space, t, items, pre, rng) for t in truths])
    cap = math.ceil(leg.mean_questions)
    probe = [run_probe(space, t, items, BUDGET_CFG, rng, cap=cap) for t in truths]
    return leg, cell_stats(probe)


def test_same_seed_same_result() -> None:
    assert compare("diamond", "matched", 3) == compare("diamond", "matched", 3)
    assert compare("diamond", "matched", 3) != compare("diamond", "matched", 4)


def test_graph_sizes() -> None:
    assert len(space_for("spec12")[0].states) == 42
    assert len(space_for("chain12")[0].states) == 13
    assert all(len(GRAPHS[g][0]) in (4, 12) for g in GRAPHS)


CI_GRAPHS = ["chain12", "diamond", "spec12"] + (["wide3"] if LONG else [])  # wide3 is slow


@pytest.mark.parametrize("graph", CI_GRAPHS)
@pytest.mark.parametrize("scenario", ["matched", "truth_low", "truth_high", "violations5"])
def test_probe_is_not_worse_than_legacy_at_equal_questions(graph: str, scenario: str) -> None:
    """Skill accuracy at the legacy planner's own question count, within paired-sample noise."""
    leg, probe = compare(graph, scenario)
    assert probe.mean_questions <= math.ceil(leg.mean_questions)
    assert probe.skill_accuracy >= leg.skill_accuracy - 0.03, (leg, probe)


@pytest.mark.parametrize("graph", ["chain12", "spec12"] + (["wide3"] if LONG else []))
def test_probe_wins_clearly_when_the_prior_is_wrong_high(graph: str) -> None:
    leg, probe = compare(graph, "truth_high")
    assert probe.skill_accuracy >= leg.skill_accuracy


@pytest.mark.parametrize("graph", ["chain12", "spec12"] + (["wide3"] if LONG else []))
def test_with_typed_items_the_production_probe_asks_fewer_questions(graph: str) -> None:
    """Real typed items guess at 0.05, which flatters the fixed-order planner. The production
    probe (its own stopping rules) then uses fewer questions at about the same accuracy. (Not
    asserted on the 4-skill diamond, where "all resolved" needs a few more questions.)"""
    space, pre = space_for(graph)
    items = sim.make_items(space, CFG)
    rng = random.Random(SEED)
    truths = [sim.draw_truth(space, CFG, rng) for _ in range(N)]
    leg = cell_stats([run_legacy(space, t, items, pre, rng) for t in truths])
    probe = cell_stats([run_probe(space, t, items, CFG, rng) for t in truths])
    assert probe.mean_questions <= leg.mean_questions + 0.1
    assert probe.skill_accuracy >= leg.skill_accuracy - 0.04, (leg, probe)


def test_matched_prior_accuracy_at_cap_12() -> None:
    space, _ = space_for("spec12")
    runs = sim.run_cell(space, CFG, random.Random(SEED), N, "matched", 12)
    assert cell_stats(runs).skill_accuracy >= 0.94


def test_accuracy_does_not_fall_as_questions_rise() -> None:
    space, _ = space_for("spec12")
    acc = [
        cell_stats(sim.run_cell(space, CFG, random.Random(SEED), N, "matched", cap)).skill_accuracy
        for cap in (4, 8, 12)
    ]
    assert acc[0] < acc[1] <= acc[2] + 0.01


def test_calibration_is_internally_consistent() -> None:
    space, _ = space_for("spec12")
    items = sim.make_items(space, CFG)
    rng = random.Random(SEED)
    # truths drawn from the model's own mixture of bases, so the prior is truly matched
    bases = [rng.choice(CFG.prior_bases) for _ in range(N * 2)]
    truths = [sim.draw_truth(space, CFG, rng, base=b) for b in bases]
    runs = [run_probe(space, t, items, CFG, rng, cap=12) for t in truths]
    n, mean_marginal, rate = sim.calibration(space, runs, 0.8, 0.9)
    assert n >= 30
    assert abs(rate - mean_marginal) <= 0.1


def test_run_never_exceeds_cap_and_is_valid() -> None:
    space, _ = space_for("spec12")
    items = sim.make_items(space, CFG)
    rng = random.Random(1)
    for _ in range(30):
        t = sim.draw_truth(space, CFG, rng)
        run = run_probe(space, t, items, CFG, rng, cap=6)
        assert run.asked <= 6
        assert 0.0 <= run.accuracy <= 1.0


def test_violation_cases_actually_break_the_graph() -> None:
    space, _ = space_for("spec12")
    rng = random.Random(5)
    closed = set(space.states)
    bad = sum(sim.draw_truth(space, CFG, rng, violation=0.05) not in closed for _ in range(300))
    assert bad > 30
    assert all(sim.draw_truth(space, CFG, rng) in closed for _ in range(100))


def test_splitmix_is_seeded_and_uniform_enough() -> None:
    a, b = SplitMix(9), SplitMix(9)
    xs = [a.random() for _ in range(2000)]
    assert xs == [b.random() for _ in range(2000)]
    assert all(0.0 <= x < 1.0 for x in xs)
    assert abs(sum(xs) / len(xs) - 0.5) < 0.03


def test_csv_cli_writes_the_accuracy_curve() -> None:
    buf = io.StringIO()
    with redirect_stdout(buf):
        assert sim.main(["--students", "5", "--min-cap", "4", "--max-cap", "5"]) == 0
    rows = list(csv.DictReader(io.StringIO(buf.getvalue())))
    assert len(rows) == 4 * 4 * 2  # graphs x scenarios x caps
    assert list(rows[0]) == sim.HEADER
    assert all(float(r["mean_questions"]) <= int(r["cap"]) for r in rows)
