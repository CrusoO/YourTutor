"""Synthetic-student simulation of the probe (test support; the app never imports this).

Pure: the caller passes a seeded random generator (anything with `.random()`, e.g. a
`random.Random`). This package may not import `random` (purity test), so `SplitMix` is provided
for the CLI. Students are drawn from the prior and answer by the same slip/guess process the model
assumes, so the numbers show the algorithm works as designed, not that real children behave so.

CSV report: `python -m app.learner.probe.sim > report.csv` (accuracy against questions asked).
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Protocol

from app.learner.probe.config import load_probe_config
from app.learner.probe.graphs import standard_graphs
from app.learner.probe.prior import initial_belief
from app.learner.probe.result import summarise
from app.learner.probe.select import choose_item, expected_gain
from app.learner.probe.space import build_space, implied_prerequisites
from app.learner.probe.stop import should_stop
from app.learner.probe.types import Answer, Belief, ProbeConfig, ProbeItem, Space
from app.learner.probe.update import item_params, update

ITEMS_PER_SKILL = 3
DEFAULT_BASE = 0.6


class Rng(Protocol):
    def random(self) -> float: ...


class SplitMix:
    """A tiny seeded generator (splitmix64) for the CLI; tests pass `random.Random` instead."""

    def __init__(self, seed: int) -> None:
        self._s = seed & 0xFFFFFFFFFFFFFFFF

    def random(self) -> float:
        mask = 0xFFFFFFFFFFFFFFFF
        self._s = (self._s + 0x9E3779B97F4A7C15) & mask
        z = self._s
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & mask
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & mask
        return ((z ^ (z >> 31)) >> 11) / float(1 << 53)


def make_items(space: Space, cfg: ProbeConfig, per_skill: int = ITEMS_PER_SKILL) -> list[ProbeItem]:
    return [item_params(f"{s}.{n}", s, cfg) for s in space.skills for n in range(per_skill)]


def draw_truth(
    space: Space, cfg: ProbeConfig, rng: Rng, *, base: float = DEFAULT_BASE, violation: float = 0.0
) -> int:
    """A true state from the product prior of one base; then each skill flips with `violation`
    (students who know a skill without its prerequisite break the graph's assumption)."""
    one = replace(cfg, prior_bases=(base,), mixture_floor=0.0)
    weights = initial_belief(space, one).weights
    r, acc, truth = rng.random(), 0.0, space.states[-1]
    for state, w in zip(space.states, weights, strict=True):
        acc += w
        if r < acc:
            truth = state
            break
    for i in range(len(space.skills)):
        if violation > 0.0 and rng.random() < violation:
            truth ^= 1 << i
    return truth


@dataclass(frozen=True)
class SimRun:
    truth: int
    asked: int
    stop_reason: str
    marginals: Mapping[str, float]
    start_skill: str | None
    accuracy: float
    start_ok: bool


def start_is_ready(space: Space, truth: int, start: str | None) -> bool:
    """The recommended start is truly unknown with every prerequisite truly known."""
    if start is None:
        return truth == (1 << len(space.skills)) - 1
    i = space.index(start)
    need = implied_prerequisites(space)[i]
    return not truth >> i & 1 and truth & need == need


def score_marginals(space: Space, truth: int, marks: Mapping[str, float]) -> float:
    right = sum((marks[s] >= 0.5) == bool(truth >> i & 1) for i, s in enumerate(space.skills))
    return right / len(space.skills)


def run_probe(
    space: Space,
    truth: int,
    items: Sequence[ProbeItem],
    cfg: ProbeConfig,
    rng: Rng,
    *,
    cap: int | None = None,
    belief: Belief | None = None,
) -> SimRun:
    """One synthetic student through the probe. `cap` overrides the item cap (for the curve)."""
    if cap is not None:
        cfg = replace(cfg, cap_items=cap, cap_items_wide=cap)
    belief = belief or initial_belief(space, cfg)
    used: set[str] = set()
    counts: dict[str, int] = {}
    recent: list[Answer] = []
    last_mcq, asked = False, 0
    while True:
        item = choose_item(belief, items, frozenset(used), counts, last_mcq, cfg)
        gain = expected_gain(belief, item) if item else 0.0
        reason = should_stop(belief, asked, 0.0, recent, gain, cfg)
        if reason or item is None:
            break
        known = bool(truth >> space.index(item.skill_id) & 1)
        correct = rng.random() < (1.0 - item.slip if known else item.guess)
        answer = Answer(item.item_id, item.skill_id, correct)
        belief = update(belief, item, answer, cfg)
        used.add(item.item_id)
        counts[item.skill_id] = counts.get(item.skill_id, 0) + 1
        recent.append(answer)
        last_mcq = item.is_mcq
        asked += 1
    result = summarise(belief, asked, reason or "no_items", cfg, space.skills)
    return SimRun(
        truth,
        asked,
        result.stop_reason,
        result.marginals,
        result.start_skill,
        score_marginals(space, truth, result.marginals),
        start_is_ready(space, truth, result.start_skill),
    )


@dataclass(frozen=True)
class CellStats:
    students: int
    mean_questions: float
    skill_accuracy: float
    start_ok: float


def cell_stats(runs: Sequence[SimRun]) -> CellStats:
    n = len(runs)
    return CellStats(
        n,
        sum(r.asked for r in runs) / n,
        sum(r.accuracy for r in runs) / n,
        sum(r.start_ok for r in runs) / n,
    )


def calibration(
    space: Space, runs: Sequence[SimRun], lo: float, hi: float
) -> tuple[int, float, float]:
    """(skills seen, mean marginal, observed known-rate) among skills with marginal in [lo, hi)."""
    marks, hits = [], []
    for run in runs:
        for i, s in enumerate(space.skills):
            if lo <= run.marginals[s] < hi:
                marks.append(run.marginals[s])
                hits.append(float(run.truth >> i & 1))
    if not marks:
        return 0, 0.0, 0.0
    return len(marks), sum(marks) / len(marks), sum(hits) / len(hits)


# name -> (true base, structure-violation rate)
SCENARIOS = {
    "matched": (0.6, 0.0),
    "truth_low": (0.3, 0.0),
    "truth_high": (0.9, 0.0),
    "violations5": (0.6, 0.05),
}


def run_cell(
    space: Space, cfg: ProbeConfig, rng: Rng, students: int, scenario: str, cap: int
) -> list[SimRun]:
    base, viol = SCENARIOS[scenario]
    items = make_items(space, cfg)
    truths = [draw_truth(space, cfg, rng, base=base, violation=viol) for _ in range(students)]
    return [run_probe(space, t, items, cfg, rng, cap=cap) for t in truths]


HEADER = [
    "graph",
    "scenario",
    "cap",
    "students",
    "mean_questions",
    "skill_accuracy",
    "start_ok",
    "calib_n",
    "calib_mean_marginal",
    "calib_known_rate",
]


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Probe accuracy versus questions (CSV on stdout)")
    ap.add_argument("--students", type=int, default=200)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--min-cap", type=int, default=4)
    ap.add_argument("--max-cap", type=int, default=16)
    ap.add_argument("--graph", choices=sorted(standard_graphs()), default=None)
    args = ap.parse_args(argv)
    cfg = load_probe_config()
    out = csv.writer(sys.stdout, lineterminator="\n")
    out.writerow(HEADER)
    for gname, (skills, prereqs) in standard_graphs().items():
        if args.graph not in (None, gname):
            continue
        space = build_space(skills, prereqs, max_states=cfg.max_states)
        for scenario in SCENARIOS:
            for cap in range(args.min_cap, args.max_cap + 1):
                runs = run_cell(space, cfg, SplitMix(args.seed), args.students, scenario, cap)
                st = cell_stats(runs)
                n, mean_m, rate = calibration(space, runs, 0.8, 0.9)
                out.writerow(
                    [gname, scenario, cap, st.students, f"{st.mean_questions:.3f}"]
                    + [f"{st.skill_accuracy:.4f}", f"{st.start_ok:.4f}", n]
                    + [f"{mean_m:.4f}", f"{rate:.4f}"]
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
