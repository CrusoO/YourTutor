"""Two independent Methods that compute the answer from the SPEC alone (never from the witness).

ClosedForm (group `closed_form`): the variant's closed-form expression evaluated in exact
fractions, with its OWN unit-factor table written out here (not the lane unit table).

SympyLaws (group `sympy.laws`): solves the variant's law equations with SymPy, converts every
quantity to SI with the KERNEL unit table, checks that each law is dimensionally homogeneous and
that the answer unit has the dimension of the quantity asked for.

Both fail closed (any exception is a rejection). A constant is given as a reference into the
lane constants table, never as a typed number.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from fractions import Fraction
from functools import lru_cache
from typing import Any

import sympy

from app.factory.kernel.exact import frac
from app.factory.lanes.physics_c12.consts import constant
from app.factory.lanes.physics_c12.quantities import evaluate, fstr, to_si, unit_si

# ---------------------------------------------------------------- shared answer shape


def answer_dict(find: str, value: Fraction, unit: str) -> dict[str, Any]:
    return {"values": {find: fstr(value)}, "unit": unit}


def _spec(spec: Mapping[str, Any]) -> Mapping[str, Any]:
    phys = spec["physics"]
    if not isinstance(phys, dict):
        raise ValueError("no physics block")
    return phys


def _check_givens(phys: Mapping[str, Any]) -> tuple[Any, Any]:
    from app.factory.lanes.physics_c12.models import ALL_MODELS

    model = ALL_MODELS[phys["model"]]
    variant = model.variants[phys["variant"]]
    given = phys["given"]
    if variant.find != phys["find"] or set(given) != set(variant.needs) | set(model.consts):
        raise ValueError("given quantities do not match the variant")
    for sym, cid in model.consts.items():
        if given[sym] != {"const": cid}:
            raise ValueError(f"constant {sym} must be a reference to {cid}")
    for sym in variant.needs:
        if "const" in given[sym] or "value" not in given[sym]:
            raise ValueError(f"{sym} must be a typed value")
    return model, variant


# ---------------------------------------------------------------- method A: closed form

_P = {"": Fraction(1), "p": Fraction(1, 10**12), "n": Fraction(1, 10**9),
      "u": Fraction(1, 10**6), "m": Fraction(1, 1000), "k": Fraction(1000),
      "M": Fraction(10**6)}  # fmt: skip
_BASE_F = {"V": Fraction(1), "ohm": Fraction(1), "F": Fraction(1), "H": Fraction(1),
           "T": Fraction(1), "Wb": Fraction(1), "Hz": Fraction(1), "W": Fraction(1),
           "J": Fraction(1), "C": Fraction(1), "A": Fraction(1), "m": Fraction(1),
           "s": Fraction(1), "N": Fraction(1), "Nm": Fraction(1),
           "eV": Fraction("1.6e-19")}  # fmt: skip
_SPECIAL = {
    "unit": Fraction(1), "deg": Fraction(1), "m/s": Fraction(1), "m/s^2": Fraction(1),
    "rad/s": Fraction(1), "V/m": Fraction(1), "N/C": Fraction(1), "N/m": Fraction(1),
    "N/A^2": Fraction(1), "A/m": Fraction(1), "Nm2/C2": Fraction(1), "Nm2/C": Fraction(1),
    "Nm": Fraction(1), "Cm": Fraction(1), "Am2": Fraction(1), "kgm/s": Fraction(1),
    "ohm*m": Fraction(1), "per_m3": Fraction(1), "per_m": Fraction(1), "per_K": Fraction(1),
    "per_s": Fraction(1), "m^2": Fraction(1), "cm^2": Fraction(1, 10**4),
    "mm^2": Fraction(1, 10**6), "min": Fraction(60), "h": Fraction(3600),
    "day": Fraction(86400), "yr": Fraction(31_536_000), "kg": Fraction(1),
    "g": Fraction(1, 1000), "mg": Fraction(1, 10**6), "cm": Fraction(1, 100),
    "mm": Fraction(1, 1000), "km": Fraction(1000), "Bq": Fraction(1), "fm": Fraction(1, 10**15),
    "u": Fraction("1.66e-27"), "MeV/u": Fraction("1.6e-13") / Fraction("1.66e-27"),
    "C^2/N/m^2": Fraction(1), "K": Fraction(1), "1": Fraction(1), "J*s": Fraction(1),
    "W/m^2": Fraction(1),
}  # fmt: skip


def a_factor(unit: str) -> Fraction:
    """SI per one `unit`, from this method's own table."""
    if unit in _SPECIAL:
        return _SPECIAL[unit]
    if "/" in unit:
        top, bottom = unit.rsplit("/", 1)
        return a_factor(top) / a_factor(bottom)
    for k in sorted(_P, key=len, reverse=True):
        if k and unit.startswith(k) and unit[len(k) :] in _BASE_F:
            return _P[k] * _BASE_F[unit[len(k) :]]
    if unit in _BASE_F:
        return _BASE_F[unit]
    raise ValueError(f"unknown unit {unit}")


def _a_env(phys: Mapping[str, Any]) -> dict[str, Fraction]:
    env: dict[str, Fraction] = {}
    for sym, q in phys["given"].items():
        if "const" in q:
            c = constant(q["const"])
            env[sym] = frac(c.value) * a_factor(c.unit)
        else:
            env[sym] = frac(q["value"]) * a_factor(q["unit"])
    return env


