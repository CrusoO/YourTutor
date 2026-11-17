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


def derive(template: Mapping[str, Any], kind: str) -> dict[str, Any]:
    """The variant of one template. Multiple-choice only where the box offers a choice of form."""
    spec = KINDS[kind]
    out = copy.deepcopy(dict(template))
    out["id"] = f"{template['id']}.{spec['suffix']}"
    if "short" in out:
        out["short"] = f"{template['short']}.{spec['suffix']}"
    out["variant"] = kind
    form = out.get("box", {}).get("form")
    if isinstance(form, dict) and "mcq1" in (form.get("choices") or []):
        form["choices"] = ["mcq1"]  # options are needed to name the wrong answer and to key it
    return out


def one_per_skill(templates: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """The first template (by id) of each skill: a stable choice, so reruns write the same files."""
    chosen: dict[str, Mapping[str, Any]] = {}
    for template in sorted(templates, key=lambda t: str(t["id"])):
        if template.get("variant"):
            continue
        chosen.setdefault(str(template["skill_id"]), template)
    return [chosen[k] for k in sorted(chosen)]
