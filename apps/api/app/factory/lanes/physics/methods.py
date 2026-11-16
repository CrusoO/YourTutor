"""Two independent Methods that compute the answer from the SPEC alone (never from the witness).

ClosedForm (group `closed_form`): the variant's closed-form expression evaluated in exact
fractions, with its OWN prefix table and its OWN hand-written sign rules.

SympyLaws (group `sympy.laws`): solves the variant's law equations with SymPy, converts every
quantity to SI with the KERNEL unit table, applies the sign convention table from convention.py,
checks that each law is dimensionally homogeneous and that the answer unit has the dimension of
the quantity asked for.

Both fail closed (any exception is a rejection). A constant must be given as a reference into the
house constants table, never as a typed number.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from fractions import Fraction
from functools import lru_cache
from typing import Any

import sympy

from app.factory.kernel.constants import constant
from app.factory.kernel.exact import frac
from app.factory.lanes.physics import convention
from app.factory.lanes.physics.models import ALL_MODELS
from app.factory.lanes.physics.quantities import evaluate, fstr, to_si, unit_si

# ---------------------------------------------------------------- shared answer shape


def answer_dict(find: str, value: Fraction, unit: str, nature: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"values": {find: fstr(value)}, "unit": unit}
    if nature is not None:
        out["nature"] = nature
    return out


def nature_label(family: str, v: Fraction, m: Fraction) -> str:
    """Real or virtual, erect or inverted, magnified or diminished, from signed v and m."""
    if abs(m) == 1:
        raise ValueError("same-size image is outside this item family")
    real = v < 0 if family == "mirror" else v > 0
    return ", ".join(
        (
            "real" if real else "virtual",
            "inverted" if m < 0 else "erect",
            "magnified" if abs(m) > 1 else "diminished",
        )
    )


def _spec(spec: Mapping[str, Any]) -> Mapping[str, Any]:
    phys = spec["physics"]
    if not isinstance(phys, dict):
        raise ValueError("no physics block")
    return phys


def _check_givens(phys: Mapping[str, Any]) -> tuple[Any, Any]:
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

_A_FACTOR: dict[str, Fraction] = {
    "A": Fraction(1), "mA": Fraction(1, 1000), "V": Fraction(1), "mV": Fraction(1, 1000),
    "kV": Fraction(1000), "ohm": Fraction(1), "kohm": Fraction(1000), "W": Fraction(1),
    "kW": Fraction(1000), "J": Fraction(1), "kJ": Fraction(1000), "kWh": Fraction(3600000),
    "C": Fraction(1), "s": Fraction(1), "min": Fraction(60), "h": Fraction(3600),
    "m": Fraction(1), "cm": Fraction(1, 100), "mm": Fraction(1, 1000), "m^2": Fraction(1),
    "mm^2": Fraction(1, 1000000), "cm^2": Fraction(1, 10000), "ohm*m": Fraction(1),
    "D": Fraction(1), "unit": Fraction(1), "m/s": Fraction(1),
}  # fmt: skip


def a_sign(device: str, role: str) -> int:
    """Hand-written sign rules (a second copy of the convention, written separately)."""
    if role == "magnitude":
        return 1
    convex = device.startswith("convex")
    mirror = device.endswith("mirror")
    if role in ("focal", "power"):
        return 1 if convex else -1
    if role in ("height_object", "height_image_erect"):
        return 1
    if role == "height_image_inverted":
        return -1
    if role == "object_distance":
        return -1
    if role == "image_real":
        return -1 if mirror else 1
    if role == "image_virtual":
        return 1 if mirror else -1
    raise ValueError(f"unknown role {role}")


def _a_env(phys: Mapping[str, Any], model: Any) -> dict[str, Fraction]:
    env: dict[str, Fraction] = {}
    for sym, q in phys["given"].items():
        if "const" in q:
            c = constant(q["const"])
            env[sym] = frac(c.value) * _A_FACTOR[c.unit]
            continue
        value = frac(q["value"]) * _A_FACTOR[q["unit"]]
        role = q.get("role")
        if role:
            value *= a_sign(q.get("device") or phys["device"], role)
        env[sym] = value
    if phys.get("find_role"):
        env["s"] = Fraction(a_sign(phys["device"], phys["find_role"]))
    return env


class ClosedForm:
    id, version, independence_group = "phys.closed_form", "1", "closed_form"
    technique = ""

    def __init__(self, technique: str = "") -> None:
        self.technique = technique

    def solve(self, spec: Mapping[str, Any]) -> dict[str, Any]:
        phys = _spec(spec)
        model, variant = _check_givens(phys)
        env = _a_env(phys, model)
        unit = str(phys["answer_unit"])
        if unit_si(unit)[1] != unit_si(model.syms[variant.find])[1]:
            raise ValueError("answer unit has the wrong dimension")
        si = evaluate(variant.expr, env)
        nature = None
        if variant.nature:
            m = -si / env["u"] if variant.nature == "mirror" else si / env["u"]
            nature = nature_label(variant.nature, si, m)
        return answer_dict(variant.find, si / _A_FACTOR[unit], unit, nature)


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
        if not e.is_Rational:
            raise ValueError("non-rational power in a law")
        frac_e = Fraction(int(e.p), int(e.q))
        return tuple(frac_e * x for x in _dim_of(expr.base, dims))
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
            if isinstance(node.op, ast.Pow) and isinstance(node.right, ast.Constant):
                return a**b
        raise ValueError(f"unsupported law syntax: {text!r}")

    return build(ast.parse(text, mode="eval"))


@lru_cache(maxsize=256)
def _prepared(model_id: str, variant_id: str) -> tuple[Any, ...]:
    model = ALL_MODELS[model_id]
    variant = model.variants[variant_id]
    laws = variant.laws if variant.laws is not None else model.laws
    names = {n for law in laws for n in _law(law, _syms(model)).free_symbols}
    symbols = _syms(model)
    sym_dims = {
        symbols[s]: tuple(Fraction(x) for x in unit_si(u)[1]) for s, u in model.syms.items()
    }
    exprs = [_law(law, symbols) for law in laws]
    for e in exprs:
        _dim_of(e, sym_dims)
    given_names = set(variant.needs) | set(model.consts)
    if model.id == "LIGHT.SIGN":
        given_names.add("s")
    unknown = [s for s in names if s.name not in given_names]
    sols = sympy.solve(exprs, unknown, dict=True)
    if len(sols) != 1 or symbols[variant.find] not in sols[0]:
        raise ValueError("laws do not determine the unknown uniquely")
    extra = symbols.get("m") if variant.nature else None
    extra_expr = sols[0].get(extra) if extra is not None else None
    return symbols, sols[0][symbols[variant.find]], sym_dims, extra_expr, symbols.get("u")


def _syms(model: Any) -> dict[str, sympy.Symbol]:
    kw: dict[str, Any] = {"real": True} if model.signed else {"positive": True}
    return {s: sympy.Symbol(s, **kw) for s in model.syms}


def _to_fraction(x: sympy.Expr) -> Fraction:
    if not x.is_Rational:
        raise ValueError("result is not rational")
    return Fraction(int(x.p), int(x.q))


class SympyLaws:
    id, version, independence_group = "phys.sympy_laws", "1", "sympy.laws"
    technique = ""

    def __init__(self, technique: str = "") -> None:
        self.technique = technique

    def solve(self, spec: Mapping[str, Any]) -> dict[str, Any]:
        phys = _spec(spec)
        model, variant = _check_givens(phys)
        symbols, target, sym_dims, extra, _ = _prepared(model.id, variant.id)
        values: dict[sympy.Symbol, sympy.Expr] = {}
        for sym, q in phys["given"].items():
            if "const" in q:
                c = constant(q["const"])
                si = to_si(c.value, c.unit)
                dim = unit_si(c.unit)[1]
            else:
                si = to_si(q["value"], q["unit"])
                dim = unit_si(q["unit"])[1]
                role = q.get("role")
                if role:
                    si *= convention.role_sign(q.get("device") or phys["device"], role)
            if tuple(Fraction(x) for x in dim) != sym_dims[symbols[sym]]:
                raise ValueError(f"{sym} has the wrong unit dimension")
            values[symbols[sym]] = sympy.Rational(si.numerator, si.denominator)
        if phys.get("find_role"):
            s = convention.role_sign(phys["device"], phys["find_role"])
            values[symbols["s"]] = sympy.Integer(s)
        unit = str(phys["answer_unit"])
        factor, adim = unit_si(unit)
        if tuple(Fraction(x) for x in adim) != sym_dims[symbols[variant.find]]:
            raise ValueError("answer unit has the wrong dimension")
        si_value = _to_fraction(target.subs(values))
        nature = None
        if variant.nature and extra is not None:
            m = _to_fraction(
                extra.subs(
                    {
                        **values,
                        symbols["v"]: sympy.Rational(si_value.numerator, si_value.denominator),
                    }
                )
            )
            nature = nature_label(variant.nature, si_value, m)
        return answer_dict(variant.find, si_value / factor, unit, nature)
