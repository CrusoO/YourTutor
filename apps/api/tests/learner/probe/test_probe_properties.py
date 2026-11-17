"""Property tests for the probe (spec section 14, properties a to j)."""

from __future__ import annotations

import dataclasses
import math

from hypothesis import given, settings
from hypothesis import strategies as st
from probe_helpers import CFG

from app.learner.probe.prior import initial_belief, mixture_weights_for
from app.learner.probe.result import summarise, to_mastery_seed
from app.learner.probe.select import choose_item, expected_gain, marginals
from app.learner.probe.space import build_space
from app.learner.probe.stop import item_cap, should_stop
from app.learner.probe.types import Answer, ProbeItem
from app.learner.probe.update import item_params, update

# derandomize: the same examples every run, so CI is stable; explore more by raising max_examples.
FAST = settings(max_examples=60, deadline=None, derandomize=True)
TOL = 1e-9


@st.composite
def graphs(draw, max_skills: int = 6):
    n = draw(st.integers(min_value=1, max_value=max_skills))
    skills = [f"s{i}" for i in range(n)]
    prereqs = {}
    for i in range(1, n):
        ps = draw(st.lists(st.sampled_from(skills[:i]), max_size=3, unique=True))
        if ps:
            prereqs[skills[i]] = ps
    return skills, prereqs


@st.composite
def scenario(draw, max_answers: int = 8, max_skills: int = 6):
    skills, prereqs = draw(graphs(max_skills))
    items = []
    for s in skills:
        for n in range(draw(st.integers(min_value=1, max_value=2))):
            options = draw(st.sampled_from([None, 2, 4]))
            multi = draw(st.booleans())
            items.append(item_params(f"{s}.{n}", s, CFG, options=options, multistep=multi))
    kinds = st.sampled_from(["right", "wrong", "idk", "rapid", "unsure"])
    steps = draw(st.lists(st.tuples(st.sampled_from(items), kinds), max_size=max_answers))
    return skills, prereqs, items, steps


def answer(item: ProbeItem, kind: str) -> Answer:
    return Answer(
        item.item_id,
        item.skill_id,
        kind in ("right", "rapid", "unsure"),
        dont_know=kind == "idk",
        rapid=kind == "rapid",
        unsure=kind == "unsure",
    )


def belief_after(skills, prereqs, steps):
    belief = initial_belief(build_space(skills, prereqs, max_states=5000), CFG)
    for item, kind in steps:
        belief = update(belief, item, answer(item, kind), CFG)
    return belief


@FAST
@given(scenario(max_answers=30))
def test_a_weights_are_a_distribution_after_any_sequence(sc) -> None:
    skills, prereqs, _, steps = sc
    belief = belief_after(skills, prereqs, steps)
    assert all(w >= 0.0 for w in belief.weights)
    assert abs(sum(belief.weights) - 1.0) < TOL
    assert abs(sum(belief.mixture) - 1.0) < TOL


@FAST
@given(scenario(max_answers=30))
def test_b_closure_prerequisite_marginal_never_below_dependent(sc) -> None:
    skills, prereqs, _, steps = sc
    marks = marginals(belief_after(skills, prereqs, steps))
    for dep, ps in prereqs.items():
        for p in ps:
            assert marks[p] >= marks[dep] - TOL


@FAST
@given(scenario(max_answers=7), st.data())
def test_c_monotone_evidence(sc, data) -> None:
    skills, prereqs, items, steps = sc
    belief = belief_after(skills, prereqs, steps)
    item = data.draw(st.sampled_from(items))
    kind = data.draw(st.sampled_from(["right", "wrong", "idk", "rapid", "unsure"]))
    before = marginals(belief)
    after = marginals(update(belief, item, answer(item, kind), CFG))
    ancestors, dependents = {item.skill_id}, {item.skill_id}
    for _ in skills:
        ancestors |= {p for s in list(ancestors) for p in prereqs.get(s, ())}
        dependents |= {d for d, ps in prereqs.items() if set(ps) & dependents}
    if kind in ("right", "rapid", "unsure"):
        assert all(after[s] >= before[s] - TOL for s in ancestors)
    else:
        assert all(after[s] <= before[s] + TOL for s in dependents)


@FAST
@given(scenario(max_answers=6), st.randoms(use_true_random=False))
def test_d_order_invariance(sc, rng) -> None:
    skills, prereqs, _, steps = sc
    shuffled = list(steps)
    rng.shuffle(shuffled)
    one = belief_after(skills, prereqs, steps)
    two = belief_after(skills, prereqs, shuffled)
    assert all(abs(a - b) < TOL for a, b in zip(one.weights, two.weights, strict=True))
    assert all(abs(a - b) < TOL for a, b in zip(one.mixture, two.mixture, strict=True))


@FAST
@given(scenario(max_answers=6))
def test_e_expected_gain_nonnegative(sc) -> None:
    skills, prereqs, items, steps = sc
    belief = belief_after(skills, prereqs, steps)
    assert all(expected_gain(belief, it) >= 0.0 for it in items)


