# ruff: noqa: E501
"""Arithmetic Progressions families (Class 10 algebra). Built backward from a, d and n.

AP maths is not in the kernel, so each item carries a kernel-checkable LINEAR model (the equation
the unknown solves, or the 2x2 system for a and d) and independent LANE methods that compute the
answer from the structured model: a closed form, a term-by-term enumeration (the definition of an
AP, no formula) and SymPy (recurrence or symbolic sum). Two methods must agree before a stamp.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from fractions import Fraction
from typing import Any

import sympy

from app.factory.lanes.maths.core import (
    Built,
    Family,
    FnMethod,
    IllPosed,
    clamp_difficulty,
    fstr,
    pick,
    quad_kernel,
)

F = Fraction


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}" + {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def _slug(*parts: Any) -> str:
    return "_".join(str(x).replace("-", "m").replace("/", "d") for x in parts)


def scalar(v: Fraction, *, extra: dict[str, Any] | None = None) -> tuple[dict, dict, list[Any]]:
    """Kernel pieces for 'the unknown u equals v': u - v = 0."""
    part = {"roots": [fstr(v)], "count": 1, **(extra or {})}
    witness = {"split": {"lead": 1, "roots": [[fstr(v), 1]]}}
    return part, witness, [fstr(-v), 1]


def _spec(lhs: list[Any], model: dict[str, Any]) -> dict[str, Any]:
    return {"domain": "algebra", "kind": "polynomial", "lhs": lhs, "model": model}


def terms_text(vals: list[Fraction], ellipsis: bool = True) -> str:
    return ", ".join(fstr(v) for v in vals) + (", ..." if ellipsis else "")


def ap_terms(a: Fraction, d: Fraction, n: int) -> list[Fraction]:
    out = [a]
    for _ in range(n - 1):
        out.append(out[-1] + d)
    return out


def _methods(
    closed: Callable[[Mapping[str, Any]], Any],
    enum: Callable[[Mapping[str, Any]], Any],
    sym: Callable[[Mapping[str, Any]], Any],
    tech: str,
) -> list[FnMethod]:
    return [
        FnMethod("maths.ap.closed", "closed_form", tech, closed),
        FnMethod("maths.ap.enumeration", "enumeration", tech, enum),
        FnMethod("maths.ap.sympy", "sympy.rsolve", "", sym),
    ]


def _scalar_answer(v: Fraction) -> dict[str, Any]:
    return scalar(v)[0]


def _sym_nth(a: Fraction, d: Fraction, n: int) -> Fraction:
    """a_n from the recurrence f(k+1) = f(k) + d, f(0) = a, by SymPy's recurrence solver."""
    k = sympy.Symbol("k", integer=True)
    f = sympy.Function("f")
    sol = sympy.rsolve(
        f(k + 1) - f(k) - sympy.Rational(d.numerator, d.denominator),
        f(k),
        {f(0): sympy.Rational(a.numerator, a.denominator)},
    )
    val = sympy.nsimplify(sol.subs(k, n - 1))
    return F(int(val.p), int(val.q))


def _sym_sum(a: Fraction, d: Fraction, n: int) -> Fraction:
    k = sympy.Symbol("k", integer=True)
    total = sympy.summation(
        sympy.Rational(a.numerator, a.denominator) + k * sympy.Rational(d.numerator, d.denominator),
        (k, 0, n - 1),
    )
    return F(int(total.p), int(total.q))


# ---------------------------------------------------------------- 1. common difference


class CommonDifference(Family):
    id = "ap_diff"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        a, d, den = p["a"], p["d"], p["den"]
        if d == 0:
            raise IllPosed("difference_must_be_nonzero")
        terms = [F(a + k * d, den) for k in range(4)]
        dd = F(d, den)
        part, witness, lhs = scalar(dd)
        wrong = [
            ("MC.AP.DIFF_SIGN_REVERSED", -dd),
            ("MC.AP.DIFF_AS_RATIO", terms[1] / terms[0] if terms[0] != 0 else F(0)),
            ("MC.AP.DIFF_FIRST_TERM_GIVEN", terms[0]),
            ("MC.AP.DIFF_SKIPPED_TERM", 2 * dd),
            ("MC.AP.DIFF_LAST_TERM_GIVEN", terms[3]),
        ]

        def closed(spec: Mapping[str, Any]) -> Any:
            t = [F(x) for x in spec["model"]["terms"]]
            diffs = {t[i + 1] - t[i] for i in range(len(t) - 1)}
            if len(diffs) != 1:
                raise ValueError("not an AP")
            return _scalar_answer(diffs.pop())

        def enum(spec: Mapping[str, Any]) -> Any:
            t = [F(x) for x in spec["model"]["terms"]]
            seen = []
            for left, right in zip(t, t[1:], strict=False):
                seen.append(right - left)
            if any(x != seen[0] for x in seen):
                raise ValueError("not an AP")
            return _scalar_answer(seen[0])

        def sym(spec: Mapping[str, Any]) -> Any:
            t = [sympy.Rational(F(x).numerator, F(x).denominator) for x in spec["model"]["terms"]]
            a0, d0 = sympy.symbols("a0 d0")
            sol = sympy.solve([a0 + i * d0 - v for i, v in enumerate(t[:2])], [a0, d0], dict=True)[
                0
            ]
            if any(sol[a0] + i * sol[d0] != v for i, v in enumerate(t)):
                raise ValueError("not an AP")
            return _scalar_answer(F(int(sol[d0].p), int(sol[d0].q)))

        return Built(
            spec=_spec(lhs, {"family": self.id, "terms": [fstr(x) for x in terms]}),
            answer=part,
            witness=witness,
            stem=pick(
                [
                    f"Find the common difference of the list {terms_text(terms)}",
                    f"What is the common difference of the AP {terms_text(terms)}?",
                    f"The numbers {terms_text(terms)} follow an arithmetic progression. State its common difference.",
                ],
                {"v": a + 2 * d + den},
            ),
            steps=[
                "In an AP every term is the previous term plus the same number, the common difference.",
                f"Subtract a term from the one after it: {fstr(terms[1])} - ({fstr(terms[0])}) = {fstr(dd)}.",
                f"Check with another pair: {fstr(terms[2])} - ({fstr(terms[1])}) = {fstr(dd)}. The common difference is {fstr(dd)}.",
            ],
            hints=[
                pick(
                    [
                        "Compare two neighbouring terms: how much is added each time?",
                        "Subtract each term from the one after it and see what you get.",
                        "The common difference is the same jump between every pair of neighbours.",
                    ],
                    p,
                ),
                "Take the later term and subtract the earlier one, keeping the order and the sign. "
                "Then try another pair to be sure the jump is the same.",
                "Full method: pick two neighbouring terms, subtract the earlier from the later, "
                "check with another pair, and keep the sign: a falling list has a negative "
                "difference.",
            ],
            wrong=[(mc, _scalar_answer(v), fstr(v)) for mc, v in wrong],
            key_text=fstr(dd),
            tokens=[fstr(dd)],
            difficulty=clamp_difficulty(0.1, a, d, steps=2),
            role="recall",
            prediction="Is the list going up or down, and by roughly how much each step?",
            methods=_methods(closed, enum, sym, "common_difference"),
            slug=_slug(a, d, den),
            tags=[f"marks:{tpl['form']['marks']}", "steps:2"],
        )


