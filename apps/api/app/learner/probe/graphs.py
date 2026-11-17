"""Standard prerequisite graphs for the simulation (test support)."""

from __future__ import annotations

SPEC_GRAPH: dict[str, list[str]] = {  # the 12-skill graph of the spec (42 closed states)
    "C": ["A"], "D": ["A", "B"], "E": ["B"], "F": ["C"], "G": ["C", "D"], "H": ["E"],
    "I": ["F", "G"], "J": ["H", "G"], "K": ["I", "J"], "L": ["J"],
}  # fmt: skip


def standard_graphs() -> dict[str, tuple[tuple[str, ...], dict[str, list[str]]]]:
    chain = tuple(f"c{i:02d}" for i in range(12))
    wide = tuple(f"w{i:02d}" for i in range(12))  # 3 layers of 4; each needs two of the layer above
    wide_pre = {
        wide[i]: [wide[(i // 4 - 1) * 4 + (i % 4 + j) % 4] for j in range(2)] for i in range(4, 12)
    }
    return {
        "chain12": (chain, {chain[i]: [chain[i - 1]] for i in range(1, 12)}),
        "wide3": (wide, wide_pre),
        "diamond": (("a", "b", "c", "d"), {"b": ["a"], "c": ["a"], "d": ["b", "c"]}),
        "spec12": (tuple("ABCDEFGHIJKL"), SPEC_GRAPH),
    }
