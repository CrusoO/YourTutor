"""Derived templates: the same certified model used for another pool or framing.

A variant is a copy of a `factory-template/1` file with a new id and `variant: <kind>`. It is
certified and stamped through the normal commands, so its items carry their own certificate and
ledger entries; nothing is typed by hand. Kinds:

- `diagnostic`: pool diagnostic (the probe warm-up draws from it).
- `explain`: role explain, a classmate's wrong answer is quoted and the learner chooses the
  correct answer (the evidence is calculation-checked; it is NOT a "why" explanation).
- `checkpoint`: pool checkpoint (the matched A and B forms are built from these).
"""

from __future__ import annotations

import copy
from collections.abc import Iterable, Mapping
from typing import Any

KINDS: dict[str, dict[str, str]] = {
    "diagnostic": {"pool": "diagnostic", "suffix": "DX", "role": ""},
    "explain": {"pool": "practice", "suffix": "EX", "role": "explain"},
    "checkpoint": {"pool": "checkpoint", "suffix": "CP", "role": ""},
}


MAX_VALUES_PER_AXIS = 5
MAX_TUPLES = 120  # a variant needs a handful of items, not the whole box to be certified


def shrink_box(box: Mapping[str, Any], limit: int = MAX_VALUES_PER_AXIS) -> dict[str, Any]:
    """The same box with few evenly spread values per axis (as explicit choices).

    At most `limit` values per axis, and the limit drops (to a minimum of 2) until the box holds
    at most MAX_TUPLES tuples. A smaller declared box means a smaller certificate (it covers
    exactly the shrunken box) and a certification that takes seconds, not hours. Items are drawn
    only from this box.
    """
    from app.factory.kernel.certify import box_axes

    axes = box_axes(dict(box))

    def pick(values: list[Any], n: int) -> list[Any]:
        if len(values) <= n:
            return list(values)
        return [
            values[i] for i in sorted({round(k * (len(values) - 1) / (n - 1)) for k in range(n)})
        ]

    while True:
        picked = {name: pick(list(values), limit) for name, values in axes}
        size = 1
        for values in picked.values():
            size *= len(values)
        if size <= MAX_TUPLES or limit <= 2:
            return {name: {"choices": values} for name, values in picked.items()}
        limit -= 1


def derive(template: Mapping[str, Any], kind: str) -> dict[str, Any]:
    """The variant of one template. Multiple-choice only where the box offers a choice of form."""
    spec = KINDS[kind]
    out = copy.deepcopy(dict(template))
    out["id"] = f"{template['id']}.{spec['suffix']}"
    if "short" in out:
        out["short"] = f"{template['short']}.{spec['suffix']}"
    out["variant"] = kind
    box = out.get("box", {})
    form = box.get("form")
    if isinstance(form, dict) and "mcq1" in (form.get("choices") or []):
        form["choices"] = ["mcq1"]  # options are needed to name the wrong answer and to key it
    out["box"] = shrink_box(box)
    return out


def one_per_skill(templates: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """The first template (by id) of each skill: a stable choice, so reruns write the same files."""
    chosen: dict[str, Mapping[str, Any]] = {}
    for template in sorted(templates, key=lambda t: str(t["id"])):
        if template.get("variant"):
            continue
        chosen.setdefault(str(template["skill_id"]), template)
    return [chosen[k] for k in sorted(chosen)]
