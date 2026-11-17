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


MAX_VALUES_PER_AXIS = 5  # a variant needs a handful of items, not the whole box to be certified


def shrink_box(box: Mapping[str, Any], limit: int = MAX_VALUES_PER_AXIS) -> dict[str, Any]:
    """The same box with at most `limit` evenly spread values per axis (as explicit choices).

    A smaller declared box means a smaller certificate (it covers exactly the shrunken box) and a
    certification that takes seconds, not hours. Items are drawn only from this box.
    """
    from app.factory.kernel.certify import box_axes

    out: dict[str, Any] = {}
    for name, values in box_axes(dict(box)):
        if len(values) > limit:
            picks = sorted({round(i * (len(values) - 1) / (limit - 1)) for i in range(limit)})
            values = [values[i] for i in picks]
        out[name] = {"choices": list(values)}
    return out


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