class ClosedForm:
    id, version, independence_group = "phys12.closed_form", "1", "closed_form"
    technique = ""

    def __init__(self, technique: str = "") -> None:
        self.technique = technique

    def solve(self, spec: Mapping[str, Any]) -> dict[str, Any]:
        phys = _spec(spec)
        model, variant = _check_givens(phys)
        env = _a_env(phys)
        unit = str(phys["answer_unit"])
        if unit_si(unit)[1] != unit_si(model.syms[variant.find])[1]:
            raise ValueError("answer unit has the wrong dimension")
        si = evaluate(variant.expr, env)
        return answer_dict(variant.find, si / a_factor(unit), unit)


# ---------------------------------------------------------------- method B: sympy laws

Dim = tuple[Fraction, ...]


def _dim_of(expr: sympy.Expr, dims: Mapping[sympy.Symbol, Dim]) -> Dim:
    zero: Dim = (Fraction(0),) * 6
    if isinstance(expr, sympy.Symbol):
        return dims[expr]
    if expr.is_number:
        return zero
    if isinstance(expr, sympy.Add):
        parts = {_dim_of(a, dims) for a in expr.args}
        if len(parts) != 1:
            raise ValueError("law is not dimensionally homogeneous")
        return next(iter(parts))
    if isinstance(expr, sympy.Mul):
        total = zero
        for a in expr.args:
            total = tuple(x + y for x, y in zip(total, _dim_of(a, dims), strict=True))
        return total
    if isinstance(expr, sympy.Pow):
        e = expr.exp
        if e.is_Rational:
            frac_e = Fraction(int(e.p), int(e.q))
            return tuple(frac_e * x for x in _dim_of(expr.base, dims))
        # a symbolic exponent must itself be a pure number, and then the base must be one too
        if _dim_of(e, dims) != zero or _dim_of(expr.base, dims) != zero:
            raise ValueError("a symbolic power needs a dimensionless base and exponent")
        return zero
    raise ValueError(f"unsupported term {expr!r}")


def _law(text: str, symbols: Mapping[str, sympy.Symbol]) -> sympy.Expr:
    """Build a SymPy expression from a law string with the ast module (no eval, no sympify)."""

    def build(node: ast.AST) -> sympy.Expr:
        if isinstance(node, ast.Expression):
            return build(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return sympy.Integer(node.value)
        if isinstance(node, ast.Name):
            return symbols[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -build(node.operand)
        if isinstance(node, ast.BinOp):
            a, b = build(node.left), build(node.right)
            if isinstance(node.op, ast.Add):
                return a + b
            if isinstance(node.op, ast.Sub):
                return a - b
            if isinstance(node.op, ast.Mult):
                return a * b
            if isinstance(node.op, ast.Div):
                return a / b
            if isinstance(node.op, ast.Pow):
                return a**b
        raise ValueError(f"unsupported law syntax: {text!r}")

    return build(ast.parse(text, mode="eval"))


def _syms(model: Any) -> dict[str, sympy.Symbol]:
    return {s: sympy.Symbol(s, positive=True) for s in model.syms}


@lru_cache(maxsize=256)
def _prepared(model_id: str, variant_id: str) -> tuple[Any, ...]:
    from app.factory.lanes.physics_c12.models import ALL_MODELS

    model = ALL_MODELS[model_id]
    variant = model.variants[variant_id]
    laws = variant.laws if variant.laws is not None else model.laws
    symbols = _syms(model)
    exprs = [_law(law, symbols) for law in laws]
    sym_dims = {
        symbols[s]: tuple(Fraction(x) for x in unit_si(u)[1]) for s, u in model.syms.items()
    }
    for e in exprs:
        _dim_of(e, sym_dims)
    names = {n for e in exprs for n in e.free_symbols}
    given_names = set(variant.needs) | set(model.consts)
    unknown = [s for s in names if s.name not in given_names]
    sols = sympy.solve(exprs, unknown, dict=True)
    if len(sols) != 1 or symbols[variant.find] not in sols[0]:
        raise ValueError("laws do not determine the unknown uniquely")
    return symbols, sols[0][symbols[variant.find]], sym_dims


def _to_fraction(x: sympy.Expr) -> Fraction:
    if not x.is_Rational:
        raise ValueError("result is not rational")
    return Fraction(int(x.p), int(x.q))


class SympyLaws:
    id, version, independence_group = "phys12.sympy_laws", "1", "sympy.laws"
    technique = ""

    def __init__(self, technique: str = "") -> None:
        self.technique = technique

    def solve(self, spec: Mapping[str, Any]) -> dict[str, Any]:
        phys = _spec(spec)
        model, variant = _check_givens(phys)
        symbols, target, sym_dims = _prepared(model.id, variant.id)
        values: dict[sympy.Symbol, sympy.Expr] = {}
        for sym, q in phys["given"].items():
            if "const" in q:
                c = constant(q["const"])
                si = to_si(c.value, c.unit)
                dim = unit_si(c.unit)[1]
            else:
                si = to_si(q["value"], q["unit"])
                dim = unit_si(q["unit"])[1]
            if tuple(Fraction(x) for x in dim) != sym_dims[symbols[sym]]:
                raise ValueError(f"{sym} has the wrong unit dimension")
            values[symbols[sym]] = sympy.Rational(si.numerator, si.denominator)
        unit = str(phys["answer_unit"])
        factor, adim = unit_si(unit)
        if tuple(Fraction(x) for x in adim) != sym_dims[symbols[variant.find]]:
            raise ValueError("answer unit has the wrong dimension")
        si_value = _to_fraction(target.subs(values))
        return answer_dict(variant.find, si_value / factor, unit)