# ---------------------------------------------------------------- 2. identify an AP


class IdentifyAP(Family):
    id = "ap_identify"
    version = "2"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        a, d, g, brk = p["a"], p["d"], p["g"], p["brk"]
        key = [a + k * d for k in range(4)]
        geo = [a * g**k for k in range(4)]
        broken = [*key[:3], key[3] + brk]
        rising = [a, a + d, a + 2 * d + 1, a + 3 * d + 3]
        lists = {
            "MC.AP.RATIO_FOR_DIFFERENCE": geo,
            "MC.AP.CHECKED_TWO_TERMS_ONLY": broken,
            "MC.AP.DIFFERENCES_INCREASING_ACCEPTED": rising,
        }
        if len({tuple(x) for x in [key, geo, broken, rising]}) != 4:
            raise IllPosed("lists_must_be_distinct")
        for lst in (geo, broken, rising):
            if len({lst[i + 1] - lst[i] for i in range(3)}) == 1:
                raise IllPosed("a_distractor_is_also_an_ap")
        part, witness, lhs = scalar(F(d), extra={"value": terms_text([F(x) for x in key], False)})
        all_lists = [key, *lists.values()]

        def closed(spec: Mapping[str, Any]) -> Any:
            found = []
            for lst in spec["model"]["lists"]:
                t = [F(x) for x in lst]
                if len({t[i + 1] - t[i] for i in range(len(t) - 1)}) == 1:
                    found.append(t)
            if len(found) != 1:
                raise ValueError("not exactly one AP among the lists")
            t = found[0]
            return {**_scalar_answer(t[1] - t[0]), "value": terms_text(t, False)}

        def enum(spec: Mapping[str, Any]) -> Any:
            found = []
            for lst in spec["model"]["lists"]:
                t = [F(x) for x in lst]
                if all(t[i + 1] - t[i] == t[1] - t[0] for i in range(len(t) - 1)):
                    found.append(t)
            if len(found) != 1:
                raise ValueError("not exactly one AP among the lists")
            t = found[0]
            return {**_scalar_answer(t[1] - t[0]), "value": terms_text(t, False)}

        def sym(spec: Mapping[str, Any]) -> Any:
            x = sympy.Symbol("x")
            found = []
            for lst in spec["model"]["lists"]:
                t = [F(v) for v in lst]
                poly = sympy.interpolate(
                    [(i, sympy.Rational(v.numerator, v.denominator)) for i, v in enumerate(t)], x
                )
                if sympy.Poly(poly, x).degree() <= 1:
                    found.append((t, sympy.Poly(poly, x).coeff_monomial(x)))
            if len(found) != 1:
                raise ValueError("not exactly one AP among the lists")
            t, slope = found[0]
            return {**_scalar_answer(F(int(slope.p), int(slope.q))), "value": terms_text(t, False)}

        return Built(
            spec=_spec(
                lhs, {"family": self.id, "lists": [[fstr(F(v)) for v in lst] for lst in all_lists]}
            ),
            answer=part,
            witness=witness,
            stem=pick(
                [
                    f"Every list starts at {a}. Which of these lists is an arithmetic progression?",
                    f"Exactly one of these lists, all starting at {a}, is an AP. Which one?",
                    f"All the lists begin with {a}. Choose the one in which the gap between neighbouring terms never changes.",
                ],
                {"a": a, "d": d, "g": g},
            ),
            steps=[
                "A list is an AP when the difference between every pair of neighbouring terms is the same.",
                f"In {terms_text([F(x) for x in key], False)} each step is {d}, and it stays {d} all the way along.",
                "In each of the other lists, at least one pair of neighbours has a different difference.",
            ],
            hints=[
                pick(
                    [
                        "An AP keeps adding the same amount; test every neighbouring pair.",
                        "Work out the gaps between neighbours for each list and compare them.",
                        "Checking only the first two terms is not enough.",
                    ],
                    p,
                ),
                "For each list subtract every term from the next one. A list passes only when all "
                "its gaps are identical.",
                "Full method: for every list write down the three gaps between neighbours, "
                "compare them, and keep the one list whose gaps are all equal.",
            ],
            wrong=[
                (
                    mc,
                    {"value": terms_text([F(x) for x in lst], False), "count": 1},
                    terms_text([F(x) for x in lst], False),
                )
                for mc, lst in lists.items()
            ],
            key_text=terms_text([F(x) for x in key], False),
            tokens=[terms_text([F(x) for x in key], False)],
            difficulty=clamp_difficulty(0.25, a, d, steps=3),
            role="recall",
            prediction="Which list do you suspect, and why?",
            methods=_methods(closed, enum, sym, "common_difference"),
            slug=_slug(a, d, g, brk),
            tags=[f"marks:{tpl['form']['marks']}", "steps:3"],
        )


# ---------------------------------------------------------------- 3. nth term


