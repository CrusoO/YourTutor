# ruff: noqa: E501
"""Trigonometry families (Class 10): ratios, special-angle values, complements, ratio from a
ratio, and heights and distances.

Trigonometric values are not in the kernel. Each item carries a kernel-checkable model (a linear
equation, or the minimal polynomial of the answer, which for p + q*sqrt3 is a quadratic whose
discriminant 12 q^2 is never a rational square) plus three independent lane methods (closed form,
SymPy, mpmath) that compute the answer from a structured geometry or expression model.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from fractions import Fraction
from typing import Any

import mpmath
import sympy

from app.factory.kernel.exact import rational_sqrt
from app.factory.lanes.maths.core import (
    DEG,
    SQ,
    Built,
    Family,
    FnMethod,
    IllPosed,
    clamp_difficulty,
    fstr,
    pick,
)
from app.factory.lanes.maths.reference import trig as ref
from app.factory.lanes.maths.surd import S, fmt, sqrt_of

F = Fraction
TIMES = "×"
DIV = "÷"


def _slug(*parts: Any) -> str:
    return "_".join(str(x).replace("-", "m").replace("/", "d") for x in parts)


def _spec(lhs: list[Any], model: dict[str, Any]) -> dict[str, Any]:
    return {"domain": "algebra", "kind": "polynomial", "lhs": lhs, "model": model}


def scalar_part(v: Fraction) -> tuple[dict, dict, list[Any]]:
    return (
        {"roots": [fstr(v)], "count": 1},
        {"split": {"lead": 1, "roots": [[fstr(v), 1]]}},
        [fstr(-v), 1],
    )


def s_part(x: S) -> tuple[dict, dict, list[Any]]:
    """Kernel pieces for an answer in Q(sqrt3): the number itself, or its minimal polynomial."""
    if x.c[1] or x.c[3]:
        raise IllPosed("answer_outside_q_sqrt3")
    if x.is_rational:
        return scalar_part(x.c[0])
    p, q = x.c[0], x.c[2]
    lhs = [fstr(p * p - 3 * q * q), fstr(-2 * p), 1]
    return {"value": fmt(x), "count": 2}, {"discriminant": fstr(12 * q * q)}, lhs


def s_answer(x: S) -> dict[str, Any]:
    return s_part(x)[0]


def _s_rec(x: S) -> dict[str, Any]:
    return {"value": fmt(x)}


def _txt(x: S) -> str:
    return fmt(x)


def _wrong_s(cands: list[tuple[str, S]]) -> list[tuple[str, dict[str, Any], str]]:
    return [(mc, _s_rec(v), _txt(v)) for mc, v in cands]


# ---------------------------------------------------------------- 1. ratios from a triangle


NAMES = {"sin": "sine", "cos": "cosine", "tan": "tangent"}


class RatiosFromTriangle(Family):
    id = "tri_ratios"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        m, n, k, swap, ratio, which = (p[x] for x in ("m", "n", "k", "swap", "ratio", "which"))
        if not (m > n >= 1 and math.gcd(m, n) == 1 and (m - n) % 2 == 1):
            raise IllPosed("needs_a_primitive_triple")
        u, v, h = m * m - n * n, 2 * m * n, m * m + n * n
        leg_p, leg_q = (k * u, k * v) if swap == 0 else (k * v, k * u)  # PQ and QR
        # angle P: opposite QR, adjacent PQ. angle R: opposite PQ, adjacent QR.
        opp, adj = (leg_q, leg_p) if which == 0 else (leg_p, leg_q)
        hyp = k * h
        angle = "P" if which == 0 else "R"
        vals = {"sin": F(opp, hyp), "cos": F(adj, hyp), "tan": F(opp, adj)}
        key = vals[ratio]
        if key == 0:
            raise IllPosed("degenerate")
        part, witness, lhs = scalar_part(key)
        inv = {name: 1 / val for name, val in vals.items()}
        table: dict[str, list[tuple[str, Fraction]]] = {
            "sin": [("MC.TRIG.SIN_COS_MIXED", vals["cos"]), ("MC.TRIG.RATIO_INVERTED", inv["sin"]),
                    ("MC.TRIG.SIN_AS_OPP_OVER_ADJ", vals["tan"]),
                    ("MC.TRIG.SIN_AS_ADJ_OVER_OPP", inv["tan"])],
            "cos": [("MC.TRIG.SIN_COS_MIXED", vals["sin"]), ("MC.TRIG.RATIO_INVERTED", inv["cos"]),
                    ("MC.TRIG.COS_AS_ADJ_OVER_OPP", inv["tan"]),
                    ("MC.TRIG.COS_AS_OPP_OVER_ADJ", vals["tan"])],
            "tan": [("MC.TRIG.RATIO_INVERTED", inv["tan"]),
                    ("MC.TRIG.TAN_AS_OPP_OVER_HYP", vals["sin"]),
                    ("MC.TRIG.TAN_AS_ADJ_OVER_HYP", vals["cos"])],
        }  # fmt: skip
        wrong_vals = table[ratio]
        if ratio != "tan":  # the hypotenuse mistaken for the sum of the two legs
            wrong_vals.append(
                ("MC.TRIG.HYP_AS_SUM_OF_LEGS", F(opp if ratio == "sin" else adj, leg_p + leg_q))
            )
        stem = (
            f"In triangle PQR the angle at Q is a right angle, PQ = {leg_p} cm and QR = {leg_q} cm. "
            f"Find the value of {ratio} {angle}."
        )

        def closed(spec: Mapping[str, Any]) -> Any:
            md = spec["model"]
            hyp_ = ref.hyp_closed(md["pq"], md["qr"])
            o, a_ = (md["qr"], md["pq"]) if md["angle"] == "P" else (md["pq"], md["qr"])
            return scalar_part(
                {"sin": F(o) / hyp_, "cos": F(a_) / hyp_, "tan": F(o, a_)}[md["ratio"]]
            )[0]

        def sym(spec: Mapping[str, Any]) -> Any:
            md = spec["model"]
            hyp_ = sympy.sqrt(sympy.Integer(md["pq"]) ** 2 + sympy.Integer(md["qr"]) ** 2)
            o, a_ = (md["qr"], md["pq"]) if md["angle"] == "P" else (md["pq"], md["qr"])
            val = {"sin": o / hyp_, "cos": a_ / hyp_, "tan": sympy.Rational(o, a_)}[md["ratio"]]
            val = sympy.nsimplify(sympy.simplify(val))
            return scalar_part(F(int(val.p), int(val.q)))[0]

        def num(spec: Mapping[str, Any]) -> Any:
            md = spec["model"]
            o, a_ = (md["qr"], md["pq"]) if md["angle"] == "P" else (md["pq"], md["qr"])
            return scalar_part(ref.ratio_numeric(o, a_, md["ratio"]))[0]

        return Built(
            spec=_spec(
                lhs, {"family": self.id, "pq": leg_p, "qr": leg_q, "angle": angle, "ratio": ratio}
            ),
            answer=part,
            witness=witness,
            stem=stem,
            steps=[
                f"Name the sides from angle {angle}: the side opposite it, the side next to it (adjacent), and the hypotenuse.",
                f"By Pythagoras the hypotenuse PR = square root of ({leg_p}{SQ} + {leg_q}{SQ}) = {hyp}.",
                f"Opposite = {opp}, adjacent = {adj}, hypotenuse = {hyp}.",
                f"{ratio} {angle} = {'opposite / hypotenuse' if ratio == 'sin' else 'adjacent / hypotenuse' if ratio == 'cos' else 'opposite / adjacent'} = {fstr(key)}.",
            ],
            hints=[
                pick(
                    [
                        "Decide which side is opposite the angle, which is next to it, and which is the longest.",
                        "Label the three sides relative to the angle asked about, not to the triangle.",
                        "The longest side is opposite the right angle; label the other two from the angle in the question.",
                    ],
                    p,
                ),
                "Only two sides are given, so use the relation between the three sides of this "
                "triangle to find the third before forming the ratio.",
                "Full method: label opposite, adjacent and hypotenuse for the stated angle, find the "
                "missing side with the rule for right triangles, write the ratio as a fraction "
                "and simplify it.",
            ],
            wrong=[(mc, scalar_part(v)[0], fstr(v)) for mc, v in wrong_vals],
            key_text=fstr(key),
            tokens=[fstr(key)],
            difficulty=clamp_difficulty(0.3, leg_p, leg_q, steps=4),
            role="procedure",
            prediction="Is this ratio bigger or smaller than 1?",
            methods=[
                FnMethod("maths.tri.closed", "closed_form", "trig_ratio_definition", closed),
                FnMethod("maths.tri.sympy", "sympy.simplify", "", sym),
                FnMethod("maths.tri.numeric", "numeric.mpmath", "trig_ratio_definition", num),
            ],
            slug=_slug(m, n, k, swap, ratio, which),
            tags=[f"marks:{tpl['form']['marks']}", "steps:4"],
        )


# ---------------------------------------------------------------- 2. values of special angles


def _tab_val(f: str, ang: int) -> S | None:
    return {"sin": ref.SIN, "cos": ref.COS, "tan": ref.TAN}[f][ang]  # type: ignore[index]


def _exact_trig(f: str, ang: int) -> S | None:
    """Value from the side ratios of the special triangles (independent of the SIN/COS/TAN table)."""
    if ang == 0:
        return {"sin": S(0), "cos": S(1), "tan": S(0)}[f]
    if ang == 90:
        return {"sin": S(1), "cos": S(0), "tan": None}[f]
    opp, adj, hyp = ref.RATIOS[ang]
    return {"sin": opp / hyp, "cos": adj / hyp, "tan": opp / adj}[f]


def _eval_expr(model: Mapping[str, Any], val: Callable[[str, int], Any]) -> Any:
    f1, x, op, f2, y, pw = (model[k] for k in ("f1", "x", "op", "f2", "y", "pw"))
    t1, t2 = val(f1, x), val(f2, y)
    if t1 is None or t2 is None:
        raise ValueError("undefined value")
    t1, t2 = t1**pw, t2**pw
    return {"+": lambda: t1 + t2, "-": lambda: t1 - t2, "*": lambda: t1 * t2, "/": lambda: t1 / t2}[
        op
    ]()


def _term_text(f: str, ang: int, pw: int) -> str:
    return f"{f}{SQ if pw == 2 else ''} {ang}{DEG}"


OPSYM = {"+": "+", "-": "-", "*": TIMES, "/": DIV}


class TableValues(Family):
    id = "tri_table"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        f1, x, op, f2, y, pw = (p[k] for k in ("f1", "x", "op", "f2", "y", "pw"))
        model = {"family": self.id, "f1": f1, "x": x, "op": op, "f2": f2, "y": y, "pw": pw}
        if (f1, x) == (f2, y):
            raise IllPosed("two_identical_terms")
        try:
            value = _eval_expr(model, _tab_val)
        except (ValueError, ZeroDivisionError):
            raise IllPosed("undefined_or_division_by_zero") from None
        if not value.is_rational:
            raise IllPosed("answer_is_not_rational")
        key = value.rational
        part, witness, lhs = scalar_part(key)

        def swapped(f: str, ang: int) -> S | None:
            return _tab_val({"sin": "cos", "cos": "sin", "tan": "tan"}[f], ang)

        def tan_as_sin(f: str, ang: int) -> S | None:
            return _tab_val("sin" if f == "tan" else f, ang)

        cands: list[tuple[str, S]] = []

        def add(mc: str, thunk: Callable[[], S]) -> None:
            try:
                cands.append((mc, thunk()))
            except (ValueError, ZeroDivisionError, KeyError, TypeError):
                pass

        add("MC.TRIG.SWAPPED_SIN_COS_VALUES", lambda: _eval_expr(model, swapped))
        if pw == 2:
            add("MC.TRIG.SQUARE_DROPPED", lambda: _eval_expr({**model, "pw": 1}, _tab_val))
        if f1 == f2 and op == "+" and x + y <= 90 and pw == 1:
            add("MC.TRIG.ANGLES_ADDED_INSIDE", lambda: S.of(_tab_val(f1, x + y)))
        add("MC.TRIG.TAN_VALUE_AS_SIN_VALUE", lambda: _eval_expr(model, tan_as_sin))
        other = {"+": "*", "*": "+", "-": "/", "/": "-"}[op]
        add("MC.TRIG.OPERATION_MIXED_UP", lambda: _eval_expr({**model, "op": other}, _tab_val))
        stem = f"Find the value of {_term_text(f1, x, pw)} {OPSYM[op]} {_term_text(f2, y, pw)}."

        def closed(spec: Mapping[str, Any]) -> Any:
            r = _eval_expr(spec["model"], _exact_trig)
            return scalar_part(r.rational)[0]

        def sym(spec: Mapping[str, Any]) -> Any:
            def sv(f: str, ang: int) -> Any:
                if f == "tan" and ang == 90:
                    return None
                return {"sin": sympy.sin, "cos": sympy.cos, "tan": sympy.tan}[f](
                    sympy.pi * ang / 180
                )

            r = sympy.nsimplify(sympy.simplify(_eval_expr(spec["model"], sv)))
            if not r.is_Rational:
                raise ValueError("not rational")
            return scalar_part(F(int(r.p), int(r.q)))[0]

        def num(spec: Mapping[str, Any]) -> Any:
            mpmath.mp.dps = 50

            def mv(f: str, ang: int) -> Any:
                if f == "tan" and ang == 90:
                    return None
                return {"sin": mpmath.sin, "cos": mpmath.cos, "tan": mpmath.tan}[f](
                    mpmath.radians(ang)
                )

            return scalar_part(ref.rational_from_mp(_eval_expr(spec["model"], mv)))[0]

        return Built(
            spec=_spec(lhs, model),
            answer=part,
            witness=witness,
            stem=stem,
            steps=[
                "Use the exact values for 0, 30, 45, 60 and 90 degrees.",
                f"{f1} {x}{DEG} = {fmt(S.of(_tab_val(f1, x)))} and {f2} {y}{DEG} = {fmt(S.of(_tab_val(f2, y)))}.",
                *(
                    ["Square each value before combining, because the squares apply to the values."]
                    if pw == 2
                    else []
                ),
                f"Combine them: the result is {fstr(key)}.",
            ],
            hints=[
                pick(
                    [
                        "Recall the exact values of the ratios for the standard angles.",
                        "Write each ratio as its exact value first, then combine.",
                        "Replace each term by its exact value before doing any arithmetic.",
                    ],
                    p,
                ),
                "If any square sits on one ratio, square the exact value of the ratio, not the angle. "
                "Then carry out the operation between the two terms.",
                "Full method: recall the exact value of each ratio, square it where a square is "
                "shown, combine the two numbers with the stated operation, and simplify.",
            ],
            wrong=[(mc, _s_rec(v), _txt(v)) for mc, v in cands],
            key_text=fstr(key),
            tokens=[fstr(key)],
            difficulty=clamp_difficulty(0.3, steps=3 + (pw == 2)),
            role="recall",
            prediction="Will the answer be a whole number, a fraction or involve a square root?",
            methods=[
                FnMethod("maths.table.exact", "closed_form", "trig_table", closed),
                FnMethod("maths.table.sympy", "sympy.trig", "", sym),
                FnMethod("maths.table.numeric", "numeric.mpmath", "trig_table", num),
            ],
            slug=_slug(f1, x, {"+": "p", "-": "m", "*": "t", "/": "d"}[op], f2, y, pw),
            tags=[f"marks:{tpl['form']['marks']}", f"steps:{3 + (pw == 2)}"],
        )


# ---------------------------------------------------------------- 3. complementary angles


KINDS = ("ratio", "product", "difference", "sumsq", "secratio")


def _comp_expr(
    kind: str, x: Any, pi_half_minus: Callable[[Any], Any], fn: Mapping[str, Any]
) -> Any:
    y = pi_half_minus(x)
    sin, cos, tan, sec, csc = (fn[k] for k in ("sin", "cos", "tan", "sec", "csc"))
    return {
        "ratio": lambda: sin(x) / cos(y),
        "product": lambda: tan(x) * tan(y),
        "difference": lambda: cos(x) - sin(y),
        "sumsq": lambda: sin(x) ** 2 + sin(y) ** 2,
        "secratio": lambda: sec(x) / csc(y),
    }[kind]()


class Complementary(Family):
    id = "tri_complement"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        kind, x = p["kind"], p["x"]
        if x in (45, 0, 90):
            raise IllPosed("angle_pair_must_be_different")
        y = 90 - x
        key = F(0) if kind == "difference" else F(1)
        part, witness, lhs = scalar_part(key)
        text = {
            "ratio": f"sin {x}{DEG} {DIV} cos {y}{DEG}",
            "product": f"tan {x}{DEG} {TIMES} tan {y}{DEG}",
            "difference": f"cos {x}{DEG} - sin {y}{DEG}",
            "sumsq": f"sin{SQ} {x}{DEG} + sin{SQ} {y}{DEG}",
            "secratio": f"sec {x}{DEG} {DIV} cosec {y}{DEG}",
        }[kind]
        names = {F(0): "ZERO", F(1): "ONE", F(2): "TWO", F(-1): "MINUS_ONE"}
        wrong = [
            (f"MC.TRIG.COMPLEMENT_GAVE_{names[F(v)]}", scalar_part(F(v))[0], str(v))
            for v in (0, 1, 2, -1)
            if F(v) != key
        ]

        def closed(spec: Mapping[str, Any]) -> Any:
            md = spec["model"]
            vals = []
            for ang in (30, 60):  # the identity holds for every angle: test it on exact ones
                tab = {
                    "sin": lambda a: _exact_trig("sin", a),
                    "cos": lambda a: _exact_trig("cos", a),
                    "tan": lambda a: _exact_trig("tan", a),
                    "sec": lambda a: S(1) / _exact_trig("cos", a),
                    "csc": lambda a: S(1) / _exact_trig("sin", a),
                }
                vals.append(_comp_expr(md["kind"], ang, lambda t: 90 - t, tab))
            if vals[0] != vals[1] or not vals[0].is_rational:
                raise ValueError("not a constant")
            return scalar_part(vals[0].rational)[0]

        def sym(spec: Mapping[str, Any]) -> Any:
            md = spec["model"]
            t = sympy.Symbol("t", positive=True)
            fn = {"sin": sympy.sin, "cos": sympy.cos, "tan": sympy.tan, "sec": sympy.sec,
                  "csc": sympy.csc}  # fmt: skip
            expr = sympy.simplify(_comp_expr(md["kind"], t, lambda a: sympy.pi / 2 - a, fn))
            if expr.free_symbols or not expr.is_Rational:
                raise ValueError("identity did not reduce to a number")
            return scalar_part(F(int(expr.p), int(expr.q)))[0]

        def num(spec: Mapping[str, Any]) -> Any:
            md = spec["model"]
            mpmath.mp.dps = 50
            fn = {"sin": mpmath.sin, "cos": mpmath.cos, "tan": mpmath.tan, "sec": mpmath.sec,
                  "csc": mpmath.csc}  # fmt: skip
            rad = mpmath.radians(md["x"])
            val = _comp_expr(md["kind"], rad, lambda a: mpmath.pi / 2 - a, fn)
            return scalar_part(ref.rational_from_mp(val))[0]

        return Built(
            spec=_spec(lhs, {"family": self.id, "kind": kind, "x": x}),
            answer=part,
            witness=witness,
            stem=f"Find the value of {text}.",
            steps=[
                f"The angles {x}{DEG} and {y}{DEG} add up to 90{DEG}, so they are complementary.",
                "For complementary angles: sin (90 - A) = cos A, cos (90 - A) = sin A, tan (90 - A) = cot A, "
                "sec (90 - A) = cosec A.",
                f"Rewrite the second term using the first angle and simplify; the value is {key}.",
            ],
            hints=[
                pick(
                    [
                        "Look at the two angles: what do they add up to?",
                        "Check whether the two angles are complementary before calculating anything.",
                        "Try rewriting one ratio so that both terms use the same angle.",
                    ],
                    p,
                ),
                "A ratio of an angle equals the matching co-ratio of its complement. Use that to "
                "rewrite one term so both terms involve the same angle.",
                "Full method: confirm the angles add to ninety, convert one term to the other "
                "angle with the complement rule, then simplify the expression.",
            ],
            wrong=wrong,
            key_text=str(key),
            tokens=[str(key)],
            difficulty=clamp_difficulty(0.3, steps=3),
            role="apply",
            prediction="Without a calculator, do you think the answer is a surprise number?",
            methods=[
                FnMethod(
                    "maths.comp.specialise", "specialisation_exact", "complementary_angles", closed
                ),
                FnMethod("maths.comp.symbolic", "sympy.symbolic", "", sym),
                FnMethod("maths.comp.numeric", "numeric.mpmath", "complementary_angles", num),
            ],
            slug=_slug(kind, x),
            tags=[f"marks:{tpl['form']['marks']}", "steps:3"],
        )


# ---------------------------------------------------------------- 4. a ratio from a ratio


class RatioFromRatio(Family):
    id = "tri_from_ratio"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        m, n, swap, given, ask = (p[k] for k in ("m", "n", "swap", "given", "ask"))
        if given == ask:
            raise IllPosed("given_and_asked_ratio_must_differ")
        if not (m > n >= 1 and math.gcd(m, n) == 1 and (m - n) % 2 == 1):
            raise IllPosed("needs_a_primitive_triple")
        u, v, h = m * m - n * n, 2 * m * n, m * m + n * n
        opp, adj = (u, v) if swap == 0 else (v, u)
        vals = {"sin": F(opp, h), "cos": F(adj, h), "tan": F(opp, adj)}
        g, key = vals[given], vals[ask]
        # the identity relations, used to build the kernel check independently of the triple
        w = {
            ("sin", "cos"): 1 - g * g, ("sin", "tan"): g * g / (1 - g * g),
            ("cos", "sin"): 1 - g * g, ("cos", "tan"): (1 - g * g) / (g * g),
            ("tan", "sin"): g * g / (1 + g * g), ("tan", "cos"): 1 / (1 + g * g),
        }[(given, ask)]  # fmt: skip
        part = {"roots": [fstr(-key), fstr(key)], "count": 2, "value": fstr(key)}
        witness = {"split": {"lead": 1, "roots": [[fstr(-key), 1], [fstr(key), 1]]}}
        third = ({"sin", "cos", "tan"} - {given, ask}).pop()
        cands: list[tuple[str, Fraction]] = [
            ("MC.TRIG.SQUARE_NOT_ROOTED", key * key),
            ("MC.TRIG.RATIO_INVERTED", 1 / key),
            ("MC.TRIG.GIVEN_REPEATED", g),
            ("MC.TRIG.WRONG_RATIO_REPORTED", vals[third]),
        ]
        if {given, ask} == {"sin", "cos"}:
            cands.insert(0, ("MC.TRIG.PYTHAG_NOT_SQUARED", 1 - g))
        stem = f"A is an acute angle and {given} A = {fstr(g)}. Find the value of {ask} A."

        def closed(spec: Mapping[str, Any]) -> Any:
            md = spec["model"]
            gg = F(md["g"])
            ident = {
                ("sin", "cos"): 1 - gg * gg, ("sin", "tan"): gg * gg / (1 - gg * gg),
                ("cos", "sin"): 1 - gg * gg, ("cos", "tan"): (1 - gg * gg) / (gg * gg),
                ("tan", "sin"): gg * gg / (1 + gg * gg), ("tan", "cos"): 1 / (1 + gg * gg),
            }[(md["given"], md["ask"])]  # fmt: skip
            root = rational_sqrt(ident)
            assert root is not None
            return {"roots": [fstr(-root), fstr(root)], "count": 2, "value": fstr(root)}

        def sym(spec: Mapping[str, Any]) -> Any:
            md = spec["model"]
            gg = sympy.Rational(F(md["g"]).numerator, F(md["g"]).denominator)
            s_, c_ = sympy.symbols("s c", positive=True)
            eqs = [s_**2 + c_**2 - 1]
            if md["given"] == "sin":
                eqs.append(s_ - gg)
            elif md["given"] == "cos":
                eqs.append(c_ - gg)
            else:
                eqs.append(s_ - gg * c_)
            sol = sympy.solve(eqs, [s_, c_], dict=True)
            if len(sol) != 1:
                raise ValueError("no unique acute angle")
            sv, cv = sol[0][s_], sol[0][c_]
            val = {"sin": sv, "cos": cv, "tan": sv / cv}[md["ask"]]
            val = sympy.nsimplify(sympy.simplify(val))
            r = F(int(val.p), int(val.q))
            return {"roots": [fstr(-r), fstr(r)], "count": 2, "value": fstr(r)}

        def num(spec: Mapping[str, Any]) -> Any:
            md = spec["model"]
            mpmath.mp.dps = 50
            gg = mpmath.mpf(F(md["g"]).numerator) / F(md["g"]).denominator
            ang = {"sin": mpmath.asin, "cos": mpmath.acos, "tan": mpmath.atan}[md["given"]](gg)
            val = {"sin": mpmath.sin, "cos": mpmath.cos, "tan": mpmath.tan}[md["ask"]](ang)
            r = ref.rational_from_mp(val)
            return {"roots": [fstr(-r), fstr(r)], "count": 2, "value": fstr(r)}

        return Built(
            spec=_spec(
                [fstr(-w), 0, 1],
                {"family": self.id, "given": given, "ask": ask, "g": fstr(g)},
            ),
            answer=part,
            witness=witness,
            stem=stem,
            steps=[
                f"Draw a right triangle with angle A and mark the sides so that {given} A = {fstr(g)}.",
                f"Use the identity sin{SQ} A + cos{SQ} A = 1 (or tan A = sin A / cos A) to find the missing ratio.",
                f"Since A is acute, take the positive root: {ask} A = {fstr(key)}.",
            ],
            hints=[
                pick(
                    [
                        "Sketch the right triangle and mark the sides that the given ratio tells you.",
                        "A single identity connects sine and cosine of the same angle.",
                        "Because the angle is acute, every ratio is positive.",
                    ],
                    p,
                ),
                "Find the third side of your triangle with the rule for right triangles, then form "
                "the ratio you need as one fraction of the sides.",
                "Full method: choose side lengths that fit the given ratio, find the missing side, "
                "write the asked ratio from the sides, and simplify.",
            ],
            wrong=[(mc, {"value": fstr(val), "count": 2}, fstr(val)) for mc, val in cands],
            key_text=fstr(key),
            tokens=[fstr(key)],
            difficulty=clamp_difficulty(0.4, h, steps=3),
            role="apply",
            prediction="Is the asked ratio bigger or smaller than the given one?",
            methods=[
                FnMethod("maths.ratio.identity", "closed_form", "trig_identities", closed),
                FnMethod("maths.ratio.sympy", "sympy.solve", "", sym),
                FnMethod("maths.ratio.numeric", "numeric.mpmath", "trig_identities", num),
            ],
            slug=_slug(m, n, swap, given, ask),
            tags=[f"marks:{tpl['form']['marks']}", "steps:3"],
        )


# ---------------------------------------------------------------- heights and distances


def _tri_methods(tech: str) -> list[FnMethod]:
    return [
        FnMethod(
            "maths.hd.special_triangle",
            "closed_form",
            tech,
            lambda sp: s_answer(ref.tri_closed(sp["model"])),
        ),
        FnMethod(
            "maths.hd.sympy", "sympy.trig", "", lambda sp: s_answer(ref.tri_sympy(sp["model"]))
        ),
        FnMethod(
            "maths.hd.numeric",
            "numeric.mpmath",
            tech,
            lambda sp: s_answer(ref.tri_numeric(sp["model"])),
        ),
    ]


def _side_ratio(angle: int, name: str) -> S:
    opp, adj, hyp = ref.RATIOS[angle]
    return {"opposite": opp, "adjacent": adj, "hypotenuse": hyp}[name]


def _convert(angle: int, value: S, known: str, unknown: str) -> S:
    return value * _side_ratio(angle, unknown) / _side_ratio(angle, known)


def _trig_of(angle: int, f: str) -> S:
    opp, adj, hyp = ref.RATIOS[angle]
    return {"sin": opp / hyp, "cos": adj / hyp, "tan": opp / adj, "cot": adj / opp,
            "sec": hyp / adj, "csc": hyp / opp}[f]  # fmt: skip


class _HDBase(Family):
    """Backward construction in Q(sqrt3): choose the answer, derive the given quantity."""

    marks_steps = 3

    def finish(
        self,
        tpl: Mapping[str, Any],
        p: Mapping[str, Any],
        *,
        angle: int,
        known: str,
        unknown: str,
        answer: S,
        stem: str,
        steps: list[str],
        hints: list[str],
        wrong: list[tuple[str, S]],
        prediction: str,
        base: float,
        role: str,
        slug: str,
    ) -> Built:
        given = _convert(angle, answer, unknown, known)
        if given.c[1] or given.c[3]:
            raise IllPosed("given_outside_q_sqrt3")
        if answer.c[1] or answer.c[3]:
            raise IllPosed("answer_outside_q_sqrt3")
        if any(c < 0 for c in (answer.c[0], answer.c[2])) or not (answer.c[0] or answer.c[2]):
            raise IllPosed("lengths_must_be_positive")
        part, witness, lhs = s_part(answer)
        model = {"family": self.id, "kind": "right_triangle", "angle": angle, "known": known,
                 "unknown": unknown, "value": ref.s_pair(given)}  # fmt: skip
        built = Built(
            spec=_spec(lhs, model),
            answer=part,
            witness=witness,
            stem=stem.format(given=fmt(given)),
            steps=[s.format(given=fmt(given), ans=fmt(answer)) for s in steps],
            hints=hints,
            wrong=_wrong_s(wrong),
            key_text=fmt(answer),
            tokens=[fmt(answer)],
            difficulty=clamp_difficulty(base, steps=self.marks_steps),
            role=role,
            prediction=prediction,
            methods=_tri_methods("special_angle_ratios"),
            slug=slug,
            tags=[f"marks:{tpl['form']['marks']}", f"steps:{self.marks_steps}"],
        )
        return built


HD_THINGS = [
    ("tower", "A tower stands on level ground."),
    ("tree", "A tree stands on level ground."),
    ("building", "A building stands on a flat plot."),
    ("flagpole", "A flagpole stands upright on level ground."),
    ("chimney", "A factory chimney stands on level ground."),
]


def _answer_for(angle: int, k: int, kind: str) -> S:
    return S(k) if kind == "rational" else sqrt_of(3) * k


class HDHeight(_HDBase):
    id = "hd_height"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        ang, k, kind, ctx = p["ang"], p["k"], p["kind"], p["ctx"]
        if (ang == 45 and kind != "rational") or (ang == 60 and kind != "surd"):
            raise IllPosed("angle_and_answer_form_do_not_match")
        ans = _answer_for(ang, k, kind)
        thing, intro = HD_THINGS[ctx]
        given = _convert(ang, ans, "opposite", "adjacent")
        cands = [
            ("MC.TRIG.HD_TAN_INVERTED", given * _trig_of(ang, "cot")),
            ("MC.TRIG.HD_SIN_FOR_TAN", given * _trig_of(ang, "sin")),
            ("MC.TRIG.HD_COS_FOR_TAN", given * _trig_of(ang, "cos")),
            ("MC.TRIG.HD_SLANT_REPORTED", given * _trig_of(ang, "sec")),
        ]
        return self.finish(
            tpl,
            p,
            angle=ang,
            known="adjacent",
            unknown="opposite",
            answer=ans,
            stem=(
                f"{intro} From a point on the ground {{given}} m from the foot, the angle of "
                f"elevation of the top is {ang}{DEG}. Find the height of the {thing} in metres."
            ),
            steps=[
                f"Sketch a right triangle: the {thing} is the side opposite the {ang}{DEG} angle and the ground distance is the adjacent side.",
                f"Opposite and adjacent sides link through tan {ang}{DEG}: height = {{given}} x tan {ang}{DEG}.",
                f"With tan {ang}{DEG} taken from the table, the height is {{ans}} m.",
            ],
            hints=[
                pick(
                    [
                        "Draw the right triangle first and label what is known and what is wanted.",
                        "Decide which side is opposite the angle and which is next to it.",
                        "Choose the ratio that links the two sides you care about.",
                    ],
                    p,
                ),
                "The ratio that links the opposite side to the adjacent side is the tangent. Write "
                "it as one relation and undo the division by doing the same thing to each side.",
                "Full method: sketch and label the triangle, name the two sides involved, write "
                "the tangent ratio for the stated angle, replace the tangent by its exact value, "
                "and solve for the height.",
            ],
            wrong=cands,
            prediction="Is the height larger or smaller than the distance from the foot?",
            base=0.3,
            role="apply",
            slug=_slug(ang, k, kind, ctx),
        )


class HDDistance(_HDBase):
    id = "hd_distance"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        ang, k, kind, ctx = p["ang"], p["k"], p["kind"], p["ctx"]
        if (ang == 30 and kind != "surd") or (ang in (45, 60) and kind != "rational"):
            raise IllPosed("angle_and_answer_form_do_not_match")
        ans = _answer_for(ang, k, kind)
        height = _convert(ang, ans, "adjacent", "opposite")
        thing, _ = HD_THINGS[ctx]
        cands = [
            ("MC.TRIG.HD_MULTIPLIED_NOT_DIVIDED", height * _trig_of(ang, "tan")),
            ("MC.TRIG.HD_SIN_FOR_TAN", height * _trig_of(ang, "sin")),
            ("MC.TRIG.HD_SLANT_REPORTED", height * _trig_of(ang, "csc")),
            ("MC.TRIG.HD_COS_FOR_TAN", height * _trig_of(ang, "cos")),
        ]
        return self.finish(
            tpl,
            p,
            angle=ang,
            known="opposite",
            unknown="adjacent",
            answer=ans,
            stem=(
                f"The sun is {ang}{DEG} above the horizontal. A vertical {thing} {{given}} m high "
                f"casts a shadow on level ground. Find the length of the shadow in metres."
            ),
            steps=[
                f"The {thing} is the side opposite the {ang}{DEG} angle and the shadow is the adjacent side.",
                f"tan {ang}{DEG} = opposite / adjacent, so shadow = {{given}} / tan {ang}{DEG}.",
                "Replace the tangent by its exact value and simplify: the shadow is {ans} m.",
            ],
            hints=[
                pick(
                    [
                        "Sketch the vertical object, its shadow and the line of the sun's rays.",
                        "The sun's angle is measured from the ground, at the tip of the shadow.",
                        "Decide which side of the triangle is the shadow.",
                    ],
                    p,
                ),
                "The shadow is the unknown and it sits underneath in the tangent ratio. Undo the "
                "division by doing the same thing to each side before you substitute the value.",
                "Full method: sketch the triangle, write the tangent ratio with the shadow as the "
                "unknown, swap the unknown into the numerator by multiplying each side, replace "
                "the tangent by its exact value and simplify, rationalising if needed.",
            ],
            wrong=cands,
            prediction="Will the shadow be longer or shorter than the object is tall?",
            base=0.4,
            role="apply",
            slug=_slug(ang, k, kind, ctx),
        )


class HDLadder(_HDBase):
    id = "hd_ladder"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        ang, k, ask = p["ang"], p["k"], p["ask"]
        length = S(2 * k)
        if ask == "reach":
            ans, known, unknown = (
                _convert(ang, length, "hypotenuse", "opposite"),
                "hypotenuse",
                "opposite",
            )
        elif ask == "foot":
            ans, known, unknown = (
                _convert(ang, length, "hypotenuse", "adjacent"),
                "hypotenuse",
                "adjacent",
            )
        elif ask == "length_reach":
            ans, known, unknown = length, "opposite", "hypotenuse"
        else:
            ans, known, unknown = length, "adjacent", "hypotenuse"
        given = _convert(ang, ans, unknown, known)
        trig = lambda f: _trig_of(ang, f)  # noqa: E731
        if ask in ("reach", "foot"):
            this = "sin" if ask == "reach" else "cos"
            other = "cos" if ask == "reach" else "sin"
            cands = [
                ("MC.TRIG.HD_SIN_COS_SWAPPED", given * trig(other)),
                ("MC.TRIG.HD_TAN_FOR_SIN_COS", given * trig("tan")),
                ("MC.TRIG.HD_DIVIDED_NOT_MULTIPLIED", given / trig(this)),
                ("MC.TRIG.HD_HALF_LENGTH_ONLY", given / 2),
            ]
            tail = (
                "How high up the wall does the ladder reach, in metres?"
                if ask == "reach"
                else "How far is the foot of the ladder from the wall, in metres?"
            )
            stem = (
                f"A ladder {{given}} m long leans against a vertical wall and makes an angle of "
                f"{ang}{DEG} with the level ground. {tail}"
            )
            ratio_name = "sine" if ask == "reach" else "cosine"
            steps = [
                f"The ladder is the hypotenuse. The wall height is opposite the {ang}{DEG} angle and the foot distance is adjacent to it.",
                f"{'Height' if ask == 'reach' else 'Distance'} = ladder x {ratio_name} {ang}{DEG} = {{given}} x ({fmt(trig(this))}).",
                "Simplify: {ans} m.",
            ]
            hint2 = (
                "Choose between sine and cosine by asking which side the question wants: the "
                "side opposite the angle goes with sine, the side next to it with cosine."
            )
        else:
            this = "sin" if ask == "length_reach" else "cos"
            other = "cos" if ask == "length_reach" else "sin"
            cands = [
                ("MC.TRIG.HD_SIN_COS_SWAPPED", given / trig(other)),
                ("MC.TRIG.HD_MULTIPLIED_NOT_DIVIDED", given * trig(this)),
                ("MC.TRIG.HD_TAN_FOR_SIN_COS", given / trig("tan")),
                ("MC.TRIG.HD_SIDE_REPORTED", given),
            ]
            clause = (
                "It reaches a height of {given} m up the wall."
                if ask == "length_reach"
                else "Its foot is {given} m from the wall."
            )
            stem = (
                f"A ladder leans against a vertical wall and makes an angle of {ang}{DEG} with the "
                f"level ground. {clause} Find the length of the ladder in metres."
            )
            steps = [
                "The ladder is the hypotenuse of the right triangle.",
                f"Known side = ladder x {'sine' if this == 'sin' else 'cosine'} {ang}{DEG}, so ladder = {{given}} / ({fmt(trig(this))}).",
                "Simplify: {ans} m.",
            ]
            hint2 = (
                "The ladder is the unknown and it is the hypotenuse. Undo the multiplication by "
                "doing the same thing to each side, dividing by the ratio."
            )
        return self.finish(
            tpl,
            p,
            angle=ang,
            known=known,
            unknown=unknown,
            answer=ans,
            stem=stem,
            steps=steps,
            hints=[
                pick(
                    [
                        "Sketch the wall, the ground and the ladder as the right triangle.",
                        "Mark the angle with the ground and name the three sides.",
                        "The ladder is always the longest side of the triangle.",
                    ],
                    p,
                ),
                hint2,
                "Full method: sketch and label the triangle, identify which two sides are involved, "
                "pick sine or cosine for them, replace the ratio by its exact value, and solve.",
            ],
            wrong=cands,
            prediction="Is the answer more or less than the length of the ladder?"
            if ask in ("reach", "foot")
            else "Will the ladder be longer than the given side?",
            base=0.4,
            role="apply",
            slug=_slug(ang, k, ask),
        )


class HDDepression(_HDBase):
    id = "hd_depression"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        ang, k, ask, ctx = p["ang"], p["k"], p["ask"], p["ctx"]
        if ask == "distance":
            ans = _answer_for(ang, k, "surd" if ang == 30 else "rational")
            known, unknown = "opposite", "adjacent"
        else:
            ans = sqrt_of(3) * k if ang == 60 else S(k)
            known, unknown = "adjacent", "opposite"
        place = [
            ("lighthouse", "a boat", "the sea"), ("cliff", "a swimmer", "the water"),
            ("tower", "a car", "a straight road"), ("bridge", "a boat", "the river"),
        ][ctx % 4]  # fmt: skip
        given = _convert(ang, ans, unknown, known)
        if ask == "distance":
            cands = [
                ("MC.TRIG.HD_DEPRESSION_FROM_VERTICAL", given * _trig_of(ang, "tan")),
                ("MC.TRIG.HD_SIN_FOR_TAN", given * _trig_of(ang, "sin")),
                ("MC.TRIG.HD_SLANT_REPORTED", given * _trig_of(ang, "csc")),
                ("MC.TRIG.HD_COS_FOR_TAN", given * _trig_of(ang, "cos")),
            ]
            stem = (
                f"From the top of a {place[0]} {{given}} m high, the angle of depression of {place[1]} "
                f"on {place[2]} is {ang}{DEG}. Find the horizontal distance of {place[1]} from the "
                f"foot of the {place[0]} in metres."
            )
        else:
            cands = [
                ("MC.TRIG.HD_DEPRESSION_FROM_VERTICAL", given / _trig_of(ang, "tan")),
                ("MC.TRIG.HD_SIN_FOR_TAN", given * _trig_of(ang, "sin")),
                ("MC.TRIG.HD_SLANT_REPORTED", given * _trig_of(ang, "sec")),
                ("MC.TRIG.HD_COS_FOR_TAN", given * _trig_of(ang, "cos")),
            ]
            stem = (
                f"{place[1].capitalize()} on {place[2]} is {{given}} m from the foot of a {place[0]}. "
                f"From the top of the {place[0]} the angle of depression of {place[1]} is "
                f"{ang}{DEG}. Find the height of the {place[0]} in metres."
            )
        return self.finish(
            tpl,
            p,
            angle=ang,
            known=known,
            unknown=unknown,
            answer=ans,
            stem=stem,
            steps=[
                f"The angle of depression is measured downward from the horizontal at the top; by alternate angles it equals the angle of elevation of the top seen from {place[1]}.",
                f"So in the right triangle the {ang}{DEG} angle is at {place[1]}, and height and ground distance are opposite and adjacent to it.",
                f"Use tan {ang}{DEG} = height / distance and solve: the answer is {{ans}} m.",
            ],
            hints=[
                pick(
                    [
                        "Draw the horizontal line at the top and measure the angle downward from it.",
                        "The angle of depression is measured from the horizontal, not from the vertical.",
                        "Alternate angles let you move the angle to the bottom of the triangle.",
                    ],
                    p,
                ),
                "After placing the angle inside the right triangle, decide which side is opposite "
                "it and which is adjacent, then use the matching ratio and undo it by doing the "
                "same thing to each side.",
                "Full method: sketch the horizontal line from the top, mark the angle below it, "
                "copy that angle into the right triangle using alternate angles, pick the ratio "
                "for the two sides involved, and solve.",
            ],
            wrong=cands,
            prediction="Does the sight line make a steep or a shallow angle with the horizontal?",
            base=0.45,
            role="transfer",
            slug=_slug(ang, k, ask, ctx),
        )


class HDTwoPositions(_HDBase):
    id = "hd_two_positions"
    version = "2"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        pair, k, direction = p["pair"], p["k"], p["dir"]
        t1, t2 = {0: (30, 60), 1: (45, 60), 2: (30, 45)}[pair]
        sep = S(2 * k)
        cot = {a: ref.RATIOS[a][1] / ref.RATIOS[a][0] for a in (30, 45, 60)}
        ans = sep / (cot[t1] - cot[t2])
        if ans.c[1] or ans.c[3] or ans.c[0] < 0 or ans.c[2] < 0:
            raise IllPosed("answer_outside_q_sqrt3")
        part, witness, lhs = s_part(ans)
        far, near = (t1, t2)
        angles = [t1, t2]
        tan_ = {a: ref.RATIOS[a][0] / ref.RATIOS[a][1] for a in (30, 45, 60)}
        cands = [
            ("MC.TRIG.HD_SEPARATION_AS_HEIGHT", sep),
            ("MC.TRIG.HD_FIRST_ANGLE_ONLY", sep * tan_[far]),
            ("MC.TRIG.HD_SECOND_ANGLE_ONLY", sep * tan_[near]),
            ("MC.TRIG.HD_DISTANCES_ADDED", sep / (cot[t1] + cot[t2])),
        ]
        if direction == 0:
            move = (
                f"From a point on level ground the angle of elevation of the top of a tower is "
                f"{far}{DEG}. After walking {2 * k} m towards the foot of the tower along a straight "
                f"line, the angle of elevation becomes {near}{DEG}."
            )
        else:
            move = (
                f"From a point on level ground close to a tower the angle of elevation of its top "
                f"is {near}{DEG}. After walking {2 * k} m directly away from the tower, the angle of "
                f"elevation becomes {far}{DEG}."
            )
        stem = move + pick(
            [
                " Find the height of the tower in metres.",
                " How tall is the tower, in metres?",
                " What is the height of the tower in metres?",
            ],
            {"pair": pair, "k": k, "dir": direction},
        )

        model = {"family": self.id, "kind": "two_positions", "angles": angles,
                 "separation": ref.s_pair(sep)}  # fmt: skip
        return Built(
            spec=_spec(lhs, model),
            answer=part,
            witness=witness,
            stem=stem,
            steps=[
                f"Let the tower be h m high. Seen at {far}{DEG} the ground distance is h / tan {far}{DEG}; seen at {near}{DEG} it is h / tan {near}{DEG}.",
                f"The two distances differ by the {2 * k} m walked: h / tan {far}{DEG} - h / tan {near}{DEG} = {2 * k}.",
                f"Put in the exact values of the tangents and solve for h: h = {fmt(ans)} m.",
            ],
            hints=[
                pick(
                    [
                        "Draw both positions on one diagram with the tower standing on the same line.",
                        "You get two right triangles that share the tower as one side.",
                        "The distance walked is the difference between the two ground distances.",
                    ],
                    p,
                ),
                "Write the ground distance from each position in terms of the height. Their "
                "difference equals the distance walked. Then undo each operation by doing the "
                "same thing to each side to get the height.",
                "Full method: draw the figure, write each ground distance using the tangent of the "
                "angle, subtract to match the distance walked, replace tangents by exact values, "
                "collect the height terms, and divide each side to isolate the height.",
            ],
            wrong=_wrong_s(cands),
            key_text=fmt(ans),
            tokens=[fmt(ans)],
            difficulty=clamp_difficulty(0.65, k, steps=5),
            role="transfer",
            prediction="Is the tower taller or shorter than the distance walked?",
            methods=[
                FnMethod(
                    "maths.hd2.closed",
                    "closed_form",
                    "special_angle_ratios",
                    lambda sp: s_answer(ref.two_closed(sp["model"])),
                ),
                FnMethod(
                    "maths.hd2.sympy",
                    "sympy.trig",
                    "",
                    lambda sp: s_answer(ref.two_sympy(sp["model"])),
                ),
                FnMethod(
                    "maths.hd2.numeric",
                    "numeric.mpmath",
                    "special_angle_ratios",
                    lambda sp: s_answer(ref.two_numeric(sp["model"])),
                ),
            ],
            slug=_slug(pair, k, direction),
            tags=[f"marks:{tpl['form']['marks']}", "steps:5"],
        )


TRIG_FAMILIES: dict[str, Family] = {
    f.id: f
    for f in (
        RatiosFromTriangle(), TableValues(), Complementary(), RatioFromRatio(), HDHeight(),
        HDDistance(), HDLadder(), HDDepression(), HDTwoPositions(),
    )
}  # fmt: skip
