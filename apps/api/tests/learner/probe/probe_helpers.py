"""Shared fixtures for the probe tests: the real config and a small 6-skill graph."""

from __future__ import annotations

from app.learner.probe.config import load_probe_config
from app.learner.probe.prior import initial_belief
from app.learner.probe.space import build_space
from app.learner.probe.types import Answer, Belief, ProbeConfig, ProbeItem, Space
from app.learner.probe.update import item_params

CFG = load_probe_config()

# a -> b -> d, a -> c -> d, e standalone (a diamond plus an island); f needs e.
GRAPH = {"b": ["a"], "c": ["a"], "d": ["b", "c"], "f": ["e"]}
SKILLS = ["a", "b", "c", "d", "e", "f"]


def space_of(skills: list[str] = SKILLS, graph: dict | None = None) -> Space:
    return build_space(skills, GRAPH if graph is None else graph, max_states=20000)


def typed_items(skills: list[str], per_skill: int = 1, cfg: ProbeConfig = CFG) -> list[ProbeItem]:
    return [item_params(f"{s}{n}", s, cfg) for s in skills for n in range(per_skill)]


def fresh(skills: list[str] = SKILLS, graph: dict | None = None) -> Belief:
    return initial_belief(space_of(skills, graph), CFG)


def ans(item: ProbeItem, correct: bool = True, **kw: bool) -> Answer:
    return Answer(item.item_id, item.skill_id, correct and not kw.get("dont_know", False), **kw)