class NthTerm(Family):
    id = "ap_nth"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        a, d, n, style = p["a"], p["d"], p["n"], p["style"]
        if d == 0:
            raise IllPosed("difference_must_be_nonzero")
        an = F(a + (n - 1) * d)
        part, witness, lhs = scalar(an)
        first = [F(a + k * d) for k in range(3)]
        wrong = [
            ("MC.AP.NTH_N_FOR_N_MINUS_1", F(a + n * d)),
            ("MC.AP.NTH_D_ADDED_NOT_MULTIPLIED", F(a + (n - 1) + d)),
            ("MC.AP.NTH_SIGN_OF_D_FLIPPED", F(a - (n - 1) * d)),
            ("MC.AP.NTH_FIRST_TERM_DROPPED", F((n - 1) * d)),
            ("MC.AP.NTH_OFF_BY_ONE_LOW", F(a + (n - 2) * d)),
        ]
        if style == 0:
            stem = pick(
                [
                    f"Find the {ordinal(n)} term of the AP {terms_text(first)}",
                    f"What is the {ordinal(n)} term of the progression {terms_text(first)}?",
                ],
                {"a": a, "d": d, "n": n},
            )
        else:
            stem = pick(
                [
                    f"The first term of an AP is {a} and its common difference is {d}. "
                    f"Find the {ordinal(n)} term.",
                    f"An AP starts at {a} and changes by {d} at every step. "
                    f"What is its {ordinal(n)} term?",
                ],
                {"a": a, "d": d, "n": n},
            )

        def closed(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            return _scalar_answer(F(m["a"]) + (m["n"] - 1) * F(m["d"]))

        def enum(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            return _scalar_answer(ap_terms(F(m["a"]), F(m["d"]), m["n"])[-1])

        def sym(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            return _scalar_answer(_sym_nth(F(m["a"]), F(m["d"]), m["n"]))

        return Built(
            spec=_spec(lhs, {"family": self.id, "a": a, "d": d, "n": n}),
            answer=part,
            witness=witness,
            stem=stem,
            steps=[
                f"The first term is {a} and the common difference is {d}.",
                f"The nth term is first term + (n - 1) x difference, so a_{n} = {a} + ({n} - 1)({d}).",
                f"a_{n} = {a} + {(n - 1) * d} = {fstr(an)}.",
            ],
            hints=[
                pick(
                    [
                        "Start at the first term and count how many jumps you need to reach the one asked for.",
                        "To reach the nth term you make one fewer jump than n.",
                        "Each step adds the common difference; count the steps from the first term.",
                    ],
                    p,
                ),
                "The number of jumps is one less than the position. Multiply the difference by the "
                "number of jumps, then add the result to the first term.",
                "Full method: identify the first term and the common difference, count the jumps "
                "which is the position minus one, multiply by the difference, and add to the "
                "first term.",
            ],
            wrong=[(mc, _scalar_answer(v), fstr(v)) for mc, v in wrong],
            key_text=fstr(an),
            tokens=[fstr(an)],
            difficulty=clamp_difficulty(0.2, a, d, n, steps=3),
            role="procedure",
            prediction="Will the term be much bigger or smaller than the first term?",
            methods=_methods(closed, enum, sym, "nth_term_formula"),
            slug=_slug(a, d, n, style),
            tags=[f"marks:{tpl['form']['marks']}", "steps:3"],
        )


# ---------------------------------------------------------------- 4. which term


class WhichTerm(Family):
    id = "ap_which_term"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        a, d, n = p["a"], p["d"], p["n"]
        if d == 0:
            raise IllPosed("difference_must_be_nonzero")
        x = a + (n - 1) * d
        part, _, _ = scalar(F(n))
        lhs = [a - d - x, d]  # a + (n - 1) d - x = 0 in the unknown n
        witness = {"split": {"lead": d, "roots": [[fstr(F(n)), 1]]}}
        first = [F(a + k * d) for k in range(3)]
        wrong = [
            ("MC.AP.FIND_N_FORGOT_PLUS_ONE", F(n - 1)),
            ("MC.AP.FIND_N_OVERCOUNT", F(n + 1)),
            ("MC.AP.FIND_N_DIFFERENCE_NOT_DIVIDED", F(x - a)),
            ("MC.AP.FIND_N_VALUE_OVER_DIFFERENCE", F(x, d)),
        ]
        stem = pick(
            [
                f"Which term of the AP {terms_text(first)} is {x}?",
                f"The AP {terms_text(first)} has a term equal to {x}. What is the position of that term?",
                f"In the progression {terms_text(first)} the number {x} appears. Which term is it?",
            ],
            {"a": a, "d": d, "n": n},
        )

        def closed(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            return _scalar_answer((F(m["x"]) - F(m["a"])) / F(m["d"]) + 1)

        def enum(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            a0, d0, target = F(m["a"]), F(m["d"]), F(m["x"])
            hits, term = [], a0
            for pos in range(1, 400):
                if term == target:
                    hits.append(pos)
                term += d0
            if len(hits) != 1:
                raise ValueError("target appears zero or several times")
            return _scalar_answer(F(hits[0]))

        def sym(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            nn = sympy.Symbol("n")
            sol = sympy.solve(
                sympy.Rational(m["a"]) + (nn - 1) * sympy.Rational(m["d"]) - sympy.Rational(m["x"]),
                nn,
            )
            if len(sol) != 1:
                raise ValueError("no unique position")
            return _scalar_answer(F(int(sol[0].p), int(sol[0].q)))

        return Built(
            spec=_spec(lhs, {"family": self.id, "a": a, "d": d, "x": x}),
            answer=part,
            witness=witness,
            stem=stem,
            steps=[
                f"The first term is {a} and the common difference is {d}.",
                f"Set the nth term equal to {x}: {a} + (n - 1)({d}) = {x}.",
                f"Take {a} away from both sides: (n - 1)({d}) = {x - a}. Divide both sides by {d}: n - 1 = {fstr(F(x - a, d))}.",
                f"Add 1 to both sides: n = {n}.",
            ],
            hints=[
                pick(
                    [
                        "Write the rule for the nth term and make it equal to the given number.",
                        "You need the position n, so treat n as the unknown in the rule for any term.",
                        "Use the rule for the nth term, but this time n is the thing you do not know.",
                    ],
                    p,
                ),
                "Undo each operation in the rule by doing the same thing to each side: first take "
                "away the first term, then divide by the difference, then deal with the minus one.",
                "Full method: write first term + (n - 1) x difference, set it equal to the target, "
                "take away the first term from each side, divide each side by the difference, and "
                "add one to each side.",
            ],
            wrong=[(mc, _scalar_answer(v), fstr(v)) for mc, v in wrong],
            key_text=str(n),
            tokens=[str(n)],
            difficulty=clamp_difficulty(0.3, a, d, n, steps=4),
            role="procedure",
            prediction="Roughly how many steps from the first term will it take to reach this number?",
            methods=_methods(closed, enum, sym, "nth_term_formula"),
            slug=_slug(a, d, n),
            tags=[f"marks:{tpl['form']['marks']}", "steps:4"],
        )


# ---------------------------------------------------------------- 5. two terms given


class TwoTerms(Family):
    id = "ap_two_terms"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        a, d, pp, gap, r = p["a"], p["d"], p["p"], p["gap"], p["r"]
        q = pp + gap
        if r in (pp, q):
            raise IllPosed("asked_term_must_not_be_given")
        ap_, aq = a + (pp - 1) * d, a + (q - 1) * d
        ar = F(a + (r - 1) * d)
        values = {"a": fstr(F(a)), "d": fstr(F(d))}
        dd_wrong = F(aq - ap_)  # forgot to divide by the gap
        a_wrong = ap_ - (pp - 1) * dd_wrong
        wrong = [
            ("MC.AP.TWO_TERMS_DIFF_NOT_DIVIDED", a_wrong + (r - 1) * dd_wrong),
            ("MC.AP.TWO_TERMS_STARTED_FROM_GIVEN_TERM", F(ap_) + (r - 1) * d),
            ("MC.AP.NTH_N_FOR_N_MINUS_1", F(a + r * d)),
            ("MC.AP.DIFF_SIGN_REVERSED", F(a - (r - 1) * d)),
        ]
        spec = {
            "domain": "algebra",
            "kind": "linear_system",
            "variables": ["a", "d"],
            "equations": [
                {"coeffs": [1, pp - 1], "const": ap_},
                {"coeffs": [1, q - 1], "const": aq},
            ],
            "model": {"family": self.id, "p": pp, "q": q, "ap": ap_, "aq": aq, "r": r},
        }

        def solve_with(a1: Fraction, d1: Fraction, m: Mapping[str, Any]) -> Any:
            return {
                "values": {"a": fstr(a1), "d": fstr(d1)},
                "value": fstr(a1 + (m["r"] - 1) * d1),
            }

        def closed(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            d1 = F(m["aq"] - m["ap"], m["q"] - m["p"])
            return solve_with(F(m["ap"]) - (m["p"] - 1) * d1, d1, m)

        def enum(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            hits = [
                (F(a1), F(d1))
                for a1 in range(-200, 201)
                for d1 in range(-60, 61)
                if a1 + (m["p"] - 1) * d1 == m["ap"] and a1 + (m["q"] - 1) * d1 == m["aq"]
            ]
            if len(hits) != 1:
                raise ValueError("no unique integer solution")
            return solve_with(hits[0][0], hits[0][1], m)

        def sym(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            a0, d0 = sympy.symbols("a0 d0")
            sol = sympy.solve(
                [a0 + (m["p"] - 1) * d0 - m["ap"], a0 + (m["q"] - 1) * d0 - m["aq"]],
                [a0, d0],
                dict=True,
            )[0]
            return solve_with(
                F(int(sol[a0].p), int(sol[a0].q)), F(int(sol[d0].p), int(sol[d0].q)), m
            )

        return Built(
            spec=spec,
            answer={"values": values, "value": fstr(ar)},
            witness={"values": values},
            stem=pick(
                [
                    f"In an AP the {ordinal(pp)} term is {ap_} and the {ordinal(q)} term is {aq}. "
                    f"Find the {ordinal(r)} term.",
                    f"An AP has {ap_} as its {ordinal(pp)} term and {aq} as its {ordinal(q)} term. "
                    f"What is its {ordinal(r)} term?",
                    f"Two terms of an AP are known: term {pp} is {ap_} and term {q} is {aq}. "
                    f"Work out term {r}.",
                ],
                {"a": a, "d": d, "r": r},
            ),
            steps=[
                f"Going from term {pp} to term {q} takes {gap} equal steps, and the terms change by {aq - ap_}.",
                f"So the common difference is {aq - ap_} / {gap} = {d}.",
                f"Go back to the first term: a = {ap_} - ({pp} - 1)({d}) = {a}.",
                f"Then a_{r} = {a} + ({r} - 1)({d}) = {fstr(ar)}.",
            ],
            hints=[
                pick(
                    [
                        "First find the common difference using the two terms you are given.",
                        "The change between the two given terms is made of several equal steps.",
                        "Use the two given terms to find the first term and the difference before "
                        "anything else.",
                    ],
                    p,
                ),
                "Share the total change between the two terms equally over the number of steps "
                "between them, then work back to the first term.",
                "Full method: divide the change in value by the change in position to get the "
                "difference, use one given term to find the first term, then apply the rule for "
                "the term you are asked for.",
            ],
            wrong=[(mc, {"values": values, "value": fstr(v)}, fstr(v)) for mc, v in wrong],
            key_text=fstr(ar),
            tokens=[fstr(ar)],
            difficulty=clamp_difficulty(0.45, a, d, r, steps=4),
            role="apply",
            prediction="Is the common difference positive or negative?",
            methods=_methods(closed, enum, sym, "nth_term_formula"),
            slug=_slug(a, d, pp, gap, r),
            tags=[f"marks:{tpl['form']['marks']}", "steps:4"],
        )


# ---------------------------------------------------------------- 6/7. sums


def _sum_methods() -> list[FnMethod]:
    def closed(spec: Mapping[str, Any]) -> Any:
        m = spec["model"]
        return _scalar_answer(F(m["n"], 2) * (2 * F(m["a"]) + (m["n"] - 1) * F(m["d"])))

    def enum(spec: Mapping[str, Any]) -> Any:
        m = spec["model"]
        return _scalar_answer(sum(ap_terms(F(m["a"]), F(m["d"]), m["n"]), F(0)))

    def sym(spec: Mapping[str, Any]) -> Any:
        m = spec["model"]
        return _scalar_answer(_sym_sum(F(m["a"]), F(m["d"]), m["n"]))

    return _methods(closed, enum, sym, "sum_formula")


class SumFirstN(Family):
    id = "ap_sum"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        a, d, n = p["a"], p["d"], p["n"]
        if d == 0:
            raise IllPosed("difference_must_be_nonzero")
        s = F(n * (2 * a + (n - 1) * d), 2)
        part, witness, lhs = scalar(s)
        first = [F(a + k * d) for k in range(3)]
        wrong = [
            ("MC.AP.SUM_FORGOT_HALF", F(n * (2 * a + (n - 1) * d))),
            ("MC.AP.SUM_N_FOR_N_MINUS_1", F(n * (2 * a + n * d), 2)),
            ("MC.AP.SUM_NO_DOUBLE_A", F(n * (a + (n - 1) * d), 2)),
            ("MC.AP.SUM_AS_NTH_TERM", F(a + (n - 1) * d)),
        ]
        return Built(
            spec=_spec(lhs, {"family": self.id, "a": a, "d": d, "n": n}),
            answer=part,
            witness=witness,
            stem=pick(
                [
                    f"Find the sum of the first {n} terms of the AP {terms_text(first)}",
                    f"What is the total when the first {n} terms of {terms_text(first)} are added?",
                    f"Add up the first {n} terms of the progression {terms_text(first)}",
                ],
                {"a": a, "d": d, "n": n},
            ),
            steps=[
                f"The first term is {a}, the common difference is {d} and the number of terms is {n}.",
                f"S_n = (n/2)(2a + (n - 1)d) = ({n}/2)(2 x {a} + ({n} - 1) x {d}).",
                f"= ({n}/2)({2 * a + (n - 1) * d}) = {fstr(s)}.",
            ],
            hints=[
                pick(
                    [
                        "You need the first term, the common difference and how many terms are added.",
                        "There is one formula for the sum of the first n terms of an AP.",
                        "Pair the first term with the last, the second with the second last, and so on.",
                    ],
                    p,
                ),
                "Work out twice the first term plus one fewer than n times the difference, then "
                "multiply by n and halve.",
                "Full method: read off the first term and difference, compute twice the first term "
                "plus (n - 1) times the difference, multiply by n, then divide by 2.",
            ],
            wrong=[(mc, _scalar_answer(v), fstr(v)) for mc, v in wrong],
            key_text=fstr(s),
            tokens=[fstr(s)],
            difficulty=clamp_difficulty(0.3, a, d, n, steps=3),
            role="procedure",
            prediction="Roughly how big do you expect the total to be?",
            methods=_sum_methods(),
            slug=_slug(a, d, n),
            tags=[f"marks:{tpl['form']['marks']}", "steps:3"],
        )


class SumWithLast(Family):
    id = "ap_sum_last"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        a, d, n = p["a"], p["d"], p["n"]
        if d == 0:
            raise IllPosed("difference_must_be_nonzero")
        last = a + (n - 1) * d
        s = F(n * (a + last), 2)
        part, witness, lhs = scalar(s)
        first = [F(a + k * d) for k in range(3)]
        wrong = [
            ("MC.AP.SUM_COUNT_FORGOT_PLUS_ONE", F((n - 1) * (a + last), 2)),
            ("MC.AP.SUM_FORGOT_HALF", F(n * (a + last))),
            ("MC.AP.SUM_LAST_TERM_AS_COUNT", F(last * (a + last), 2)),
            ("MC.AP.SUM_FORGOT_COUNT_AND_HALF", F(a + last)),
        ]

        def closed(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            cnt = (F(m["l"]) - F(m["a"])) / F(m["d"]) + 1
            return _scalar_answer(cnt * (F(m["a"]) + F(m["l"])) / 2)

        def enum(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            total, term, last_term, step = F(0), F(m["a"]), F(m["l"]), F(m["d"])
            for _ in range(1000):
                total += term
                if term == last_term:
                    return _scalar_answer(total)
                term += step
                if (step > 0 and term > last_term) or (step < 0 and term < last_term):
                    break
            raise ValueError("the last term is not in the progression")

        def sym(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            k = sympy.Symbol("k", integer=True)
            nn = (sympy.Rational(m["l"]) - sympy.Rational(m["a"])) / sympy.Rational(m["d"]) + 1
            total = sympy.summation(
                sympy.Rational(m["a"]) + k * sympy.Rational(m["d"]), (k, 0, nn - 1)
            )
            return _scalar_answer(F(int(total.p), int(total.q)))

        return Built(
            spec=_spec(lhs, {"family": self.id, "a": a, "d": d, "l": last}),
            answer=part,
            witness=witness,
            stem=pick(
                [
                    f"Find the sum of all the terms of the AP {terms_text(first, False)}, ..., {last}.",
                    f"The AP {terms_text(first, False)}, ..., {last} stops at {last}. What is the sum of all its terms?",
                    f"Add every term of the progression that begins {terms_text(first, False)} and ends at {last}.",
                ],
                {"a": a, "d": d, "n": n},
            ),
            steps=[
                f"The first term is {a}, the last term is {last} and the difference is {d}.",
                f"Number of terms: n = ({last} - {a})/{d} + 1 = {n}.",
                f"S = (n/2)(first + last) = ({n}/2)({a} + {last}) = {fstr(s)}.",
            ],
            hints=[
                pick(
                    [
                        "First find out how many terms there are.",
                        "The count of terms is not given, so work it out from the first and last terms.",
                        "Before you can add, you need the number of terms.",
                    ],
                    p,
                ),
                "The number of terms is the distance from first to last divided by the difference, "
                "plus one. Then average the first and last terms and multiply by the count.",
                "Full method: subtract the first term from the last, divide by the difference, add "
                "one to get n, then multiply n by half of (first + last).",
            ],
            wrong=[(mc, _scalar_answer(v), fstr(v)) for mc, v in wrong],
            key_text=fstr(s),
            tokens=[fstr(s)],
            difficulty=clamp_difficulty(0.4, a, last, steps=4),
            role="apply",
            prediction="Is the number of terms more or less than ten?",
            methods=_methods(closed, enum, sym, "sum_formula"),
            slug=_slug(a, d, n),
            tags=[f"marks:{tpl['form']['marks']}", "steps:3"],
        )


# ---------------------------------------------------------------- 8. n from the sum


class FindNFromSum(Family):
    id = "ap_find_n_sum"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        a, d, n = p["a"], p["d"], p["n"]
        if d == 0:
            raise IllPosed("difference_must_be_nonzero")
        s = F(n * (2 * a + (n - 1) * d), 2)
        n2 = F(d - 2 * a, d) - n  # the other root of d n^2 + (2a - d) n - 2S = 0
        if n2 == n:
            raise IllPosed("double_root")
        if n2 > 0 and n2.denominator == 1:
            raise IllPosed("second_positive_whole_root_makes_the_answer_ambiguous")
        co = [-2 * s, F(2 * a - d), F(d)]
        if any(x.denominator != 1 for x in co):
            raise IllPosed("coefficients_not_whole")
        part, witness = quad_kernel(co[0], co[1], co[2])
        first = [F(a + k * d) for k in range(3)]
        wrong = [
            ("MC.AP.SUMN_OTHER_ROOT_KEPT", n2),
            ("MC.AP.SUMN_OFF_BY_ONE", F(n + 1)),
            ("MC.AP.SUMN_DIVIDED_BY_FIRST_TERM", s / a if a else F(0)),
            ("MC.AP.SUMN_OFF_BY_ONE", F(n - 1)),
        ]
        return Built(
            spec={
                "domain": "algebra",
                "kind": "polynomial",
                "lhs": [fstr(x) for x in co],
                "model": {"family": self.id, "a": a, "d": d, "S": fstr(s)},
            },
            answer={**part, "value": str(n)},
            witness=witness,
            stem=pick(
                [
                    f"How many terms of the AP {terms_text(first)} must be added to make the sum {fstr(s)}?",
                    f"The sum of the first n terms of the AP {terms_text(first)} is {fstr(s)}. Find n.",
                    f"For the progression {terms_text(first)}, how many terms from the start give a total of {fstr(s)}?",
                ],
                {"a": a, "d": d, "n": n},
            ),
            steps=[
                f"Here a = {a}, d = {d} and S_n = {fstr(s)}.",
                f"(n/2)(2 x {a} + (n - 1) x {d}) = {fstr(s)}. Multiply both sides by 2 and expand: "
                f"{d}n{chr(178)} + {2 * a - d}n = {fstr(2 * s)}.",
                f"Rearranged: {d}n{chr(178)} + ({2 * a - d})n - {fstr(2 * s)} = 0, whose solutions are "
                f"n = {n} and n = {fstr(n2)}.",
                f"The number of terms is a positive whole number, so n = {n}.",
            ],
            hints=[
                pick(
                    [
                        "Use the sum formula, but this time the unknown is the number of terms.",
                        "Write the sum formula with n as the unknown and make it equal to the target.",
                        "This leads to quadratic working in n.",
                    ],
                    p,
                ),
                "Multiply each side by 2 to clear the fraction, expand the bracket, and bring "
                "everything to one side so the other side is zero. Then solve for n.",
                "Full method: put the numbers into the sum formula, multiply each side by 2, "
                "expand, rearrange to zero, solve for n, and keep only the positive whole number.",
            ],
            wrong=[(mc, {**part, "value": fstr(v)}, fstr(v)) for mc, v in wrong],
            key_text=str(n),
            tokens=[str(n)],
            difficulty=clamp_difficulty(0.6, a, d, n, steps=5),
            role="transfer",
            prediction="Is n more likely to be small or large?",
            methods=_methods(
                lambda sp: _nsum_answer(sp["model"], _n_from_sum_closed(sp["model"])),
                lambda sp: _nsum_answer(sp["model"], _n_from_sum_scan(sp["model"])),
                lambda sp: _nsum_answer(sp["model"], _n_from_sum_sympy(sp["model"])),
                "sum_formula",
            ),
            slug=_slug(a, d, n),
            tags=[f"marks:{tpl['form']['marks']}", "steps:5"],
        )


def _nsum_answer(m: Mapping[str, Any], n: Fraction) -> dict[str, Any]:
    a, d, s = F(m["a"]), F(m["d"]), F(m["S"])
    part, _ = quad_kernel(-2 * s, 2 * a - d, d)
    return {**part, "value": fstr(n)}


def _n_from_sum_closed(m: Mapping[str, Any]) -> Fraction:
    a, d, s = F(m["a"]), F(m["d"]), F(m["S"])
    from app.factory.kernel.exact import rational_sqrt

    root = rational_sqrt((2 * a - d) ** 2 + 8 * d * s)
    assert root is not None
    roots = {(-(2 * a - d) + root) / (2 * d), (-(2 * a - d) - root) / (2 * d)}
    whole = [r for r in roots if r > 0 and r.denominator == 1]
    if len(whole) != 1:
        raise ValueError("not exactly one positive whole solution")
    return whole[0]


def _n_from_sum_scan(m: Mapping[str, Any]) -> Fraction:
    a, d, s = F(m["a"]), F(m["d"]), F(m["S"])
    hits = []
    total = F(0)
    for n in range(1, 300):
        total += a + (n - 1) * d
        if total == s:
            hits.append(n)
    if len(hits) != 1:
        raise ValueError("not exactly one n")
    return F(hits[0])


def _n_from_sum_sympy(m: Mapping[str, Any]) -> Fraction:
    n = sympy.Symbol("n", integer=True, positive=True)
    k = sympy.Symbol("k", integer=True)
    total = sympy.summation(sympy.Rational(m["a"]) + k * sympy.Rational(m["d"]), (k, 0, n - 1))
    sol = sympy.solve(sympy.Eq(total, sympy.Rational(m["S"])), n)
    if len(sol) != 1:
        raise ValueError("not exactly one n")
    return F(int(sol[0].p), int(sol[0].q))


# ---------------------------------------------------------------- 9. term from the sum formula


class TermFromSum(Family):
    id = "ap_term_from_sum"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        big_a, big_b, k, ask = p["A"], p["B"], p["k"], p["ask"]
        if ask == "d" and k != tpl["box"]["k"]["choices"][0]:
            raise IllPosed("position_only_matters_for_the_kth_term_question")

        def s(n: int) -> int:
            return big_a * n * n + big_b * n

        if ask == "kth":
            val = big_a * (2 * k - 1) + big_b
            wrong = [
                ("MC.AP.TERM_IS_SUM", s(k)),
                ("MC.AP.TERM_FROM_SUM_AVERAGE", F(s(k), k)),
                ("MC.AP.TERM_FROM_SUM_WRONG_INDEX", s(k) - s(k - 2)),
                ("MC.AP.TERM_FROM_SUM_NEXT_SUM", s(k + 1) - s(k - 1)),
            ]
            question = f"Find the {ordinal(k)} term."
        else:
            val = 2 * big_a
            wrong = [
                ("MC.AP.D_FROM_SUM_COEFF_NOT_DOUBLED", big_a),
                ("MC.AP.D_FROM_SUM_FIRST_TERM", big_a + big_b),
                ("MC.AP.D_FROM_SUM_SECOND_TERM", 3 * big_a + big_b),
                ("MC.AP.D_FROM_SUM_LINEAR_COEFF", big_b),
            ]
            question = "Find the common difference."
        part, witness, lhs = scalar(F(val))
        expr = (
            f"{big_a}n{chr(178)} {'+' if big_b >= 0 else '-'} {abs(big_b)}n"
            if big_b
            else f"{big_a}n{chr(178)}"
        )

        def closed(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            if m["ask"] == "kth":
                return _scalar_answer(F(m["A"] * (2 * m["k"] - 1) + m["B"]))
            return _scalar_answer(F(2 * m["A"]))

        def enum(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]

            def sn(n: int) -> int:
                return m["A"] * n * n + m["B"] * n

            if m["ask"] == "kth":
                return _scalar_answer(F(sn(m["k"]) - sn(m["k"] - 1)))
            return _scalar_answer(F((sn(3) - sn(2)) - (sn(2) - sn(1))))

        def sym(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            n = sympy.Symbol("n")
            sn = m["A"] * n**2 + m["B"] * n
            term = sympy.expand(sn - sn.subs(n, n - 1))
            if m["ask"] == "kth":
                return _scalar_answer(F(int(term.subs(n, m["k"]))))
            return _scalar_answer(F(int(sympy.expand(term.subs(n, n + 1) - term))))

        return Built(
            spec=_spec(lhs, {"family": self.id, "A": big_a, "B": big_b, "k": k, "ask": ask}),
            answer=part,
            witness=witness,
            stem=f"The sum of the first n terms of an AP is S_n = {expr}. {question}",
            steps=[
                "The nth term is the difference of two sums: a_n = S_n - S_(n-1).",
                f"S_n - S_(n-1) = {expr} - ({big_a}(n - 1){chr(178)} {'+' if big_b >= 0 else '-'} {abs(big_b)}(n - 1)) "
                f"= {2 * big_a}n {'+' if big_b - big_a >= 0 else '-'} {abs(big_b - big_a)}.",
                (
                    f"Put n = {k}: a_{k} = {fstr(F(val))}."
                    if ask == "kth"
                    else f"The coefficient of n is {2 * big_a}, so the common difference is {2 * big_a}."
                ),
            ],
            hints=[
                pick(
                    [
                        "A single term is the difference between two consecutive sums.",
                        "The sum up to one term and the sum up to the term before it differ by exactly that term.",
                        "Think about what is left when you remove the earlier sum from the later sum.",
                    ],
                    p,
                ),
                "Write the sum with n replaced by n minus one, subtract it from the original sum, "
                "and simplify the result.",
                "Full method: find S_n minus S_(n-1) in terms of n, simplify to get the rule for "
                "the nth term, then substitute the position you need or read off the difference.",
            ],
            wrong=[(mc, _scalar_answer(F(v)), fstr(F(v))) for mc, v in wrong],  # type: ignore[call-overload]
            key_text=fstr(F(val)),
            tokens=[fstr(F(val))],
            difficulty=clamp_difficulty(0.55, big_a, big_b, k, steps=4),
            role="apply",
            prediction="Will the term be larger or smaller than the sum for the same n?",
            methods=_methods(closed, enum, sym, "sum_formula"),
            slug=_slug(big_a, big_b, k, ask),
            tags=[f"marks:{tpl['form']['marks']}", "steps:4"],
        )


# ---------------------------------------------------------------- 10. situations


CONTEXTS = {
    0: ("In a hall the first row has {a} seats and every row after it has {d} more seats than "
        "the row before. There are {n} rows.",
        "How many seats are in the last row?", "How many seats are there in the whole hall?"),
    1: ("A runner trains for {n} weeks. In week 1 she runs {a} km and each week she runs {d} km "
        "more than the week before.",
        "How far does she run in the last week, in km?",
        "How far does she run in all the weeks together, in km?"),
    2: ("A library puts books on display. On day 1 it shows {a} books and each day it shows {d} "
        "more than the day before, for {n} days.",
        "How many books are on display on the last day?",
        "How many books are shown over all the days together?"),
    3: ("Pipes are stacked in rows. The bottom row has {a} pipes and every row above it has {d} "
        "fewer pipes than the row below. There are {n} rows.",
        "How many pipes are in the top row?", "How many pipes are in the whole stack?"),
}  # fmt: skip


class WordSituation(Family):
    id = "ap_word"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        ctx, a, d, n, ask = p["ctx"], p["a"], p["d"], p["n"], p["ask"]
        story, q_last, q_total = CONTEXTS[ctx]
        step = -d if ctx == 3 else d
        if ctx == 3 and a - (n - 1) * d < 1:
            raise IllPosed("stack_would_have_no_pipes_at_the_top")
        if ctx != 3 and a < 3:
            raise IllPosed("start_too_small_for_the_story")
        last = a + (n - 1) * step
        s = F(n * (a + last), 2)
        part, witness, lhs = scalar(F(last) if ask == "last" else s)
        if ask == "last":
            val = F(last)
            wrong = [
                ("MC.AP.NTH_N_FOR_N_MINUS_1", F(a + n * step)),
                ("MC.AP.NTH_OFF_BY_ONE_LOW", F(a + (n - 2) * step)),
                ("MC.AP.NTH_D_ADDED_NOT_MULTIPLIED", F(a + (n - 1) + step)),
                ("MC.AP.WORD_TOTAL_REPORTED", s),
            ]
            question = q_last
        else:
            val = s
            wrong = [
                ("MC.AP.SUM_FORGOT_HALF", F(n * (a + last))),
                ("MC.AP.WORD_LAST_REPORTED", F(last)),
                ("MC.AP.SUM_N_FOR_N_MINUS_1", F(n * (2 * a + n * step), 2)),
                ("MC.AP.SUM_NO_DOUBLE_A", F(n * (a + (n - 1) * step), 2)),
            ]
            question = q_total
        stem = story.format(a=a, d=d, n=n) + " " + question

        def closed(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            aa, dd, nn = F(m["a"]), F(m["step"]), m["n"]
            return _scalar_answer(
                aa + (nn - 1) * dd if m["ask"] == "last" else F(nn, 2) * (2 * aa + (nn - 1) * dd)
            )

        def enum(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            rows = ap_terms(F(m["a"]), F(m["step"]), m["n"])
            return _scalar_answer(rows[-1] if m["ask"] == "last" else sum(rows, F(0)))

        def sym(spec: Mapping[str, Any]) -> Any:
            m = spec["model"]
            aa, dd, nn = F(m["a"]), F(m["step"]), m["n"]
            return _scalar_answer(
                _sym_nth(aa, dd, nn) if m["ask"] == "last" else _sym_sum(aa, dd, nn)
            )

        return Built(
            spec=_spec(lhs, {"family": self.id, "a": a, "step": step, "n": n, "ask": ask}),
            answer=part,
            witness=witness,
            stem=stem,
            steps=[
                f"The amounts form an AP with first term {a} and common difference {step}.",
                *(
                    [f"The last amount is a_{n} = {a} + ({n} - 1)({step}) = {last}."]
                    if ask == "last"
                    else [
                        f"The last amount is {last}, so the total is S = ({n}/2)({a} + {last}).",
                        f"S = {fstr(s)}.",
                    ]
                ),
            ],
            hints=[
                pick(
                    [
                        "Let the amounts in order be the terms of an AP: name its first term and its "
                        "common difference.",
                        "Write the amounts as one list and look at what changes from one step to the next.",
                        "The same change repeats at every step, so the amounts form an AP: find its "
                        "first term and its difference.",
                    ],
                    p,
                ),
                "Decide whether the question asks for one term or for the sum of all the terms, "
                "then choose the matching rule. Work through it one operation after another.",
                "Full method: identify the first term, the common difference and the number of "
                "rows or days, pick the rule for one term or for the sum, substitute carefully, "
                "and give the answer with its unit.",
            ],
            wrong=[(mc, _scalar_answer(v), fstr(v)) for mc, v in wrong],
            key_text=fstr(val),
            tokens=[fstr(val)],
            difficulty=clamp_difficulty(0.35 if ask == "last" else 0.55, a, d, n, steps=4),
            role="apply" if ask == "last" else "transfer",
            prediction="Is the pattern growing or shrinking from one step to the next?",
            methods=_methods(
                closed, enum, sym, "nth_term_formula" if ask == "last" else "sum_formula"
            ),
            slug=_slug(ctx, a, d, n, ask),
            tags=[f"marks:{tpl['form']['marks']}", "steps:4"],
        )


# ---------------------------------------------------------------- 11. sum of multiples


class SumOfMultiples(Family):
    id = "ap_multiples"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        m, i, cnt, e1, e2 = p["m"], p["i"], p["cnt"], p["e1"], p["e2"]
        if e1 >= m or e2 >= m:
            raise IllPosed("end_offsets_must_be_smaller_than_the_multiple")
        j = i + cnt - 1
        low, high = m * i - e1, m * j + e2
        if low < 1:
            raise IllPosed("range_must_start_at_a_positive_number")
        s = F(m * (i + j) * cnt, 2)
        part, witness, lhs = scalar(s)
        wrong = [
            ("MC.AP.COUNT_FORGOT_PLUS_ONE", F(m * (i + j) * (cnt - 1), 2)),
            ("MC.AP.ENDPOINTS_USED_NOT_MULTIPLES", F((low + high) * cnt, 2)),
            ("MC.AP.SUM_FORGOT_HALF", F(m * (i + j) * cnt)),
            ("MC.AP.MULTIPLES_STARTED_FROM_FIRST", F(m * j * (j + 1), 2)),
        ]

        def closed(spec: Mapping[str, Any]) -> Any:
            md = spec["model"]
            first = -(-md["low"] // md["m"])  # ceiling
            last = md["high"] // md["m"]
            n_terms = last - first + 1
            return _scalar_answer(F(md["m"] * (first + last) * n_terms, 2))

        def enum(spec: Mapping[str, Any]) -> Any:
            md = spec["model"]
            return _scalar_answer(
                F(sum(x for x in range(md["low"], md["high"] + 1) if x % md["m"] == 0))
            )

        def sym(spec: Mapping[str, Any]) -> Any:
            md = spec["model"]
            k = sympy.Symbol("k", integer=True)
            first = sympy.ceiling(sympy.Rational(md["low"], md["m"]))
            last = sympy.floor(sympy.Rational(md["high"], md["m"]))
            total = sympy.summation(md["m"] * k, (k, first, last))
            return _scalar_answer(F(int(total)))

        return Built(
            spec=_spec(lhs, {"family": self.id, "m": m, "low": low, "high": high}),
            answer=part,
            witness=witness,
            stem=pick(
                [
                    f"Find the sum of all the multiples of {m} from {low} to {high}, both included.",
                    f"What is the sum of the multiples of {m} that lie between {low} and {high}, ends included?",
                    f"Add every multiple of {m} from {low} up to {high}, counting both ends if they qualify.",
                ],
                {"m": m, "i": i, "c": cnt},
            ),
            steps=[
                f"The first multiple of {m} in the range is {m * i} and the last is {m * j}.",
                f"They form an AP with common difference {m}. Number of terms: ({m * j} - {m * i})/{m} + 1 = {cnt}.",
                f"S = ({cnt}/2)({m * i} + {m * j}) = {fstr(s)}.",
            ],
            hints=[
                pick(
                    [
                        "The multiples form an AP: find the first and last ones inside the range.",
                        "The end numbers of the range may not themselves be multiples.",
                        "List the first multiple inside the range and the last multiple inside it.",
                    ],
                    p,
                ),
                "Work out how many multiples lie between the first and last, remembering to add "
                "one to the count, then use the sum rule with the first and last multiples.",
                "Full method: find the first and last multiples inside the range, count them "
                "using the difference between multiples, then multiply the count by half the sum "
                "of the first and last multiples.",
            ],
            wrong=[(mc, _scalar_answer(v), fstr(v)) for mc, v in wrong],
            key_text=fstr(s),
            tokens=[fstr(s)],
            difficulty=clamp_difficulty(0.5, m, cnt, steps=4),
            role="apply",
            prediction="About how many multiples do you expect in the range?",
            methods=_methods(closed, enum, sym, "sum_formula"),
            slug=_slug(m, i, cnt, e1, e2),
            tags=[f"marks:{tpl['form']['marks']}", "steps:4"],
        )


AP_FAMILIES: dict[str, Family] = {
    f.id: f
    for f in (
        CommonDifference(), IdentifyAP(), NthTerm(), WhichTerm(), TwoTerms(), SumFirstN(),
        SumWithLast(), FindNFromSum(), TermFromSum(), WordSituation(), SumOfMultiples(),
    )
}  # fmt: skip
