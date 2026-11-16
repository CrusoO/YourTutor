# ruff: noqa: E501
"""Quadratic Equations families (Class 10 algebra). Every family builds BACKWARD from the answer.

Each family: chooses the roots (or the asked value) first, expands to the stem, writes wrong
options from NAMED wrong procedures (each carries a misconception id), writes a numeral-free hint
ladder (strategy, next operation with a first-step lead-in, full method) and attaches three
independent engines (closed form, SymPy, interpolation/enumeration) as methods.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from fractions import Fraction
from typing import Any

import sympy

from app.factory.kernel.exact import rational_sqrt
from app.factory.lanes.maths.core import (
    SQ,
    Built,
    Family,
    FnMethod,
    IllPosed,
    clamp_difficulty,
    fstr,
    pick,
    poly_text,
    quad_kernel,
)
from app.factory.lanes.maths.reference.quad import (
    ENGINES,
    PM,
    SQRT,
    surd_pair_text,
)

F = Fraction


def roots_phrase(roots: list[Fraction]) -> str:
    if not roots:
        return "no real roots"
    return " or ".join(f"x = {fstr(r)}" for r in sorted(roots))


def _slug(*parts: Any) -> str:
    return "_".join(str(x).replace("-", "m").replace("/", "d") for x in parts)


def _base_spec(lhs: list[Any], rhs: list[Any] | None, model: dict[str, Any]) -> dict[str, Any]:
    spec: dict[str, Any] = {"domain": "algebra", "kind": "polynomial", "lhs": lhs, "model": model}
    if rhs is not None:
        spec["rhs"] = rhs
    return spec


def quad_methods(
    extract: Callable[[dict[str, Any], dict[str, Any]], str], closed_tech: str, interp_tech: str
) -> list[FnMethod]:
    """Three independent engines reading the equation from the spec; `extract` reads one field."""

    def make(engine: str) -> Callable[[Mapping[str, Any]], Any]:
        def run(spec: Mapping[str, Any]) -> Any:
            info = ENGINES[engine](spec)
            part, _ = quad_kernel(info["c"], info["b"], info["a"])
            return {**part, "value": extract(info, spec["model"])}

        return run

    return [
        FnMethod("maths.quad.closed", "closed_form", closed_tech, make("closed")),
        FnMethod("maths.quad.sympy", "sympy.poly", "", make("sympy")),
        FnMethod("maths.quad.interp", "interpolation", interp_tech, make("interp")),
    ]


def _roots_extract(info: dict[str, Any], model: dict[str, Any] | None = None) -> str:
    if info["roots"]:
        return roots_phrase(info["roots"])
    if info["D"] < 0:
        return "no real roots"
    raise ValueError("irrational roots: outside this extractor")


def _rec(part: dict[str, Any], value: str) -> dict[str, Any]:
    return {**part, "value": value}


def _lin(q: int, p: int) -> str:
    """The bracket (q x - p)."""
    return "(" + poly_text([-p, q]) + ")"


# ---------------------------------------------------------------- 1. standard form


class StdForm(Family):
    id = "std_form"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        a, r1, r2, e, f, ask = (p[k] for k in ("a", "r1", "r2", "e", "f", "ask"))
        if r1 >= r2:
            raise IllPosed("needs_two_distinct_roots_in_order")
        if (ask == "b" and e == 0) or (ask == "c" and f == 0):
            raise IllPosed("moved_term_must_matter_for_the_asked_coefficient")
        c0, b0 = a * r1 * r2, -a * (r1 + r2)
        lhs, rhs = [c0 + f, b0 + e, a], [f, e]
        part, witness = quad_kernel(F(c0), F(b0), F(a))
        val, left, other = (b0, b0 + e, e) if ask == "b" else (c0, c0 + f, f)
        wrong_vals = [
            ("MC.QUAD.STD_RHS_IGNORED", left),
            ("MC.QUAD.STD_TERM_ADDED", val + 2 * other),
            ("MC.QUAD.STD_SIGN_NEGATED", -val),
            ("MC.QUAD.STD_COEFF_POSITION_MIXED", a if ask == "b" else b0),
        ]
        std = poly_text([c0, b0, a])
        eq = f"{poly_text(lhs)} = {poly_text(rhs)}"
        stem = f"Rearrange {eq} into the form ax{SQ} + bx + c = 0. What is the value of {ask}?"
        strat = pick(
            [
                "Get everything onto one side so that the other side is exactly zero.",
                "The standard form has zero on the right, so deal with the terms on the right first.",
                "Collect all the terms on the left side and leave zero on the right.",
            ],
            p,
        )
        lead = (
            "Start with the term in x on the right: take it away from both sides first."
            if ask == "b"
            else "Start with the plain number on the right: take it away from both sides first."
        )
        return Built(
            spec=_base_spec(lhs, rhs, {"family": self.id, "ask": ask}),
            answer=_rec(part, str(val)),
            witness=witness,
            stem=stem,
            steps=[
                "Take the whole right-hand side away from both sides, so the right-hand side is 0.",
                f"The left-hand side becomes {std}, so the equation is {std} = 0.",
                f"Comparing with ax{SQ} + bx + c = 0 gives {ask} = {val}.",
            ],
            hints=[
                strat,
                "Undo each term on the right by doing the same operation to both sides: take the "
                "term away from both sides, then combine like terms. " + lead,
                "Full method: take the x term on the right from both sides, take the plain number "
                "on the right from both sides, combine the x terms, combine the plain numbers, "
                "then read the coefficient you need, keeping its sign.",
            ],
            wrong=[(mc, _rec(part, str(v)), str(v)) for mc, v in wrong_vals],
            key_text=str(val),
            tokens=[str(val)],
            difficulty=clamp_difficulty(0.15, a, e, f, steps=3),
            role="procedure",
            prediction="Before you work it out, will the coefficient be positive or negative?",
            methods=quad_methods(
                lambda i, md: fstr(i[md["ask"]]), "standard_form", "standard_form"
            ),
            slug=_slug(a, r1, r2, e, f, ask),
            tags=["marks:1", "steps:3"],
        )


# ---------------------------------------------------------------- 2/3. solve by factorising


class SolveFactor(Family):
    id = "solve_factor"

    def _roots(self, p: Mapping[str, Any]) -> tuple[Fraction, Fraction]:
        p1, q1, p2, q2 = p["p1"], p["q1"], p["p2"], p["q2"]
        if 0 in (p1, p2):
            raise IllPosed("zero_root_is_a_different_skill")
        if math.gcd(p1, q1) != 1 or math.gcd(p2, q2) != 1:
            raise IllPosed("root_not_in_lowest_terms")
        r1, r2 = F(p1, q1), F(p2, q2)
        if r1 >= r2:
            raise IllPosed("needs_two_distinct_roots_in_order")
        return r1, r2

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        a, p1, q1, p2, q2 = (p[k] for k in ("a", "p1", "q1", "p2", "q2"))
        r1, r2 = self._roots(p)
        lead = q1 * q2
        mid = -(q1 * p2 + q2 * p1)
        low = p1 * p2
        coeffs = [a * low, a * mid, a * lead]
        part, witness = quad_kernel(F(coeffs[0]), F(coeffs[1]), F(coeffs[2]))
        key = [r1, r2]
        wrong_roots: list[tuple[str, list[Fraction]]] = [
            ("MC.QUAD.FACTOR_SIGN_READ", [-r1, -r2]),
            ("MC.QUAD.FACTOR_ONE_SIGN", [r1, -r2]),
            ("MC.QUAD.FACTOR_ONE_ROOT_ONLY", [r1]),
            ("MC.QUAD.FACTOR_ONE_SIGN", [-r1, r2]),
            ("MC.QUAD.FACTOR_SUM_PRODUCT_CONFUSED", [r1 + r2, r1 * r2]),
        ]
        if q1 > 1 or q2 > 1:
            wrong_roots[2:2] = [
                ("MC.QUAD.BRACKET_COEFF_IGNORED", [F(p1), F(p2)]),
                ("MC.QUAD.BRACKET_COEFF_INVERTED", [F(q1, p1), F(q2, p2)]),
            ]
        stem = pick(
            [
                f"Solve {poly_text(coeffs)} = 0.",
                f"Find the roots of the equation {poly_text(coeffs)} = 0.",
                f"Find all values of x that satisfy {poly_text(coeffs)} = 0.",
            ],
            {"p1": p1, "p2": p2, "q": q1 + q2},
        )
        steps: list[str] = []
        if a > 1:
            steps.append(
                f"Divide both sides by {a}, the common factor, to get {poly_text([low, mid, lead])} = 0."
            )
        if q1 == 1 and q2 == 1:
            steps.append(
                f"Look for two numbers with product {low} and sum {mid}: they are {-p1} and {-p2}."
            )
        else:
            u, v = -q1 * p2, -q2 * p1
            steps.append(
                f"Split the middle term {mid}x into {u}x and {v}x, because {u} and {v} multiply to "
                f"{lead * low} (the product of {lead} and {low}) and add to {mid}."
            )
        steps += [
            f"Factorise: {_lin(q1, p1)}{_lin(q2, p2)} = 0.",
            "A product is zero only when one factor is zero, so set each bracket equal to zero.",
            f"Undo each bracket by doing the same thing to both sides: {poly_text([-p1, q1])} = 0 "
            f"gives x = {fstr(r1)} and {poly_text([-p2, q2])} = 0 gives x = {fstr(r2)}.",
        ]
        general = q1 > 1 or q2 > 1 or a > 1
        strat = pick(
            [
                "Try writing the left side as two brackets multiplied together.",
                "Factorise the left side first; any product that equals zero tells you something "
                "about each bracket.",
                "Aim to turn the left side into two simpler expressions multiplied together.",
            ],
            p,
        )
        op = (
            "Divide out any common factor, split the middle term into two parts, and group in "
            "pairs to find the brackets."
            if general
            else "Find two numbers that multiply to the plain number and add to the x coefficient."
        )
        return Built(
            spec=_base_spec(coeffs, None, {"family": self.id}),
            answer=_rec(part, roots_phrase(key)),
            witness=witness,
            stem=stem,
            steps=steps,
            hints=[
                strat,
                op + " Then set each bracket to zero and undo it by doing the same thing to both "
                "sides.",
                "Full method: factorise the left side, set each bracket to zero, add or subtract "
                "the same number on both sides, divide both sides by the coefficient of x, then "
                "check each solution by substituting it back.",
            ],
            wrong=[(mc, _rec(part, roots_phrase(r)), roots_phrase(r)) for mc, r in wrong_roots],
            key_text=roots_phrase(key),
            tokens=[fstr(r) for r in key],
            difficulty=clamp_difficulty(
                0.3 if not general else 0.5, p1, p2, q1 * q2, steps=len(steps)
            ),
            role="procedure",
            prediction="How many different values of x do you expect?",
            methods=quad_methods(_roots_extract, "factorise_quadratic", "factorise_quadratic"),
            slug=_slug(a, p1, q1, p2, q2),
            tags=[f"marks:{tpl['form']['marks']}", f"steps:{len(steps)}"],
        )


class FormulaRational(SolveFactor):
    """Same backward construction, but the stem and solution use the quadratic formula."""

    id = "formula_rational"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        built = super().build(tpl, p)
        a, p1, q1, p2, q2 = (p[k] for k in ("a", "p1", "q1", "p2", "q2"))
        r1, r2 = self._roots(p)
        c, b, aa = built.spec["lhs"]
        disc = b * b - 4 * aa * c
        s = rational_sqrt(F(disc))
        if s is None or s == 0:
            raise IllPosed("discriminant_not_a_positive_perfect_square")
        key = [r1, r2]
        cand: list[tuple[str, list[Fraction]]] = [
            ("MC.QUAD.FORMULA_B_SIGN", [(b + s) / (2 * aa), (b - s) / (2 * aa)]),
            ("MC.QUAD.FORMULA_FORGOT_2A", [(-b + s) / aa, (-b - s) / aa]),
            ("MC.QUAD.FORMULA_DIVIDE_ONE_TERM", [-b + s / (2 * aa), -b - s / (2 * aa)]),
            ("MC.QUAD.FORMULA_FORGOT_A", [(-b + s) / 2, (-b - s) / 2]),
        ]
        built.wrong = [(mc, _rec({"count": 2}, roots_phrase(r)), roots_phrase(r)) for mc, r in cand]
        built.stem = f"Use the quadratic formula to solve {poly_text(built.spec['lhs'])} = 0."
        built.steps = [
            f"Read off the coefficients: coefficient of x{SQ} is {aa}, of x is {b}, plain number is {c}.",
            f"The discriminant is {b}{SQ} - 4 x {aa} x {c} = {disc}, and its square root is {fstr(s)}.",
            f"Substitute into x = (-b {PM} square root of the discriminant) / (2 x {aa}).",
            f"Work out both signs: x = {fstr(r1)} or x = {fstr(r2)}.",
        ]
        built.hints = [
            pick(
                [
                    "Identify the three coefficients carefully before you substitute anything.",
                    "Every quadratic can be solved with the formula; the work is in the "
                    "discriminant.",
                    "Write down the three coefficients with their signs, then work out the "
                    "discriminant on its own.",
                ],
                p,
            ),
            "Work out the discriminant first, then its square root. Keep the minus sign of the "
            "x coefficient when you write the opposite of it.",
            "Full method: list the coefficients, compute the discriminant, take its square root, "
            "put the numbers into the formula once with the plus sign and once with the minus "
            "sign, divide each by twice the leading coefficient, and check by substitution.",
        ]
        built.role = "procedure"
        built.methods = quad_methods(_roots_extract, "quadratic_formula", "quadratic_formula")
        built.difficulty = clamp_difficulty(0.45, p1, p2, aa, steps=4)
        built.tags = [f"marks:{tpl['form']['marks']}", "steps:4"]
        built.key_text = roots_phrase(key)
        return built


# ---------------------------------------------------------------- 4. incomplete quadratics


class IncompletePure(Family):
    id = "incomplete_pure"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        a, r, form, neg = p["a"], p["r"], p["form"], p["neg"]
        k = a * r * r
        sign = 1 if neg else -1  # a x^2 + k = 0 has no real roots
        if form == 0:
            lhs, rhs = [sign * k, 0, a], None
            stem = pick(
                [
                    f"Solve {poly_text(lhs)} = 0.",
                    f"Find every real solution of {poly_text(lhs)} = 0.",
                    f"Which real values of x satisfy {poly_text(lhs)} = 0?",
                ],
                p,
            )
        else:
            lhs, rhs = [0, 0, a], [-sign * k]
            stem = pick(
                [
                    f"Solve {poly_text(lhs)} = {-sign * k}.",
                    f"Find every real solution of {poly_text(lhs)} = {-sign * k}.",
                    f"Which real values of x satisfy {poly_text(lhs)} = {-sign * k}?",
                ],
                p,
            )
        coeffs = [sign * k, 0, a]
        part, witness = quad_kernel(F(coeffs[0]), F(0), F(a))
        if neg:
            key_vals = []
            key_text = "no real roots"
            wrong = [
                ("MC.QUAD.PURE_SIGN_IGNORED", [F(-r), F(r)]),
                ("MC.QUAD.PURE_ONE_NEGATIVE_ROOT", [F(-r)]),
                ("MC.QUAD.PURE_ONE_POSITIVE_ROOT", [F(r)]),
                ("MC.QUAD.PURE_ZERO_ROOT", [F(0)]),
            ]
            steps = [
                f"Take {k} away from both sides and then divide both sides by {a}: x{SQ} = {-r * r}.",
                "A square is never negative, so no real number satisfies this.",
                "The equation has no real roots.",
            ]
        else:
            key_vals = [F(-r), F(r)]
            key_text = roots_phrase(key_vals)
            wrong = [
                ("MC.QUAD.PURE_PLUS_ONLY", [F(r)]),
                ("MC.QUAD.PURE_FORGOT_SQRT", [F(-r * r), F(r * r)]),
                ("MC.QUAD.PURE_MULTIPLIED_NOT_DIVIDED", [F(-a * r), F(a * r)]),
                ("MC.QUAD.PURE_NO_REAL_ROOTS", []),
            ]
            steps = [
                f"Add {k} to both sides and divide both sides by {a}: x{SQ} = {r * r}.",
                f"Take the square root of both sides, remembering both signs: x = {-r} or x = {r}.",
            ]
        wrong_c = [
            (mc, _rec({"count": len(v)}, roots_phrase(v)), roots_phrase(v)) for mc, v in wrong
        ]
        return Built(
            spec=_base_spec(lhs, rhs, {"family": self.id}),
            answer=_rec(part, key_text),
            witness=witness,
            stem=stem,
            steps=steps,
            hints=[
                pick(
                    [
                        "There is no x term, so isolate the squared term instead of factorising.",
                        "Get the squared term on its own by undoing the other operations.",
                        "Undo the operations around the squared term one after another.",
                    ],
                    p,
                ),
                "Undo the addition or subtraction by doing the same thing to both sides, then undo "
                "the multiplication by dividing both sides by the same number.",
                "Full method: take the plain number off one side by adding or subtracting it on both "
                "sides, divide both sides by the coefficient of the squared term, then take the "
                "square root of both sides if the result is positive, keeping both signs.",
            ],
            wrong=wrong_c,
            key_text=key_text,
            tokens=[fstr(v) for v in key_vals],
            difficulty=clamp_difficulty(0.2 if not neg else 0.35, a, r, steps=len(steps)),
            role="procedure",
            prediction="Will this equation have two answers, one answer or none?",
            methods=quad_methods(_roots_extract, "square_root_method", "square_root_method"),
            slug=_slug(a, r, form, neg),
            tags=[f"marks:{tpl['form']['marks']}", f"steps:{len(steps)}"],
        )


class IncompleteX(Family):
    id = "incomplete_x"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        a, r, form = p["a"], p["r"], p["form"]
        if r == 0:
            raise IllPosed("nonzero_second_root_needed")
        k = a * r  # a x^2 - k x = 0
        if form == 0:
            lhs, rhs = [0, -k, a], None
            stem = pick(
                [
                    f"Solve {poly_text(lhs)} = 0.",
                    f"Find both roots of {poly_text(lhs)} = 0.",
                    f"Which values of x satisfy {poly_text(lhs)} = 0?",
                ],
                p,
            )
        else:
            lhs, rhs = [0, 0, a], [0, k]
            stem = pick(
                [
                    f"Solve {poly_text(lhs)} = {poly_text(rhs)}.",
                    f"Find both roots of {poly_text(lhs)} = {poly_text(rhs)}.",
                    f"Which values of x satisfy {poly_text(lhs)} = {poly_text(rhs)}?",
                ],
                p,
            )
        part, witness = quad_kernel(F(0), F(-k), F(a))
        key = sorted([F(0), F(r)])
        wrong = [
            ("MC.QUAD.DIVIDED_BY_X_LOST_ROOT", [F(r)]),
            ("MC.QUAD.ONE_FACTOR_ONLY", [F(0)]),
            ("MC.QUAD.FACTOR_SIGN_SLIP", sorted([F(0), F(-r)])),
            ("MC.QUAD.SECOND_ROOT_SIGN_ONLY", [F(-r)]),
        ]
        steps = [
            "Bring every term to the left so the right side is 0, then take out x as a common factor.",
            f"This gives x({poly_text([-k, a])}) = 0.",
            "A product is zero only when one factor is zero, so x = 0 or the bracket is 0.",
            f"Undo the bracket: add {k} to both sides, then divide both sides by {a}: x = {r}.",
            f"The solutions are {roots_phrase(key)}.",
        ]
        return Built(
            spec=_base_spec(lhs, rhs, {"family": self.id}),
            answer=_rec(part, roots_phrase(key)),
            witness=witness,
            stem=stem,
            steps=steps,
            hints=[
                pick(
                    [
                        "Both terms share an x, so take it out as the common factor instead of dividing.",
                        "Do not divide by x: that would lose an answer. Factorise instead.",
                        "Look for the factor that both terms contain.",
                    ],
                    p,
                ),
                "Set each factor to zero. For the bracket, undo each operation by doing the same "
                "thing to both sides.",
                "Full method: bring all terms to one side, take out the common factor x, set each "
                "factor to zero, add the same number to both sides, divide both sides by the "
                "coefficient, and write both solutions.",
            ],
            wrong=[(mc, _rec(part, roots_phrase(v)), roots_phrase(v)) for mc, v in wrong],
            key_text=roots_phrase(key),
            tokens=[fstr(v) for v in key if v != 0],
            difficulty=clamp_difficulty(0.3, a, r, steps=4),
            role="procedure",
            prediction="Will x = 0 be one of the answers?",
            methods=quad_methods(_roots_extract, "common_factor", "common_factor"),
            slug=_slug(a, r, form),
            tags=[f"marks:{tpl['form']['marks']}", "steps:5"],
        )


# ---------------------------------------------------------------- 5. formula with surd roots


class FormulaSurd(Family):
    id = "formula_surd"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        a, b, c = p["a"], p["b"], p["c"]
        disc = b * b - 4 * a * c
        if disc <= 0 or rational_sqrt(F(disc)) is not None:
            raise IllPosed("needs_positive_non_square_discriminant")
        coeffs = [c, b, a]
        part, witness = quad_kernel(F(c), F(b), F(a))
        pa, t2 = F(-b, 2 * a), F(disc, 4 * a * a)
        key = "x = " + surd_pair_text(pa, t2)

        def text_for(disc2: int, num: F, den: F) -> str:
            if disc2 < 0:
                return "no real roots"
            s2 = rational_sqrt(F(disc2))
            if s2 is not None:
                return roots_phrase(sorted({(num + s2) / den, (num - s2) / den}))
            return "x = " + surd_pair_text(num / den, F(disc2) / (den * den))

        cands = [
            ("MC.QUAD.FORMULA_B_SIGN", text_for(disc, F(b), F(2 * a))),
            ("MC.QUAD.FORMULA_DIVIDE_ONE_TERM", "x = " + surd_pair_text(F(-b), F(disc, 4 * a * a))),
            ("MC.QUAD.FORMULA_FORGOT_2A", text_for(disc, F(-b), F(a))),
            ("MC.QUAD.FORMULA_DISC_SIGN", text_for(b * b + 4 * a * c, F(-b), F(2 * a))),
            ("MC.QUAD.FORMULA_FORGOT_A", text_for(disc, F(-b), F(2))),
        ]
        steps = [
            f"The coefficients are {a}, {b} and {c}.",
            f"The discriminant is {b}{SQ} - 4 x {a} x {c} = {disc}, which is positive but not a perfect square.",
            f"So x = (-({b}) {PM} {SQRT}{disc}) / {2 * a}, and the square root is simplified as far as it will go.",
            f"{key}.",
        ]

        def surd_extract(info: dict[str, Any], model: dict[str, Any] | None = None) -> str:
            if "sympy_solutions" in info:
                s1, s2 = info["sympy_solutions"]
                mid = sympy.simplify((s1 + s2) / 2)
                half = sympy.simplify(((s1 - s2) / 2) ** 2)
                x = sympy.Symbol("x")
                poly = sum(
                    (
                        sympy.Rational(co.numerator, co.denominator) * x**i
                        for i, co in enumerate((info["c"], info["b"], info["a"]))
                    ),
                    sympy.Integer(0),
                )
                if sympy.simplify(poly.subs(x, s1)) != 0 or sympy.simplify(poly.subs(x, s2)) != 0:
                    raise ValueError("a SymPy root does not satisfy the equation")
                return "x = " + surd_pair_text(
                    F(int(mid.p), int(mid.q)), F(int(half.p), int(half.q))
                )
            bb, aa, dd = info["b"], info["a"], info["D"]
            return "x = " + surd_pair_text(-bb / (2 * aa), dd / (4 * aa * aa))

        return Built(
            spec=_base_spec(coeffs, None, {"family": self.id}),
            answer=_rec(part, key),
            witness=witness,
            stem=f"Use the quadratic formula to solve {poly_text(coeffs)} = 0. Leave surds in simplest form.",
            steps=steps,
            hints=[
                pick(
                    [
                        "Work out the discriminant first; it tells you what kind of roots to expect.",
                        "This one will not factorise nicely, so the formula is the right tool.",
                        "Write down the three coefficients with their signs, then compute the "
                        "discriminant.",
                    ],
                    p,
                ),
                "Put the numbers into the formula once with the plus sign and once with the minus "
                "sign. Simplify the square root by pulling out any square factor.",
                "Full method: list the coefficients, compute the discriminant, simplify its square "
                "root, write both roots over twice the leading coefficient, and cancel any common "
                "factor from every term of the top and the bottom.",
            ],
            wrong=[(mc, {"value": t, "count": 2}, t) for mc, t in cands],
            key_text=key,
            tokens=[key],
            difficulty=clamp_difficulty(0.6, a, b, c, steps=4),
            role="apply",
            prediction="Is the discriminant a perfect square? What does that say about the roots?",
            methods=quad_methods(surd_extract, "quadratic_formula", "quadratic_formula"),
            slug=_slug(a, b, c),
            tags=[f"marks:{tpl['form']['marks']}", "steps:4"],
        )


# ---------------------------------------------------------------- 6/7. discriminant, nature


def _disc_info(c: int, b: int, a: int) -> tuple[int, dict[str, Any], dict[str, Any]]:
    part, witness = quad_kernel(F(c), F(b), F(a))
    return b * b - 4 * a * c, part, witness


class Discriminant(Family):
    id = "discriminant"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        a, b, c = p["a"], p["b"], p["c"]
        if a == 0:
            raise IllPosed("leading_coefficient_must_be_nonzero")
        disc, part, witness = _disc_info(c, b, a)
        coeffs = [c, b, a]
        cands = [
            ("MC.QUAD.DISC_SIGN_OF_4AC", b * b + 4 * a * c),
            ("MC.QUAD.DISC_FORGOT_FOUR", b * b - a * c),
            ("MC.QUAD.DISC_DOUBLED_B", 2 * b - 4 * a * c),
            ("MC.QUAD.DISC_NEGATIVE_B_SQUARED", -(b * b) - 4 * a * c),
        ]
        return Built(
            spec=_base_spec(coeffs, None, {"family": self.id}),
            answer=_rec(part, str(disc)),
            witness=witness,
            stem=pick(
                [
                    f"Find the discriminant of the equation {poly_text(coeffs)} = 0.",
                    f"Calculate the discriminant for {poly_text(coeffs)} = 0.",
                    f"What is the value of the discriminant of {poly_text(coeffs)} = 0?",
                ],
                p,
            ),
            steps=[
                f"Here the coefficients are {a}, {b} and {c}.",
                f"The discriminant is b{SQ} - 4ac = ({b}){SQ} - 4({a})({c}).",
                f"This equals {b * b} - ({4 * a * c}) = {disc}.",
            ],
            hints=[
                pick(
                    [
                        "Name the three coefficients first, keeping each sign.",
                        "The discriminant uses only the three coefficients, not x itself.",
                        "Be careful with brackets around negative numbers when you square.",
                    ],
                    p,
                ),
                "Square the x coefficient first, then work out four times the product of the other "
                "two coefficients, and subtract.",
                "Full method: write the three coefficients with signs, square the middle one, "
                "multiply the outer two together and then by four, and subtract the second result "
                "from the first.",
            ],
            wrong=[(mc, _rec(part, str(v)), str(v)) for mc, v in cands],
            key_text=str(disc),
            tokens=[str(disc)],
            difficulty=clamp_difficulty(0.2, a, b, c, steps=3),
            role="procedure",
            prediction="Will the discriminant be positive, zero or negative?",
            methods=quad_methods(lambda i, md: fstr(i["D"]), "discriminant", "discriminant"),
            slug=_slug(a, b, c),
            tags=[f"marks:{tpl['form']['marks']}", "steps:3"],
        )


NATURES = {
    "pos": "Two distinct real roots",
    "zero": "Two equal real roots",
    "neg": "No real roots",
}


def _sign_name(x: Fraction) -> str:
    return "pos" if x > 0 else ("zero" if x == 0 else "neg")


class Nature(Family):
    id = "nature"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        a, b, c = p["a"], p["b"], p["c"]
        if a == 0:
            raise IllPosed("leading_coefficient_must_be_nonzero")
        disc, part, witness = _disc_info(c, b, a)
        key = _sign_name(F(disc))
        coeffs = [c, b, a]
        tag_for = {
            ("pos", "neg"): "MC.QUAD.NATURE_DISC_SIGN_REVERSED",
            ("neg", "pos"): "MC.QUAD.NATURE_DISC_SIGN_REVERSED",
            ("pos", "zero"): "MC.QUAD.NATURE_ZERO_ONLY_TESTED",
            ("neg", "zero"): "MC.QUAD.NATURE_ZERO_ONLY_TESTED",
            ("zero", "pos"): "MC.QUAD.NATURE_EQUAL_ROOTS_MISSED",
            ("zero", "neg"): "MC.QUAD.NATURE_ZERO_DISC_NO_ROOTS",
        }
        wrong: list[tuple[str, dict[str, Any], str]] = []
        for other in ("pos", "neg", "zero"):
            if other != key:
                wrong.append((tag_for[(key, other)], _rec(part, NATURES[other]), NATURES[other]))
        impossible = "One real root and one non-real root"
        wrong.append(("MC.QUAD.NATURE_ONE_REAL_ONE_NOT", _rec(part, impossible), impossible))
        return Built(
            spec=_base_spec(coeffs, None, {"family": self.id}),
            answer=_rec(part, NATURES[key]),
            witness=witness,
            stem=pick(
                [
                    f"Without solving it, decide the nature of the roots of {poly_text(coeffs)} = 0.",
                    f"What can you say about the roots of {poly_text(coeffs)} = 0 without solving it?",
                    f"Describe the roots of the equation {poly_text(coeffs)} = 0 using the discriminant.",
                ],
                p,
            ),
            steps=[
                f"The coefficients are {a}, {b} and {c}.",
                f"The discriminant is b{SQ} - 4ac = {disc}.",
                f"The discriminant is {'positive' if disc > 0 else 'zero' if disc == 0 else 'negative'}, "
                f"so the equation has: {NATURES[key].lower()}.",
            ],
            hints=[
                pick(
                    [
                        "Look for one number that decides the nature of the roots.",
                        "You do not need to solve the equation; one quantity from the coefficients "
                        "tells you.",
                        "Compare that quantity with zero to decide.",
                    ],
                    p,
                ),
                "Work out the discriminant from the three coefficients, then see whether it is "
                "positive, zero or negative.",
                "Full method: write the coefficients with signs, compute the discriminant, and "
                "match its sign to the three possible cases for the roots.",
            ],
            wrong=wrong,
            key_text=NATURES[key],
            tokens=[],
            difficulty=clamp_difficulty(0.35, a, b, c, steps=3),
            role="apply",
            prediction="Which sign do you expect the discriminant to have?",
            methods=quad_methods(
                lambda i, md: NATURES[_sign_name(i["D"])], "discriminant", "completing_square"
            ),
            slug=_slug(a, b, c),
            tags=[f"marks:{tpl['form']['marks']}", "steps:3"],
        )


# ---------------------------------------------------------------- 8. find k for equal roots


def _k_methods(extract_name: str) -> list[FnMethod]:
    """Methods for 'find k': closed form, SymPy, and an integer scan, all from spec['model']."""

    def closed(spec: Mapping[str, Any]) -> Any:
        m = spec["model"]
        if extract_name == "middle":
            a, c = F(m["a"]), F(m["c"])
            s = rational_sqrt(4 * a * c)
            if s is None:
                raise ValueError("no rational k")
            ks = sorted({s, -s})
        else:
            b, c = F(m["b"]), F(m["c"])
            ks = [b * b / (4 * c)]
        return {"roots": [fstr(k) for k in ks], "count": len(ks), "value": _k_phrase(ks)}

    def sym(spec: Mapping[str, Any]) -> Any:
        m = spec["model"]
        x, k = sympy.symbols("x k")
        if extract_name == "middle":
            expr = m["a"] * x**2 + k * x + m["c"]
        else:
            expr = k * x**2 + m["b"] * x + m["c"]
        sols = sympy.solve(sympy.discriminant(expr, x), k)
        ks = sorted({F(int(s.p), int(s.q)) for s in sols})
        return {"roots": [fstr(v) for v in ks], "count": len(ks), "value": _k_phrase(ks)}

    def scan(spec: Mapping[str, Any]) -> Any:
        m = spec["model"]
        bound = 4 * abs(m["c"]) * max(1, abs(m.get("a", 1))) + abs(m.get("b", 0)) ** 2 + 4
        found = []
        for k in range(-bound, bound + 1):
            if extract_name == "middle":
                disc = k * k - 4 * m["a"] * m["c"]
            else:
                disc = m["b"] ** 2 - 4 * k * m["c"]
            if disc == 0:
                found.append(F(k))
        return {"roots": [fstr(v) for v in found], "count": len(found), "value": _k_phrase(found)}

    return [
        FnMethod("maths.quad.k_closed", "closed_form", "discriminant", closed),
        FnMethod("maths.quad.k_sympy", "sympy.solve", "", sym),
        FnMethod("maths.quad.k_scan", "enumeration", "discriminant", scan),
    ]


def _k_phrase(ks: list[Fraction]) -> str:
    return " or ".join(f"k = {fstr(k)}" for k in sorted(ks))


class FindKMiddle(Family):
    id = "find_k_middle"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        a, g = p["a"], p["g"]
        c = a * g * g
        r = 2 * a * g
        keys = [F(-r), F(r)]
        # k^2 - 4ac = 0 as a polynomial in k
        lhs = [-4 * a * c, 0, 1]
        part, witness = quad_kernel(F(lhs[0]), F(0), F(1))
        wrong = [
            ("MC.QUAD.K_POSITIVE_ONLY", [F(r)]),
            ("MC.QUAD.K_FORGOT_SQRT", [F(-4 * a * c), F(4 * a * c)]),
            ("MC.QUAD.K_FORGOT_FACTOR_FOUR", [F(-a * g), F(a * g)]),
            ("MC.QUAD.K_ONE_SIGN_PAIR", [F(-r), F(2 * c)]),
        ]
        eq = f"{a if a != 1 else ''}x{SQ} + kx + {c} = 0"
        stem = pick(
            [
                f"Find the values of k for which the equation {eq} has two equal real roots.",
                f"For which values of k does {eq} have equal roots?",
                f"The equation {eq} has repeated roots. Find k.",
            ],
            p,
        )
        phrase = _k_phrase(keys)
        return Built(
            spec=_base_spec(lhs, None, {"family": self.id, "a": a, "c": c}),
            answer=_rec(part, phrase),
            witness=witness,
            stem=stem,
            steps=[
                f"Equal roots need the discriminant to be zero: k{SQ} - 4({a})({c}) = 0.",
                f"So k{SQ} = {4 * a * c}.",
                f"Take the square root of both sides, keeping both signs: {phrase}.",
            ],
            hints=[
                pick(
                    [
                        "Equal roots happen when the discriminant is exactly zero.",
                        "Set the discriminant equal to zero and treat k as the unknown.",
                        "The discriminant will contain k; make it zero.",
                    ],
                    p,
                ),
                "After writing the discriminant, undo the subtraction by adding the same number to "
                "both sides, then undo the square by taking the square root of both sides.",
                "Full method: write the discriminant with k in it, set it to zero, add the same "
                "number to both sides, take the square root of both sides, and remember both signs.",
            ],
            wrong=[(mc, _rec(part, _k_phrase(v)), _k_phrase(v)) for mc, v in wrong],
            key_text=phrase,
            tokens=[fstr(k) for k in keys],
            difficulty=clamp_difficulty(0.5, a, g, steps=3),
            role="apply",
            prediction="Should k be allowed to be negative as well as positive?",
            methods=_k_methods("middle"),
            slug=_slug(a, g),
            tags=[f"marks:{tpl['form']['marks']}", "steps:3"],
        )


class FindKLead(Family):
    id = "find_k_lead"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        c, g = p["c"], p["g"]
        if c == 0:
            raise IllPosed("constant_term_must_be_nonzero")
        b = 2 * c * g
        kval = F(c * g * g)
        lhs = [-(b * b), 4 * c]  # 4 c k - b^2 = 0
        part = {"roots": [fstr(kval)], "count": 1}
        witness = {"split": {"lead": 4 * c, "roots": [[fstr(kval), 1]]}}
        wrong = [
            ("MC.QUAD.K_SIGN", -kval),
            ("MC.QUAD.K_FORGOT_FACTOR_FOUR", F(b * b, c)),
            ("MC.QUAD.K_HALF_FACTOR", F(b * b, 2 * c)),
            ("MC.QUAD.K_INVERTED", F(4 * c, b * b)),
        ]
        mid = f"{'+' if b > 0 else '-'} {abs(b)}x"
        const = f"{'+' if c > 0 else '-'} {abs(c)}"
        stem = pick(
            [
                f"Find the value of k for which kx{SQ} {mid} {const} = 0 has two equal real roots.",
                f"For what value of k does kx{SQ} {mid} {const} = 0 have equal roots?",
                f"The equation kx{SQ} {mid} {const} = 0 has repeated roots. What is k?",
            ],
            p,
        )
        return Built(
            spec=_base_spec(lhs, None, {"family": self.id, "b": b, "c": c}),
            answer=_rec(part, f"k = {fstr(kval)}"),
            witness=witness,
            stem=stem,
            steps=[
                f"Equal roots need b{SQ} - 4ac = 0, so ({b}){SQ} - 4(k)({c}) = 0.",
                f"This gives {b * b} - {4 * c}k = 0. Add {4 * c}k to both sides: {4 * c}k = {b * b}.",
                f"Divide both sides by {4 * c}: k = {fstr(kval)}.",
            ],
            hints=[
                pick(
                    [
                        "Equal roots mean the discriminant is zero. Put the unknown k into it.",
                        "The unknown k sits in the leading coefficient, so it appears in the "
                        "product inside the discriminant.",
                        "Write the discriminant with k as one of the coefficients and make it zero.",
                    ],
                    p,
                ),
                "You will get an equation that is linear in k. Undo each operation by doing the "
                "same thing to both sides.",
                "Full method: write the discriminant using k as the leading coefficient, set it "
                "to zero, collect the k term on one side by adding the same amount to both sides, "
                "then divide both sides by the number multiplying k.",
            ],
            wrong=[(mc, _rec(part, f"k = {fstr(v)}"), f"k = {fstr(v)}") for mc, v in wrong],
            key_text=f"k = {fstr(kval)}",
            tokens=[fstr(kval)],
            difficulty=clamp_difficulty(0.45, b, c, steps=3),
            role="apply",
            prediction="Will k have the same sign as the plain number?",
            methods=_k_methods("lead"),
            slug=_slug(c, g),
            tags=[f"marks:{tpl['form']['marks']}", "steps:3"],
        )


# ---------------------------------------------------------------- 9. equation from roots


def _equation_text(coeffs: list[int]) -> str:
    return f"{poly_text(coeffs)} = 0"


class FormFromRoots(Family):
    id = "form_from_roots"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        a, r1, r2 = p["a"], p["r1"], p["r2"]
        if r1 >= r2:
            raise IllPosed("needs_two_distinct_roots_in_order")
        s, pr = r1 + r2, r1 * r2
        key = [a * pr, -a * s, a]
        part, witness = quad_kernel(F(key[0]), F(key[1]), F(key[2]))
        cands = [
            ("MC.QUAD.FORM_SUM_SIGN", [a * pr, a * s, a]),
            ("MC.QUAD.FORM_PRODUCT_SIGN", [-a * pr, -a * s, a]),
            ("MC.QUAD.SUM_PRODUCT_CONFUSED", [a * s, -a * pr, a]),
            ("MC.QUAD.FORM_BOTH_SIGNS_FLIPPED", [-a * pr, a * s, a]),
        ]
        lead_txt = "" if a == 1 else f" The coefficient of x{SQ} is {a}."
        stem = pick(
            [
                f"Which quadratic equation has the roots {r1} and {r2}?{lead_txt}",
                f"Form the quadratic equation whose roots are {r1} and {r2}.{lead_txt}",
                f"Choose the quadratic equation that has {r1} and {r2} as its solutions.{lead_txt}",
            ],
            p,
        )

        def method_fn(kind: str) -> Callable[[Mapping[str, Any]], Any]:
            def run(spec: Mapping[str, Any]) -> Any:
                m = spec["model"]
                lead, x1, x2 = F(m["a"]), F(m["r1"]), F(m["r2"])
                if kind == "closed":
                    co = [lead * x1 * x2, -lead * (x1 + x2), lead]
                elif kind == "sympy":
                    x = sympy.Symbol("x")
                    expr = sympy.expand(
                        sympy.Rational(lead.numerator, lead.denominator)
                        * (x - sympy.Rational(x1.numerator, x1.denominator))
                        * (x - sympy.Rational(x2.numerator, x2.denominator))
                    )
                    cs = sympy.Poly(expr, x).all_coeffs()[::-1]
                    co = [F(int(v.p), int(v.q)) for v in cs]
                else:

                    def val(t: int) -> Fraction:
                        return lead * (t - x1) * (t - x2)

                    a0 = (val(1) + val(-1)) / 2 - val(0)
                    b0 = (val(1) - val(-1)) / 2
                    co = [val(0), b0, a0]
                ints = [int(v) for v in co]
                pt, _ = quad_kernel(co[0], co[1], co[2])
                return {**pt, "value": _equation_text(ints)}

            return run

        methods = [
            FnMethod(
                "maths.form.closed", "closed_form", "sum_and_product_of_roots", method_fn("closed")
            ),
            FnMethod("maths.form.sympy", "sympy.expand", "", method_fn("sympy")),
            FnMethod("maths.form.interp", "interpolation", "factor_theorem", method_fn("interp")),
        ]
        return Built(
            spec=_base_spec(key, None, {"family": self.id, "a": a, "r1": r1, "r2": r2}),
            answer=_rec(part, _equation_text(key)),
            witness=witness,
            stem=stem,
            steps=[
                f"A root r means (x - r) is a factor, so the factors are (x - ({r1})) and (x - ({r2})).",
                f"Multiply them: x{SQ} - ({s})x + ({pr}).",
                f"Multiply by the leading coefficient {a} if it is not 1: {_equation_text(key)}.",
            ],
            wrong=[(mc, _rec(part, _equation_text(c)), _equation_text(c)) for mc, c in cands],
            hints=[
                pick(
                    [
                        "A root tells you one bracket of the factorised form.",
                        "Think backwards from the solutions to the brackets that produce them.",
                        "Each root gives one factor; multiply the factors back together.",
                    ],
                    p,
                ),
                "To find each factor, undo x equals the root by doing the same thing to each side: "
                "take the root away from each side. Then multiply the two factors and collect terms.",
                "Full method: write one factor for each root, multiply the two brackets, collect "
                "like terms, then multiply every term by the stated leading coefficient.",
            ],
            key_text=_equation_text(key),
            tokens=[],
            difficulty=clamp_difficulty(0.35, a, r1, r2, steps=3),
            role="procedure",
            prediction="Will the x coefficient be the sum of the roots or its opposite?",
            methods=methods,
            slug=_slug(a, r1, r2),
            tags=[f"marks:{tpl['form']['marks']}", "steps:3"],
        )


# ---------------------------------------------------------------- 10. completing the square


class CompleteSquare(Family):
    id = "complete_square"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        h, c, ask = p["h"], p["c"], p["ask"]
        if h == 0:
            raise IllPosed("needs_a_nonzero_half_coefficient")
        coeffs = [c, 2 * h, 1]
        part, witness = quad_kernel(F(c), F(2 * h), F(1))
        k = h * h - c
        val = h if ask == "p" else k
        wrong_vals = (
            [
                ("MC.QUAD.CS_SIGN_OF_HALF", -h),
                ("MC.QUAD.CS_NOT_HALVED", 2 * h),
                ("MC.QUAD.CS_SQUARED_INSTEAD", h * h),
            ]
            if ask == "p"
            else [
                ("MC.QUAD.CS_ADDED_NOT_SUBTRACTED", h * h + c),
                ("MC.QUAD.CS_NOT_SQUARED", h - c),
                ("MC.QUAD.CS_NOT_HALVED", 4 * h * h - c),
                ("MC.QUAD.CS_SIGN_SWAPPED", c - h * h),
            ]
        )
        pbr = f"x + {h}" if h > 0 else f"x - {-h}"
        stem = pick(
            [
                f"The equation {poly_text(coeffs)} = 0 is rewritten by completing the square as "
                f"(x + p){SQ} = q. Find the value of {ask}.",
                f"Complete the square on {poly_text(coeffs)} = 0 to reach (x + p){SQ} = q. What is {ask}?",
                f"Writing {poly_text(coeffs)} = 0 in the form (x + p){SQ} = q gives which value of {ask}?",
            ],
            p,
        )

        def method_fn(kind: str) -> Callable[[Mapping[str, Any]], Any]:
            def run(spec: Mapping[str, Any]) -> Any:
                lhs = [F(v) for v in spec["lhs"]]
                ask_ = spec["model"]["ask"]
                if kind == "closed":
                    pp = lhs[1] / 2
                    qq = pp * pp - lhs[0]
                elif kind == "sympy":
                    x, pv, qv = sympy.symbols("x p q")
                    expr = sympy.expand(
                        (x + pv) ** 2
                        - qv
                        - sum(
                            sympy.Rational(v.numerator, v.denominator) * x**i
                            for i, v in enumerate(lhs)
                        )
                    )
                    sol = sympy.solve(sympy.Poly(expr, x).all_coeffs(), [pv, qv], dict=True)
                    pp = F(int(sol[0][pv].p), int(sol[0][pv].q))
                    qq = F(int(sol[0][qv].p), int(sol[0][qv].q))
                else:

                    def poly(t: int) -> Fraction:
                        return sum((v * t**i for i, v in enumerate(lhs)), F(0))

                    pp = (poly(1) - poly(-1)) / 4  # coefficient of x is 2p
                    qq = pp * pp - poly(0)
                info = ENGINES["closed"](spec)
                pt, _ = quad_kernel(info["c"], info["b"], info["a"])
                return {**pt, "value": fstr(pp if ask_ == "p" else qq)}

            return run

        return Built(
            spec=_base_spec(coeffs, None, {"family": self.id, "ask": ask}),
            answer=_rec(part, str(val)),
            witness=witness,
            stem=stem,
            steps=[
                f"Half of the x coefficient {2 * h} is {h}, so the square is ({pbr}){SQ}.",
                f"({pbr}){SQ} = x{SQ} + {2 * h}x + {h * h}, so add {h * h} to both sides and subtract {c} from both sides.",
                f"This gives ({pbr}){SQ} = {k}. So p = {h} and q = {k}.",
            ],
            wrong=[(mc, _rec(part, str(v)), str(v)) for mc, v in wrong_vals],
            hints=[
                pick(
                    [
                        "Halve the x coefficient to find what goes inside the bracket.",
                        "Think of one bracket squared; match the x term first.",
                        "Take the plain number away from both sides, then add whatever makes the left side "
                        "into one bracket squared.",
                    ],
                    p,
                ),
                "Whatever you add to one side you must add to both sides. Compare the expanded "
                "bracket with the original to see what is missing.",
                "Full method: halve the x coefficient, square it, add that square to both sides "
                "after taking the plain number away from both sides, write the left side as a bracket squared, "
                "and read off the two values.",
            ],
            key_text=str(val),
            tokens=[str(val)],
            difficulty=clamp_difficulty(0.5, h, c, steps=3),
            role="procedure",
            prediction="Will p have the same sign as the x coefficient?",
            methods=[
                FnMethod(
                    "maths.cs.closed", "closed_form", "complete_the_square", method_fn("closed")
                ),
                FnMethod("maths.cs.sympy", "sympy.solve", "", method_fn("sympy")),
                FnMethod(
                    "maths.cs.interp", "interpolation", "complete_the_square", method_fn("interp")
                ),
            ],
            slug=_slug(h, c, ask),
            tags=[f"marks:{tpl['form']['marks']}", "steps:3"],
        )


# ---------------------------------------------------------------- 11. check a root


class CheckRoot(Family):
    id = "check_root"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        a, r1, r2, which = p["a"], p["r1"], p["r2"], p["which"]
        if r1 >= r2:
            raise IllPosed("needs_two_distinct_roots_in_order")
        c0, b0 = a * r1 * r2, -a * (r1 + r2)
        coeffs = [c0, b0, a]
        part, witness = quad_kernel(F(c0), F(b0), F(a))
        r = (r1, r2)[which]

        def at(x: int) -> int:
            return a * x * x + b0 * x + c0

        cands = [
            ("MC.QUAD.CHECK_SIGN_FLIPPED", -r),
            ("MC.QUAD.CHECK_CONSTANT_TERM_USED", c0),
            ("MC.QUAD.CHECK_ONE_OFF", r + 1),
            ("MC.QUAD.CHECK_COEFFICIENT_USED", b0),
            ("MC.QUAD.CHECK_ONE_OFF", r - 1),
        ]
        wrong = [(mc, {"value": str(v)}, str(v)) for mc, v in cands if at(v) != 0]
        return Built(
            spec=_base_spec(coeffs, None, {"family": self.id, "which": which}),
            answer=_rec(part, str(r)),
            witness=witness,
            stem=pick(
                [
                    f"Which of these values of x satisfies the equation {poly_text(coeffs)} = 0?",
                    f"One of the following is a root of {poly_text(coeffs)} = 0. Which one?",
                    f"Which number makes the left side of {poly_text(coeffs)} = 0 equal to zero?",
                ],
                p,
            ),
            steps=[
                "A value satisfies the equation when substituting it makes the left side equal to 0.",
                f"Substitute x = {r}: {a}({r}){SQ} + ({b0})({r}) + ({c0}) = {at(r)}.",
                f"The left side is 0, so x = {r} satisfies the equation.",
            ],
            wrong=wrong,
            hints=[
                pick(
                    [
                        "Test each choice by putting it in place of x.",
                        "Solutions are the numbers that make the left side exactly zero.",
                        "You can check an answer without solving anything.",
                    ],
                    p,
                ),
                "Substitute the choices one after another, work out the left side carefully "
                "with its signs, and see whether it comes to zero.",
                "Full method: replace x by the choice, square first, then multiply by the "
                "coefficients, add the terms, and keep only the choice that gives zero.",
            ],
            key_text=str(r),
            tokens=[str(r)],
            difficulty=clamp_difficulty(0.1, a, r1, r2, steps=2),
            role="recall",
            prediction="Which choice looks most likely to work?",
            methods=quad_methods(
                lambda i, md: fstr(sorted(i["roots"])[md["which"]]), "substitution", "substitution"
            ),
            slug=_slug(a, r1, r2, which),
            tags=[f"marks:{tpl['form']['marks']}", "steps:2"],
        )


# ---------------------------------------------------------------- 12. word problems


def _word_methods(
    closed: Callable[[Mapping[str, Any]], Any],
    sym: Callable[[Mapping[str, Any]], Any],
    scan: Callable[[Mapping[str, Any]], Any],
    tech: str,
) -> list[FnMethod]:
    return [
        FnMethod("maths.word.closed", "closed_form", tech, closed),
        FnMethod("maths.word.sympy", "sympy.solve", "", sym),
        FnMethod("maths.word.scan", "enumeration", tech, scan),
    ]


def _poly_roots_answer(co: list[int], value: Fraction) -> dict[str, Any]:
    part, _ = quad_kernel(F(co[0]), F(co[1]), F(co[2]))
    return {**part, "value": fstr(value)}


def _sym_roots(co: list[int]) -> list[Fraction]:
    x = sympy.Symbol("x")
    sols = sympy.solve(sum(c * x**i for i, c in enumerate(co)), x)
    return sorted(F(int(s.p), int(s.q)) for s in sols)


class WordConsecutive(Family):
    id = "word_consecutive"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        s, n = p["s"], p["n"]
        prod = n * (n + s)
        co = [-prod, s, 1]
        part, witness = quad_kernel(F(co[0]), F(co[1]), F(1))
        kind = "integers" if s == 1 else ("even integers" if n % 2 == 0 else "odd integers")
        stem = f"The product of two consecutive positive {kind} is {prod}. Find the smaller one."
        cands = [
            ("MC.QUAD.WORD_LARGER_REPORTED", n + s),
            ("MC.QUAD.WORD_NEGATIVE_ROOT_KEPT", -(n + s)),
            ("MC.QUAD.WORD_SETUP_WRONG_DIFFERENCE", n - s),
            ("MC.QUAD.WORD_SUM_USED_FOR_PRODUCT", n + (n + s)),
        ]

        def closed(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            root = rational_sqrt(F(m["s"] ** 2 + 4 * m["P"]))
            assert root is not None
            val = (-F(m["s"]) + root) / 2
            return _poly_roots_answer([-m["P"], m["s"], 1], val)

        def sym(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            roots = _sym_roots([-m["P"], m["s"], 1])
            return _poly_roots_answer([-m["P"], m["s"], 1], max(roots))

        def scan(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            hits = [x for x in range(1, m["P"] + 1) if x * (x + m["s"]) == m["P"]]
            if len(hits) != 1:
                raise ValueError("not exactly one positive solution")
            return _poly_roots_answer([-m["P"], m["s"], 1], F(hits[0]))

        return Built(
            spec=_base_spec(co, None, {"family": self.id, "P": prod, "s": s}),
            answer=_rec(part, str(n)),
            witness=witness,
            stem=stem,
            steps=[
                f"Let x be the smaller number. The other is x + {s}.",
                f"Their product is {prod}, so x(x + {s}) = {prod}, which is x{SQ} + {s}x - {prod} = 0.",
                f"Factorise: (x - {n})(x + {n + s}) = 0, so x = {n} or x = {-(n + s)}.",
                f"The numbers must be positive, so the smaller number is {n}.",
            ],
            wrong=[(mc, _rec(part, str(v)), str(v)) for mc, v in cands],
            hints=[
                pick(
                    [
                        "Let x be the smaller number and write the other number using x.",
                        "Let x stand for the smaller number, then express the larger one with x.",
                        "Let x be the number you are asked for and write the other number in terms of x.",
                    ],
                    p,
                ),
                "Write the product as one relation in x, bring every term to one side, then "
                "factorise or use the formula. Check which solution fits the words of the question.",
                "Full method: name the smaller number, write the larger one, form the product "
                "relation, rearrange so the right side is zero, solve, and reject any solution "
                "that is not positive.",
            ],
            key_text=str(n),
            tokens=[str(n)],
            difficulty=clamp_difficulty(0.45, n, prod, steps=4),
            role="apply",
            prediction="Roughly how big do you expect the smaller number to be?",
            methods=_word_methods(closed, sym, scan, "model_with_quadratic"),
            slug=_slug(s, n),
            tags=[f"marks:{tpl['form']['marks']}", "steps:4"],
        )


class WordRectangle(Family):
    id = "word_rectangle"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        d, w, ask, rate = p["d"], p["w"], p["ask"], p["rate"]
        if ask != "cost" and rate != tpl["box"]["rate"]["choices"][0]:
            raise IllPosed("rate_only_matters_for_the_cost_question")
        area = w * (w + d)
        co = [-area, d, 1]
        part, witness = quad_kernel(F(co[0]), F(d), F(1))
        perim = 2 * (2 * w + d)
        if ask == "breadth":
            stem = (
                f"The length of a rectangular field is {d} m more than its breadth. Its area is "
                f"{area} m{SQ}. Find the breadth of the field in metres."
            )
            val = w
            cands = [
                ("MC.QUAD.WORD_LENGTH_REPORTED", w + d),
                ("MC.QUAD.WORD_NEGATIVE_ROOT_KEPT", -(w + d)),
                ("MC.QUAD.WORD_SEMIPERIMETER_FOR_SIDE", 2 * w + d),
            ]
        elif ask == "length":
            stem = (
                f"A rectangular plot has a length that is {d} m more than its breadth. The plot "
                f"covers {area} m{SQ}. Find the length of the plot in metres."
            )
            val = w + d
            cands = [
                ("MC.QUAD.WORD_BREADTH_REPORTED", w),
                ("MC.QUAD.WORD_DIFFERENCE_ADDED_TWICE", w + 2 * d),
                ("MC.QUAD.WORD_NEGATIVE_ROOT_KEPT", -w),
            ]
        else:
            stem = (
                f"A school garden is rectangular. Its length is {d} m more than its breadth and "
                f"it covers {area} m{SQ}. The garden is to be fenced all the way round and the "
                f"fencing costs {rate} rupees per metre. Find the total cost of the fencing in rupees."
            )
            val = perim * rate
            cands = [
                ("MC.QUAD.WORD_HALF_PERIMETER", (2 * w + d) * rate),
                ("MC.QUAD.WORD_AREA_NOT_PERIMETER", area * rate),
                ("MC.QUAD.WORD_LENGTH_AS_BREADTH", 2 * (2 * w + 3 * d) * rate),
                ("MC.QUAD.WORD_FORGOT_FINAL_STEP", perim),
            ]

        def answer_of(width: Fraction, m: Mapping[str, Any]) -> Any:
            dd, rr = F(m["d"]), F(m.get("rate", 1))
            out = {"breadth": width, "length": width + dd, "cost": 2 * (2 * width + dd) * rr}
            return _poly_roots_answer([-m["A"], m["d"], 1], out[m["ask"]])

        def closed(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            root = rational_sqrt(F(m["d"] ** 2 + 4 * m["A"]))
            assert root is not None
            return answer_of((-F(m["d"]) + root) / 2, m)

        def sym(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            return answer_of(max(_sym_roots([-m["A"], m["d"], 1])), m)

        def scan(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            hits = [x for x in range(1, m["A"] + 1) if x * (x + m["d"]) == m["A"]]
            if len(hits) != 1:
                raise ValueError("not exactly one positive solution")
            return answer_of(F(hits[0]), m)

        model = {"family": self.id, "d": d, "A": area, "ask": ask, "rate": rate}
        return Built(
            spec=_base_spec(co, None, model),
            answer=_rec(part, str(val)),
            witness=witness,
            stem=stem,
            steps=[
                f"Let x metres be the breadth. Then the length is x + {d} metres.",
                f"The area gives x(x + {d}) = {area}, so x{SQ} + {d}x - {area} = 0.",
                f"Factorise: (x - {w})(x + {w + d}) = 0, so x = {w} or x = {-(w + d)}; a length is "
                f"positive, so the breadth is {w} m and the length is {w + d} m.",
                *(
                    [
                        f"The perimeter is 2({w} + {w + d}) = {perim} m, and the cost is {perim} x {rate}."
                    ]
                    if ask == "cost"
                    else []
                ),
            ],
            wrong=[(mc, _rec(part, str(v)), str(v)) for mc, v in cands],
            hints=[
                pick(
                    [
                        "Let x be the breadth and write the length using x, then use the area.",
                        "Let x stand for the breadth, then write the length in terms of x.",
                        "Let x be the unknown side, express the other side with x, then use the area.",
                    ],
                    p,
                ),
                "Write the area as one relation in x, rearrange so the right side is zero, and "
                "solve it. Discard any solution that makes the length negative. Undo each step by "
                "doing the same thing to each side.",
                "Full method: name the breadth, write the length, form the area relation, "
                "rearrange to zero, factorise, keep the positive solution, then answer exactly "
                "what is asked (breadth, length or cost).",
            ],
            key_text=str(val),
            tokens=[str(val)],
            difficulty=clamp_difficulty(
                0.4 if ask != "cost" else 0.6, w, d, steps=4 + (ask == "cost")
            ),
            role="apply" if ask != "cost" else "transfer",
            prediction="About how long do you think the shorter side is?",
            methods=_word_methods(closed, sym, scan, "model_with_quadratic"),
            slug=_slug(d, w, ask, rate if ask == "cost" else 0),
            tags=[f"marks:{tpl['form']['marks']}", f"steps:{4 + (ask == 'cost')}"],
        )


class WordTriangle(Family):
    id = "word_triangle"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        x, d, ask = p["x"], p["d"], p["ask"]
        h2 = x * x + (x + d) ** 2
        h = math.isqrt(h2)
        if h * h != h2:
            raise IllPosed("hypotenuse_not_a_whole_number")
        if h > 150:
            raise IllPosed("park_too_large_to_be_sensible")
        co = [d * d - h2, 2 * d, 2]
        part, witness = quad_kernel(F(co[0]), F(co[1]), F(co[2]))
        val = x if ask == "shorter" else x + d
        word = "shorter" if ask == "shorter" else "longer"
        stem = (
            f"A triangular park has a right angle. The two sides that meet at the right angle "
            f"differ in length by {d} m, and the longest side is {h} m. Find the length of the "
            f"{word} of the two sides in metres."
        )
        cands = [
            ("MC.QUAD.WORD_OTHER_SIDE_REPORTED", (x + d) if ask == "shorter" else x),
            ("MC.QUAD.WORD_NEGATIVE_ROOT_KEPT", -(x + d)),
            ("MC.QUAD.WORD_HYPOTENUSE_MINUS_DIFFERENCE", h - d),
            ("MC.QUAD.WORD_SIDES_SUMMED", h - x),
        ]

        def answer_of(short: Fraction, m: Mapping[str, Any]) -> Any:
            return _poly_roots_answer(
                [m["d"] ** 2 - m["h"] ** 2, 2 * m["d"], 2],
                short if m["ask"] == "shorter" else short + m["d"],
            )

        def closed(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            disc = F(4 * m["d"] ** 2 - 8 * (m["d"] ** 2 - m["h"] ** 2))
            root = rational_sqrt(disc)
            assert root is not None
            return answer_of((-F(2 * m["d"]) + root) / 4, m)

        def sym(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            sols = _sym_roots([m["d"] ** 2 - m["h"] ** 2, 2 * m["d"], 2])
            return answer_of(max(sols), m)

        def scan(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            hits = [t for t in range(1, m["h"]) if t * t + (t + m["d"]) ** 2 == m["h"] ** 2]
            if len(hits) != 1:
                raise ValueError("not exactly one positive solution")
            return answer_of(F(hits[0]), m)

        return Built(
            spec=_base_spec(co, None, {"family": self.id, "d": d, "h": h, "ask": ask}),
            answer=_rec(part, str(val)),
            witness=witness,
            stem=stem,
            steps=[
                f"Let x metres be the shorter side. The other side is x + {d} metres.",
                f"By Pythagoras, x{SQ} + (x + {d}){SQ} = {h}{SQ}, so 2x{SQ} + {2 * d}x - {h2 - d * d} = 0.",
                f"Divide both sides by 2 and factorise: (x - {x})(x + {x + d}) = 0, so x = {x} (a length cannot be negative).",
                f"The shorter side is {x} m and the longer side is {x + d} m.",
            ],
            wrong=[(mc, _rec(part, str(v)), str(v)) for mc, v in cands],
            hints=[
                pick(
                    [
                        "Let x be the shorter side and write the other side using x. The longest side "
                        "is opposite the right angle.",
                        "Let x stand for the shorter side, then write the other side with x.",
                        "Let x be the unknown short side and give the other side in terms of x.",
                    ],
                    p,
                ),
                "Use the relation for the sides of this triangle, expand the bracket carefully, "
                "bring every term to one side, then solve. Undo each step by doing the same thing "
                "to each side.",
                "Full method: name the shorter side, write the longer one, apply the rule linking "
                "the three sides, expand, rearrange to zero, divide out any common factor, solve, "
                "and keep the positive solution.",
            ],
            key_text=str(val),
            tokens=[str(val)],
            difficulty=clamp_difficulty(0.55, x, d, steps=5),
            role="transfer",
            prediction="Is the shorter side more or less than half the longest side?",
            methods=_word_methods(closed, sym, scan, "model_with_quadratic"),
            slug=_slug(x, d, ask),
            tags=[f"marks:{tpl['form']['marks']}", "steps:5"],
        )


class WordMotion(Family):
    id = "word_motion"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        v, s, t, ask = p["v"], p["s"], p["t"], p["ask"]
        num = t * v * (v + s)
        if num % s:
            raise IllPosed("journey_distance_not_a_whole_number")
        dist = num // s
        if dist > 900:
            raise IllPosed("journey_too_long_to_be_sensible")
        co = [-dist * s, t * s, t]
        part, witness = quad_kernel(F(co[0]), F(co[1]), F(co[2]))
        plural = "s" if t > 1 else ""
        stem = (
            f"A bus travels {dist} km along a fixed route at a steady speed. If it travelled "
            f"{s} km/h faster, the journey would take {t} hour{plural} less. "
            + (
                "Find the usual speed of the bus in km/h."
                if ask == "usual"
                else "Find the speed of the bus on the faster run in km/h."
            )
        )
        val = v if ask == "usual" else v + s
        cands = [
            ("MC.QUAD.WORD_OTHER_SPEED_REPORTED", (v + s) if ask == "usual" else v),
            ("MC.QUAD.WORD_NEGATIVE_ROOT_KEPT", -(v + s)),
            ("MC.QUAD.WORD_INCREASE_SUBTRACTED", v - s),
            ("MC.QUAD.WORD_INCREASE_ONLY", s),
        ]

        def answer_of(speed: Fraction, m: Mapping[str, Any]) -> Any:
            co2 = [-m["D"] * m["s"], m["t"] * m["s"], m["t"]]
            return _poly_roots_answer(co2, speed if m["ask"] == "usual" else speed + m["s"])

        def closed(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            b, a, c = F(m["t"] * m["s"]), F(m["t"]), F(-m["D"] * m["s"])
            root = rational_sqrt(b * b - 4 * a * c)
            assert root is not None
            return answer_of((-b + root) / (2 * a), m)

        def sym(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            x = sympy.Symbol("x", positive=True)
            sols = sympy.solve(
                sympy.Rational(m["D"]) / x - sympy.Rational(m["D"]) / (x + m["s"]) - m["t"], x
            )
            if len(sols) != 1:
                raise ValueError("not exactly one positive solution")
            return answer_of(F(int(sols[0].p), int(sols[0].q)), m)

        def scan(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            hits = [sp for sp in range(1, 400) if F(m["D"], sp) - F(m["D"], sp + m["s"]) == m["t"]]
            if len(hits) != 1:
                raise ValueError("not exactly one positive solution")
            return answer_of(F(hits[0]), m)

        return Built(
            spec=_base_spec(co, None, {"family": self.id, "D": dist, "s": s, "t": t, "ask": ask}),
            answer=_rec(part, str(val)),
            witness=witness,
            stem=stem,
            steps=[
                f"Let x km/h be the usual speed. The time taken is {dist}/x hours, and at the higher speed it is {dist}/(x + {s}) hours.",
                f"The saving is {t}: {dist}/x - {dist}/(x + {s}) = {t}. Multiply every term by x(x + {s}) to clear the fractions.",
                f"This gives {t}x{SQ} + {t * s}x - {dist * s} = 0, which factorises as (x - {v})(x + {v + s}) = 0 after dividing by {t}.",
                f"A speed is positive, so the usual speed is {v} km/h and the faster speed is {v + s} km/h.",
            ],
            wrong=[(mc, _rec(part, str(w)), str(w)) for mc, w in cands],
            hints=[
                pick(
                    [
                        "Let x be the usual speed. Time equals distance divided by speed, so write "
                        "both journey times using x.",
                        "Let x stand for the usual speed and write the time for each journey with x.",
                        "Let x be the usual speed, then express the two journey times in terms of x.",
                    ],
                    p,
                ),
                "Subtract the two times and set the difference equal to the time saved. Multiply "
                "every term by the same expression to clear the fractions, then solve. Do the same "
                "thing to each side at every step.",
                "Full method: name the usual speed, write the two times, form the difference "
                "relation, clear the fractions by multiplying every term, rearrange to zero, solve, "
                "reject the negative speed, then answer the speed that was asked for.",
            ],
            key_text=str(val),
            tokens=[str(val)],
            difficulty=clamp_difficulty(0.65, v, dist, steps=5),
            role="transfer",
            prediction="Will the usual speed be more or less than the increase in speed?",
            methods=_word_methods(closed, sym, scan, "model_with_quadratic"),
            slug=_slug(v, s, t, ask),
            tags=[f"marks:{tpl['form']['marks']}", "steps:5"],
        )


QUAD_FAMILIES: dict[str, Family] = {
    f.id: f
    for f in (
        StdForm(), SolveFactor(), FormulaRational(), IncompletePure(), IncompleteX(),
        FormulaSurd(), Discriminant(), Nature(), FindKMiddle(), FindKLead(), FormFromRoots(),
        CompleteSquare(), CheckRoot(), WordConsecutive(), WordRectangle(), WordTriangle(),
        WordMotion(),
    )
}  # fmt: skip
