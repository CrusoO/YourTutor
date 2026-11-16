"""Data classes that describe one physics model (a relation plus its question variants).

A Model says which quantities exist, how a chosen set of nice base values gives all the others
(backward construction), and for each Variant (one unknown to find) which closed form answers
it, which named wrong procedures make distractors, and the plain words for hints and steps.
Everything is data; the verifying code lives in methods.py and lane.py.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

FORMS = ("mcq1", "num2", "num3", "case4")
MARKS = {"mcq1": 1, "num2": 2, "num3": 3, "case4": 4}

# a named wrong procedure: (misconception id, expression, kind)
# expression: SI names (G), raw display numbers (name_r), K = key in the answer unit, FA = answer
# unit factor. A leading "@" means the value is already in the answer unit.
Wrong = tuple[str, str]


@dataclass(frozen=True)
class Variant:
    id: str
    find: str
    needs: tuple[str, ...]
    expr: str  # closed form for the find, over the SI names in `needs` (and constants)
    keq: tuple[str, str]  # kernel equation: coeff * x_si = const over `needs`
    formula: str  # the relation, in words and symbols, for the hints
    ask: str
    wrongs: tuple[Wrong, ...]
    rearr: str | None = None  # the "same operation on each side" step, or None
    laws: tuple[str, ...] | None = None  # sympy laws for method C (default: the model's)
    forms: tuple[str, ...] = FORMS
    kind: str = "calc"  # calc | rule (answer follows by rule from the formula's dependencies)
    find_role: str | None = None  # signed-answer role (sign convention items)
    nature: str | None = None  # "mirror" | "lens": image nature is part of the answer


@dataclass(frozen=True)
class Model:
    id: str
    skill: str
    chapter: str  # cbse.10.physics.electricity | cbse.10.physics.light
    technique: str
    topic: str  # a short noun phrase used in stems
    syms: Mapping[str, str]  # symbol -> its SI display unit (also fixes its dimension)
    labels: Mapping[str, tuple[str, str]]  # symbol -> (noun, clause with {v})
    base: Callable[[Mapping[str, Any]], tuple[dict[str, Fraction], dict[str, str]]]
    derived: Callable[[Mapping[str, Any]], tuple[tuple[str, str], ...]]
    variants: Mapping[str, Variant]
    laws: tuple[str, ...] = ()
    consts: Mapping[str, str] = field(default_factory=dict)  # symbol -> constant id
    signed: bool = False
    dunits: Mapping[str, str] = field(default_factory=dict)  # display unit of derived symbols
    sizes: Mapping[str, tuple[Fraction, Fraction]] = field(default_factory=dict)  # plausible |x|
    extra_wrongs: Callable[[Mapping[str, Any], Variant], tuple[Wrong, ...]] | None = None
    device: Callable[[Mapping[str, Any]], str | None] | None = None
    # symbol -> (role, device or None): which sign rule a displayed magnitude follows
    roles: (
        Callable[[Mapping[str, Any], Mapping[str, Fraction]], dict[str, tuple[str, str | None]]]
        | None
    ) = None
    rule_derived: bool = False
    mc_prefix: str = "PHY.MC.ELEC"
    auto_slips: bool = True
