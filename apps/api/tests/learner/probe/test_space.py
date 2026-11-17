from __future__ import annotations

import dataclasses

import pytest
from probe_helpers import CFG, GRAPH, SKILLS, space_of

from app.learner.probe.config import config_from_mapping, load_probe_config
from app.learner.probe.prior import initial_belief, mixture_weights_for
from app.learner.probe.space import build_space, implied_prerequisites, shrink_skills
from app.learner.probe.types import ProbeConfig, TooManyStates


def closed(space, skill_graph) -> bool:
    idx = {s: i for i, s in enumerate(space.skills)}
    for state in space.states:
        for s, ps in skill_graph.items():
            if s in idx and state >> idx[s] & 1:
                assert all(state >> idx[p] & 1 for p in ps if p in idx)
    return True


def test_diamond_island_states_are_closed_and_counted() -> None:
    space = space_of()
    # diamond a,b,c,d has 6 closed states; island e,f has 3 (none, e, e+f)
    assert len(space.states) == 6 * 3
    assert len(set(space.states)) == len(space.states)
    assert closed(space, GRAPH)
    assert space.depth == (0, 1, 1, 2, 0, 1)


def test_boundary_graphs() -> None:
    empty = build_space([], {}, max_states=10)
    assert empty.states == (0,)
    one = build_space(["x"], {}, max_states=10)
    assert one.states == (0, 1)
    disjoint = build_space(["x", "y", "z"], {}, max_states=10)
    assert len(disjoint.states) == 8


def test_chain_has_n_plus_one_states() -> None:
    chain = {f"s{i}": [f"s{i - 1}"] for i in range(1, 12)}
    space = build_space([f"s{i}" for i in range(12)], chain, max_states=100)
    assert len(space.states) == 13


def test_duplicate_edges_and_skills_and_outside_prereqs_are_harmless() -> None:
    graph = {"b": ["a", "a"], "c": ["outside"]}
    space = build_space(["a", "b", "b", "c"], graph, max_states=100)
    assert space.skills == ("a", "b", "c")
    assert len(space.states) == 6  # {a,b chain: 3} x {c free: 2}


def test_cycle_is_rejected() -> None:
    with pytest.raises(ValueError, match="cycle"):
        build_space(["a", "b"], {"a": ["b"], "b": ["a"]}, max_states=10)
    with pytest.raises(ValueError, match="cycle"):
        build_space(["a"], {"a": ["a"]}, max_states=10)


def test_too_many_states_raises() -> None:
    with pytest.raises(TooManyStates):
        build_space([f"s{i}" for i in range(6)], {}, max_states=63)
    assert len(build_space([f"s{i}" for i in range(6)], {}, max_states=64).states) == 64


def test_graph_hash_changes_with_edges_not_with_order_of_dict() -> None:
    a = build_space(SKILLS, GRAPH, max_states=1000)
    b = build_space(SKILLS, dict(reversed(list(GRAPH.items()))), max_states=1000)
    c = build_space(SKILLS, {**GRAPH, "e": ["a"]}, max_states=1000)
    assert a.graph_hash == b.graph_hash != c.graph_hash


def test_implied_prerequisites_are_transitive() -> None:
    space = space_of()
    needs = implied_prerequisites(space)
    d, a = space.index("d"), space.index("a")
    assert needs[d] >> a & 1
    assert needs[a] == 0


def test_shrink_skills_takes_nearest_ancestors_first_and_respects_cap() -> None:
    chain = {"c": ["b"], "b": ["a"], "a": ["z"]}
    assert shrink_skills(["c"], chain, levels=1, cap=10) == ("c", "b")
    assert shrink_skills(["c"], chain, levels=5, cap=10) == ("c", "b", "a", "z")
    assert shrink_skills(["c"], chain, levels=5, cap=2) == ("c", "b")
    with pytest.raises(ValueError):
        shrink_skills(["c"], chain, levels=1, cap=0)


def test_prior_is_a_distribution_and_deeper_skills_are_less_likely() -> None:
    belief = initial_belief(space_of(), CFG)
    assert sum(belief.weights) == pytest.approx(1.0)
    assert sum(belief.mixture) == pytest.approx(1.0)
    assert belief.mixture == pytest.approx((1 / 3, 1 / 3, 1 / 3))
    from app.learner.probe.select import marginals

    m = marginals(belief)
    assert m["a"] > m["b"] > m["d"]


def test_mixture_weights_for_tap_values() -> None:
    assert mixture_weights_for(None, CFG) == pytest.approx((1 / 3, 1 / 3, 1 / 3))
    assert mixture_weights_for(2, CFG) == pytest.approx((0.15, 0.35, 0.50))
    assert mixture_weights_for(0, CFG) == pytest.approx((0.25, 0.45, 0.30))
    assert mixture_weights_for(-4, CFG) == pytest.approx((0.50, 0.35, 0.15))


def test_given_weights_are_validated_and_floored() -> None:
    space = space_of()
    with pytest.raises(ValueError):
        initial_belief(space, CFG, [0.5, 0.5])
    with pytest.raises(ValueError):
        initial_belief(space, CFG, [1.0, -0.1, 0.1])
    belief = initial_belief(space, CFG, [1.0, 0.0, 0.0])
    assert min(belief.mixture) >= CFG.mixture_floor - 1e-12


def test_config_loads_and_validates() -> None:
    assert load_probe_config() is load_probe_config()  # cached
    assert CFG.prior_bases == (0.3, 0.6, 0.9)
    assert CFG.cap_items == 12
    base = dataclasses.asdict(CFG)
    with pytest.raises(ValueError, match="unknown"):
        config_from_mapping({**base, "slp": 0.1})
    with pytest.raises(ValueError, match="invalid"):
        config_from_mapping({k: v for k, v in base.items() if k != "slip"})


@pytest.mark.parametrize(
    "change",
    [
        {"slip": 0.0},
        {"slip": 0.7, "guess_typed": 0.4},
        {"idk_known": 0.6},
        {"mixture_floor": 0.4},
        {"prior_bases": ()},
        {"resolve_lo": 0.6},
        {"cap_items_wide": 5},
        {"cap_items": 0},
        {"seed_cap": 1.5},
        {"guess_mcq_floor": 0.4},
    ],
)
def test_config_rejects_bad_values(change: dict) -> None:
    with pytest.raises(ValueError):
        dataclasses.replace(CFG, **change)


def test_config_type_is_frozen() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        CFG.slip = 0.5  # type: ignore[misc]
    assert isinstance(CFG, ProbeConfig)
