"""Fault injection: seed known-wrong items and prove the checkers reject every one.

Each Fault class turns a known-good ItemContext into mutants that are WRONG by construction (a
mutant that happened to stay correct would be a harness bug, so mutators only make changes that
provably break the item). `run_fault_injection` reports, per class, how many mutants were applied,
how many the whole pipeline rejected and how many each claiming checker rejected on its own. The
release rule: 100 percent per class, and a class that never applied is reported, not hidden.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any
from unittest import mock

from app.factory.checkers import Method1
from app.factory.kernel import constants, units
from app.factory.kernel import kinematics as kin
from app.factory.kernel.exact import chash, frac, is_number_text, round_half_up
from app.factory.kernel.stoichiometry import molar_mass, parse_formula
from app.factory.pipeline import default_checkers, run
from app.factory.registry import FAIL, ItemContext

Mutator = Callable[[ItemContext], list[ItemContext]]


@dataclass(frozen=True)
class Fault:
    id: str
    description: str
    mutate: Mutator
    catchers: tuple[str, ...]  # checker ids that must each reject the mutant on their own


# ---------------------------------------------------------------- helpers


def _clone(ctx: ItemContext) -> ItemContext:
    return copy.deepcopy(ctx)


def _with_answer(ctx: ItemContext, answer: dict[str, Any]) -> ItemContext:
    """A lane that is consistently wrong: the key option carries the same wrong answer."""
    out = _clone(ctx)
    out.answer = answer
    for option in out.options:
        if option["id"] == out.key_option:
            option["value"] = copy.deepcopy(answer)
    return out


def _bump(value: Any) -> Any:
    """Add 1 to the first number found (used to corrupt a method's answer)."""
    if isinstance(value, dict):
        out = dict(value)
        for key in out:
            changed = _bump(out[key])
            if changed != out[key]:
                out[key] = changed
                return out
        return out
    if isinstance(value, list):
        out_list = list(value)
        for i, item in enumerate(out_list):
            changed = _bump(item)
            if changed != item:
                out_list[i] = changed
                return out_list
        return out_list
    if isinstance(value, int) and not isinstance(value, bool):
        return value + 1
    if isinstance(value, str) and is_number_text(value):
        return str(frac(value) + 1)
    return value


def _kind(ctx: ItemContext) -> tuple[str, str]:
    return ctx.spec.get("domain", ""), ctx.spec.get("kind", "")


# ---------------------------------------------------------------- mutators


def sign_flip(ctx: ItemContext) -> list[ItemContext]:
    domain, kind = _kind(ctx)
    out: list[ItemContext] = []
    if domain == "algebra" and kind == "polynomial":
        roots = [frac(r) for r in ctx.answer.get("roots", [])]
        if any(roots):
            flipped = {**ctx.answer, "roots": [str(r) for r in sorted(-r for r in roots)]}
            out.append(_with_answer(ctx, flipped))
            both = _with_answer(ctx, flipped)  # the witness lies consistently too
            split = both.witness["split"]
            split["roots"] = [[str(-frac(r)), m] for r, m in split["roots"]]
            out.append(both)
    elif "value" in ctx.answer and frac(ctx.answer["value"]) != 0:
        flipped = {**ctx.answer, "value": str(-frac(ctx.answer["value"]))}
        out.append(_with_answer(ctx, flipped))
    return out


def wrong_constant(ctx: ItemContext) -> list[ItemContext]:
    domain, kind = _kind(ctx)
    out: list[ItemContext] = []
    if domain == "kinematics" and any("const" in q for q in ctx.spec["given"].values()):
        literal = copy.deepcopy(ctx.spec)
        for sym, q in literal["given"].items():
            if "const" in q:  # the lane computed with g = 10 instead of the table's 9.8
                literal["given"][sym] = {"value": "10", "unit": constants.constant(q["const"]).unit}
                if frac(q.get("factor", 1)) < 0:
                    literal["given"][sym]["value"] = "-10"
        full = [c for c in kin._solve(kin._given_si(literal)) if c["t"] >= 0]
        if len(full) == 1:
            si = full[0]
            value, _ = units.from_si(si[ctx.spec["find"]], ctx.answer["unit"])
            if ctx.answer.get("dp") is not None:
                value = round_half_up(value, int(ctx.answer["dp"]))
            if str(value) != str(frac(ctx.answer["value"])):
                mutant = _with_answer(ctx, {**ctx.answer, "value": str(value)})
                mutant.witness = {k: str(v) for k, v in si.items()}
                out.append(mutant)
    elif domain == "stoichiometry" and kind == "mass":
        elements = {
            e for sp in ctx.spec["reaction"]["species"] for e in parse_formula(sp["formula"])
        }
        for element in sorted(elements):
            bad = str(frac(constants.atomic_mass(element)) + 2)  # a typo in one atomic mass
            with mock.patch.dict(constants._MASS, {element: bad}):
                value = _mass_answer(ctx.spec)
                masses = [str(molar_mass(sp["formula"])) for sp in ctx.spec["reaction"]["species"]]
            if str(value) != str(frac(ctx.answer["value"])):
                mutant = _with_answer(ctx, {**ctx.answer, "value": str(value)})
                mutant.witness = {"molar_masses": masses}
                out.append(mutant)
    return out


def _mass_answer(spec: dict[str, Any]) -> Fraction:
    sp, co = spec["reaction"]["species"], spec["reaction"]["coefficients"]
    g, t = spec["given"], spec["target"]
    mm = [molar_mass(x["formula"]) for x in sp]
    si, _ = units.to_si(g["value"], g["unit"])
    moles = si * 1000 / mm[g["index"]] if g.get("quantity", "mass") == "mass" else si
    target = moles * co[t["index"]] / co[g["index"]]
    si_out = target * mm[t["index"]] / 1000 if t["quantity"] == "mass" else target
    value, _ = units.from_si(si_out, spec["answer_unit"])
    return (
        round_half_up(value, int(spec["answer_dp"])) if spec.get("answer_dp") is not None else value
    )


_SAME_DIM = {
    "m/s": "km/h",
    "km/h": "m/s",
    "m": "km",
    "km": "m",
    "s": "min",
    "min": "s",
    "m/s^2": "cm/s^2",
    "g": "kg",
    "kg": "g",
    "mol": "mmol",
    "mmol": "mol",
    "cm": "m",
}


def unit_slip(ctx: ItemContext) -> list[ItemContext]:
    if "unit" not in ctx.answer or "value" not in ctx.answer:
        return []
    unit, out = ctx.answer["unit"], []
    if unit in _SAME_DIM:  # right dimension, wrong scale: km/h written for m/s
        out.append(_with_answer(ctx, {**ctx.answer, "unit": _SAME_DIM[unit]}))
    if frac(ctx.answer["value"]) != 0:  # value off by a power of ten, unit kept
        out.append(
            _with_answer(ctx, {**ctx.answer, "value": str(frac(ctx.answer["value"]) * 1000)})
        )
    return out


def unit_dimension_slip(ctx: ItemContext) -> list[ItemContext]:
    if "unit" not in ctx.answer:
        return []
    wrong = "m" if ctx.answer["unit"] == "s" else "s"
    return [_with_answer(ctx, {**ctx.answer, "unit": wrong})]


def off_by_one_atom(ctx: ItemContext) -> list[ItemContext]:
    domain, kind = _kind(ctx)
    if domain != "stoichiometry":
        return []
    out: list[ItemContext] = []
    for i in range(len(_species(ctx))):
        coeff = _clone(ctx)  # one coefficient off by one
        if kind == "balance":
            coeff.answer["coefficients"][i] += 1
            for option in coeff.options:
                if option["id"] == coeff.key_option:
                    option["value"] = copy.deepcopy(coeff.answer)
        else:
            coeff.spec["reaction"]["coefficients"][i] += 1
        out.append(coeff)
        atom = _clone(ctx)  # one subscript off by one
        sp = _species(atom)[i]
        sp["formula"] = re.sub(
            r"([A-Z][a-z]?)(\d*)",
            lambda m: m.group(1) + str(int(m.group(2) or 1) + 1),
            sp["formula"],
            count=1,
        )
        if kind == "balance":
            atom.witness["atom_counts"][i] = parse_formula(sp["formula"])
        else:
            atom.witness["molar_masses"] = [str(molar_mass(s["formula"])) for s in _species(atom)]
        out.append(atom)
    return out


def _species(ctx: ItemContext) -> list[dict[str, Any]]:
    spec = ctx.spec
    return spec["species"] if spec.get("kind") == "balance" else spec["reaction"]["species"]  # type: ignore[no-any-return]


def dropped_root(ctx: ItemContext) -> list[ItemContext]:
    domain, kind = _kind(ctx)
    out: list[ItemContext] = []
    if domain == "algebra" and kind == "polynomial" and ctx.answer.get("roots"):
        for i in range(len(ctx.answer["roots"])):
            kept = [r for j, r in enumerate(ctx.answer["roots"]) if j != i]
            out.append(_with_answer(ctx, {**ctx.answer, "roots": kept}))  # count left stale
            out.append(_with_answer(ctx, {"roots": kept, "count": len(kept)}))
            both = _with_answer(ctx, {"roots": kept, "count": len(kept)})
            both.witness["split"]["roots"] = [
                r for j, r in enumerate(both.witness["split"]["roots"]) if j != i
            ]
            out.append(both)
    elif domain == "genetics" and "probabilities" in ctx.answer:
        for key in ctx.answer["probabilities"]:
            rest = {k: v for k, v in ctx.answer["probabilities"].items() if k != key}
            out.append(_with_answer(ctx, {"probabilities": rest}))
    return out


def swapped_option(ctx: ItemContext) -> list[ItemContext]:
    out: list[ItemContext] = []
    others = [o for o in ctx.options if o["id"] != ctx.key_option]
    for other in others:
        moved = _clone(ctx)
        moved.key_option = other["id"]  # key points at a wrong option
        out.append(moved)
        swapped = _clone(ctx)  # two options trade values; ids stay put
        key = next(o for o in swapped.options if o["id"] == swapped.key_option)
        peer = next(o for o in swapped.options if o["id"] == other["id"])
        key["value"], peer["value"] = peer["value"], key["value"]
        out.append(swapped)
    return out


def distractor_equals_key(ctx: ItemContext) -> list[ItemContext]:
    out = []
    for other in [o for o in ctx.options if o["id"] != ctx.key_option]:
        mutant = _clone(ctx)
        peer = next(o for o in mutant.options if o["id"] == other["id"])
        peer["value"] = copy.deepcopy(mutant.answer)
        out.append(mutant)
    return out


def duplicate_distractor(ctx: ItemContext) -> list[ItemContext]:
    wrong = [o["id"] for o in ctx.options if o["id"] != ctx.key_option]
    if len(wrong) < 2:
        return []
    mutant = _clone(ctx)
    first, second = (next(o for o in mutant.options if o["id"] == w) for w in wrong[:2])
    second["value"] = copy.deepcopy(first["value"])
    return [mutant]


def hint_leaks_key(ctx: ItemContext) -> list[ItemContext]:
    if not ctx.answer_tokens:
        return []
    mutant = _clone(ctx)
    mutant.hints[0] += f" The answer is {ctx.answer_tokens[0]}."
    return [mutant]


class _FaultyMethod:
    def __init__(self, inner: Any) -> None:
        self.id, self.version = inner.id, inner.version
        self.independence_group, self.technique = inner.independence_group, inner.technique
        self._inner = inner

    def solve(self, spec: Any) -> Any:
        return _bump(self._inner.solve(spec))  # method 1 alone is wrong


def method_wrong_answer(ctx: ItemContext) -> list[ItemContext]:
    if not ctx.methods:
        return []
    mutant = _clone(ctx)
    mutant.methods[0] = _FaultyMethod(mutant.methods[0])
    return [mutant]


def single_group(ctx: ItemContext) -> list[ItemContext]:
    if not ctx.methods:
        return []
    mutant = _clone(ctx)
    for method in mutant.methods:
        method.independence_group = "kernel.exact"  # claims to be the kernel: not independent
    return [mutant]


FAULTS: tuple[Fault, ...] = (
    Fault("sign_flip", "answer sign flipped", sign_flip, ("wellposed.predicates",)),
    Fault(
        "wrong_constant", "g=10 or an atomic mass typo", wrong_constant, ("wellposed.predicates",)
    ),
    Fault(
        "unit_slip",
        "right-dimension unit slip or power of ten",
        unit_slip,
        ("wellposed.predicates",),
    ),
    Fault(
        "unit_dimension_slip",
        "answer unit has the wrong dimension",
        unit_dimension_slip,
        ("wellposed.predicates", "units.dimension"),
    ),
    Fault(
        "off_by_one_atom",
        "coefficient or subscript off by one",
        off_by_one_atom,
        ("wellposed.predicates",),
    ),
    Fault("dropped_root", "a root or outcome dropped", dropped_root, ("wellposed.predicates",)),
    Fault(
        "swapped_option",
        "key points at, or trades values with, a wrong option",
        swapped_option,
        ("answer.key_consistency",),
    ),
    Fault(
        "distractor_equals_key",
        "a distractor equals the key",
        distractor_equals_key,
        ("mcq.distractors",),
    ),
    Fault(
        "duplicate_distractor",
        "two distractors identical",
        duplicate_distractor,
        ("mcq.distractors",),
    ),
    Fault("hint_leaks_key", "hint 1 states the answer", hint_leaks_key, ("leak.hints",)),
    Fault(
        "method_wrong_answer",
        "independent method 1 returns a wrong answer",
        method_wrong_answer,
        ("verify.method_1",),
    ),
    Fault(
        "single_group",
        "methods share the kernel's independence group",
        single_group,
        ("verify.methods_2n",),
    ),
)


# ---------------------------------------------------------------- harness


@dataclass
class ClassReport:
    fault: str
    applied: int = 0
    killed: int = 0  # rejected by the whole pipeline
    by_checker: dict[str, list[int]] = field(default_factory=dict)  # id -> [applied, killed]
    survivors: list[str] = field(default_factory=list)

    @property
    def kill_rate(self) -> float | None:
        return self.killed / self.applied if self.applied else None


@dataclass
class FaultReport:
    classes: dict[str, ClassReport]
    baseline_failures: list[str]

    @property
    def perfect(self) -> bool:
        return not self.baseline_failures and all(
            c.applied > 0
            and c.killed == c.applied
            and all(k[0] == k[1] for k in c.by_checker.values())
            for c in self.classes.values()
        )

    @property
    def report_id(self) -> str:
        summary = {k: [c.applied, c.killed, c.by_checker] for k, c in sorted(self.classes.items())}
        return "FI-" + chash(summary)[:16]

    def render(self) -> str:
        lines = ["fault class | applied | killed | kill rate | per-checker"]
        for c in self.classes.values():
            rate = "n/a" if c.kill_rate is None else f"{100 * c.kill_rate:.0f}%"
            per = ", ".join(f"{k} {v[1]}/{v[0]}" for k, v in sorted(c.by_checker.items()))
            lines.append(f"{c.fault} | {c.applied} | {c.killed} | {rate} | {per}")
        return "\n".join(lines)


def _alone(checker_id: str, mutant: ItemContext) -> bool:
    """True if the named checker, run by itself on the mutant, fails it."""
    checkers = {c.id: c for c in default_checkers()}
    if checker_id == "verify.methods_2n":
        Method1().check(mutant)  # it needs method 1's results
    return bool(checkers[checker_id].check(mutant).status == FAIL)


def run_fault_injection(
    cases: Sequence[ItemContext], faults: Sequence[Fault] = FAULTS
) -> FaultReport:
    baseline = [c.item_id for c in cases if not run(_clone(c)).stampable]
    classes: dict[str, ClassReport] = {}
    for fault in faults:
        report = classes.setdefault(fault.id, ClassReport(fault.id))
        for case in cases:
            for n, mutant in enumerate(fault.mutate(case)):
                report.applied += 1
                label = f"{case.item_id}#{n}"
                if run(_clone(mutant)).rejected:
                    report.killed += 1
                else:
                    report.survivors.append(label)
                for checker_id in fault.catchers:
                    row = report.by_checker.setdefault(checker_id, [0, 0])
                    row[0] += 1
                    if _alone(checker_id, _clone(mutant)):
                        row[1] += 1
                    else:
                        report.survivors.append(f"{label}@{checker_id}")
    return FaultReport(classes, baseline)
