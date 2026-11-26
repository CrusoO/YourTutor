"""Two independent Methods per item model, both computing the answer from the SPEC alone.

Method A and Method B are the model's own `solve_a` and `solve_b`: different formulations that
share no code with each other (a Punnett grid against allele shares, a closed form against a
step-by-step simulation, and so on). Each carries its own independence group, so the kernel's
rule (kernel plus at least one other group) holds twice over. Both fail closed: any exception is
a rejection, and a disagreement is never settled by a vote.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.factory.lanes.biology.models import ALL_MODELS


class BioMethod:
    version = "1"

    def __init__(self, which: str, group: str, technique: str) -> None:
        self.which = which
        self.id = group
        self.independence_group = group
        self.technique = technique

    def solve(self, spec: Mapping[str, Any]) -> Any:
        bio = spec["bio"]
        if not isinstance(bio, dict):
            raise ValueError("no bio block")
        model = ALL_MODELS[bio["model"]]
        return (model.solve_a if self.which == "a" else model.solve_b)(bio)


def methods_for(model_id: str) -> list[BioMethod]:
    model = ALL_MODELS[model_id]
    return [
        BioMethod("a", model.group_a, model.technique),
        BioMethod("b", model.group_b, model.technique_b),
    ]