@FAST
@given(scenario(max_answers=0), st.integers(min_value=0, max_value=40), st.randoms())
def test_f_choose_item_respects_used_cap_and_mcq_rule(sc, seed_steps, rng) -> None:
    skills, prereqs, items, _ = sc
    belief = initial_belief(build_space(skills, prereqs, max_states=5000), CFG)
    used: set[str] = set()
    counts: dict[str, int] = {}
    last_mcq = False
    for _ in range(seed_steps % 14):
        item = choose_item(belief, items, frozenset(used), counts, last_mcq, CFG)
        if item is None:
            break
        assert item.item_id not in used
        assert counts.get(item.skill_id, 0) < CFG.max_per_skill
        assert not (last_mcq and item.is_mcq)
        used.add(item.item_id)
        counts[item.skill_id] = counts.get(item.skill_id, 0) + 1
        last_mcq = item.is_mcq
        kind = rng.choice(["right", "wrong", "idk"])
        belief = update(belief, item, answer(item, kind), CFG)


def _sharp(cfg=CFG):
    return dataclasses.replace(
        cfg, slip=0.001, slip_multistep=0.001, guess_typed=0.001, guess_mcq_floor=0.001
    )


@st.composite
def structured(draw):
    kind = draw(st.sampled_from(["chain", "antichain", "diamond"]))
    n = draw(st.integers(min_value=2, max_value=6))
    if kind == "chain":
        skills = [f"s{i}" for i in range(n)]
        return skills, {skills[i]: [skills[i - 1]] for i in range(1, n)}
    if kind == "antichain":
        return [f"s{i}" for i in range(n)], {}
    return ["a", "b", "c", "d"], {"b": ["a"], "c": ["a"], "d": ["b", "c"]}


@FAST
@given(structured(), st.data())
def test_g_posterior_mode_finds_the_true_state_quickly(graph, data) -> None:
    cfg = _sharp()
    skills, prereqs = graph
    space = build_space(skills, prereqs, max_states=5000)
    truth = data.draw(st.sampled_from(space.states))
    items = [item_params(f"{s}.0", s, cfg) for s in skills]
    belief = initial_belief(space, cfg)
    used: set[str] = set()
    counts: dict[str, int] = {}
    limit = math.ceil(math.log2(len(space.states))) + 2
    for asked in range(1, limit + 1):
        item = choose_item(belief, items, frozenset(used), counts, False, cfg)
        if item is None:
            break
        used.add(item.item_id)
        counts[item.skill_id] = counts.get(item.skill_id, 0) + 1
        known = bool(truth >> space.index(item.skill_id) & 1)
        belief = update(belief, item, Answer(item.item_id, item.skill_id, known), cfg)
        mode = space.states[max(range(len(space.states)), key=lambda k: belief.weights[k])]
        if mode == truth:
            break
    else:
        mode = space.states[max(range(len(space.states)), key=lambda k: belief.weights[k])]
    assert mode == truth


@FAST
@given(st.one_of(st.none(), st.integers(min_value=-(10**6), max_value=10**6)))
def test_h_mixture_weights_floor_and_sum(delta) -> None:
    w = mixture_weights_for(delta, CFG)
    assert len(w) == len(CFG.prior_bases)
    assert abs(sum(w) - 1.0) < TOL
    assert all(x >= CFG.mixture_floor - TOL for x in w)


@FAST
@given(scenario(max_answers=0), st.randoms())
def test_i_stopping_terminates_by_the_cap(sc, rng) -> None:
    skills, prereqs, items, _ = sc
    belief = initial_belief(build_space(skills, prereqs, max_states=5000), CFG)
    used: set[str] = set()
    counts: dict[str, int] = {}
    recent: list[Answer] = []
    asked, reason = 0, None
    for _ in range(100):  # far above any cap: the loop must break well before this
        item = choose_item(belief, items, frozenset(used), counts, False, CFG)
        gain = expected_gain(belief, item) if item else 0.0
        reason = should_stop(belief, asked, 0.0, recent, gain, CFG)
        if reason or item is None:
            break
        used.add(item.item_id)
        counts[item.skill_id] = counts.get(item.skill_id, 0) + 1
        a = answer(item, rng.choice(["right", "wrong", "idk"]))
        recent.append(a)
        belief = update(belief, item, a, CFG)
        asked += 1
    assert asked <= item_cap(len(skills), CFG)
    assert reason is not None or item is None
    assert should_stop(belief, item_cap(len(skills), CFG), 0.0, [], 1.0, CFG) is not None


@FAST
@given(scenario(max_answers=12))
def test_j_mastery_seed_stays_in_bounds(sc) -> None:
    skills, prereqs, _, steps = sc
    belief = belief_after(skills, prereqs, steps)
    result = summarise(belief, len(steps), "item_cap", CFG, skills)
    seeds = to_mastery_seed(result, CFG)
    assert set(seeds) == set(skills)
    for skill, value in seeds.items():
        assert CFG.seed_floor <= value <= CFG.seed_cap
        assert value <= max(result.marginals[skill], CFG.unclear_lo, CFG.seed_floor) + TOL
