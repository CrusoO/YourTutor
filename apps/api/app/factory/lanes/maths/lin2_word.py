# ruff: noqa: E501
"""Pair of Linear Equations: word problems and equations that reduce to a pair of linear equations.

A word family keeps the story as structured numbers. Three methods read only that model:
the coefficient rows solved in closed form, the story relations solved symbolically by SymPy, and the
story relations scanned over a grid of simple rationals. The kernel certifies the coefficient rows.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from fractions import Fraction
from typing import Any

import sympy

from app.factory.lanes.maths.core import Built, Family, IllPosed, clamp_difficulty, fstr, pick
from app.factory.lanes.maths.lin2_core import F, coef_text, make, method, nice, pair_rec, slug, system_spec
from app.factory.lanes.maths.reference import lin2 as ref

Fmt = Callable[[Mapping[str, Any], Fraction, Fraction], tuple[dict[str, Any], str]]


def _safe(fn: Callable[[], Any]) -> Any:
    try:
        return fn()
    except (ZeroDivisionError, ValueError):
        return None


def plural(word: str, n: int) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


class WordFamily(Family):
    """Hooks: model, rows_of, story, fmt, wrongs, stem, steps, hints."""

    base = 0.4
    role = "apply"
    prediction = "Roughly what size should the answer be?"

    def model(self, p: Mapping[str, Any]) -> dict[str, Any]:  # pragma: no cover
        raise NotImplementedError

    def solution(self, p: Mapping[str, Any]) -> tuple[Fraction, Fraction]:  # pragma: no cover
        raise NotImplementedError

    def rows_of(self, m: Mapping[str, Any]) -> list[list[int]]:  # pragma: no cover
        raise NotImplementedError

    def story(self, m: Mapping[str, Any], x: Any, y: Any) -> list[Any]:  # pragma: no cover
        raise NotImplementedError

    def fmt(self, m: Mapping[str, Any], x: Fraction, y: Fraction) -> tuple[dict[str, Any], str]:  # pragma: no cover
        raise NotImplementedError

    def wrongs(self, m: Mapping[str, Any], x: Fraction, y: Fraction) -> list[tuple[str, Any]]:  # pragma: no cover
        """(misconception id, (x', y') or a ready (record, text))."""
        raise NotImplementedError

    def stem(self, m: Mapping[str, Any], p: Mapping[str, Any]) -> str:  # pragma: no cover
        raise NotImplementedError

    def steps(self, m: Mapping[str, Any], x: Fraction, y: Fraction) -> list[str]:  # pragma: no cover
        raise NotImplementedError

    def hints(self, p: Mapping[str, Any]) -> list[str]:  # pragma: no cover
        raise NotImplementedError

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        m = self.model(p)
        x, y = self.solution(p)
        rows = self.rows_of(m)
        spec = system_spec(rows, m)
        key, key_text = self.fmt(m, x, y)
        wrong: list[tuple[str, dict[str, Any], str]] = []
        for mc, val in self.wrongs(m, x, y):
            if val is None:
                continue
            if isinstance(val[0], dict):
                rec, text = val
            else:
                if not (nice(val[0]) and nice(val[1])):
                    continue
                rec, text = self.fmt(m, val[0], val[1])
            wrong.append((mc, rec, text))
        fam = self

        def closed(s: Mapping[str, Any]) -> Any:
            return fam.fmt(s["model"], *ref.cramer(ref.eqs(fam.rows_of(s["model"]))))[0]

        def by_sympy(s: Mapping[str, Any]) -> Any:
            xs, ys = sympy.symbols("xs ys")
            sol = sympy.linsolve(fam.story(s["model"], xs, ys), (xs, ys))
            if len(sol) != 1:
                raise ValueError("no unique solution")
            xv, yv = next(iter(sol))
            return fam.fmt(s["model"], ref._rat(xv), ref._rat(yv))[0]

        def scan(s: Mapping[str, Any]) -> Any:
            mm = s["model"]

            def resid(xv: Fraction, yv: Fraction) -> list[Fraction]:
                return [F(r) for r in fam.story(mm, xv, yv)]

            for row in (0, 1):
                try:
                    return fam.fmt(mm, *ref.scan(resid, ref.linear_y(resid, row)))[0]
                except ValueError:
                    continue
            raise ValueError("no grid solution")

        methods = [
            method("maths.lin2.word_rows", "closed_form", "model_as_pair", closed),
            method("maths.lin2.word_sympy", "sympy.linsolve", "", by_sympy),
            method("maths.lin2.word_grid", "grid_search", "", scan),
        ]
        steps = self.steps(m, x, y)
        return make(
            tpl,
            spec=spec,
            key=key,
            witness={"values": key["values"]},
            key_text=key_text,
            wrong=wrong,
            stem=self.stem(m, p),
            steps=steps,
            hints=self.hints(p),
            methods=methods,
            difficulty=clamp_difficulty(self.base, x, y, steps=len(steps)),
            role=self.role,
            prediction=self.prediction,
            slug_text=slug(*p.values()),
            nsteps=len(steps),
        )


def _hint_set(p: Mapping[str, Any], pool: list[str], second: str, third: str) -> list[str]:
    return [pick(pool, p), second, third]


# ---------------------------------------------------------------- ages

_PAIRS = [("Asha", "Bilal"), ("Charu", "Dev"), ("Esha", "Farid"), ("Gita", "Hari")]


class WordAges(WordFamily):
    id = "lin_word_ages"
    base = 0.45

    def model(self, p: Mapping[str, Any]) -> dict[str, Any]:
        y, k, t, when, ask, who = p["y"], p["k"], p["t"], p["when"], p["ask"], p["who"]
        if when == "ago" and y <= t:
            raise IllPosed("younger_not_born_yet")
        x = k * (y + t) - t if when == "later" else k * (y - t) + t
        if x <= y:
            raise IllPosed("older_must_be_older")
        return {"family": self.id, "S": x + y, "k": k, "t": t, "when": when, "ask": ask, "who": who}

    def solution(self, p: Mapping[str, Any]) -> tuple[Fraction, Fraction]:
        y, k, t = p["y"], p["k"], p["t"]
        return F(k * (y + t) - t if p["when"] == "later" else k * (y - t) + t), F(y)

    def rows_of(self, m: Mapping[str, Any]) -> list[list[int]]:
        k, t = m["k"], m["t"]
        return [[1, 1, m["S"]], [1, -k, (k - 1) * t if m["when"] == "later" else -(k - 1) * t]]

    def story(self, m: Mapping[str, Any], x: Any, y: Any) -> list[Any]:
        k, t = m["k"], m["t"]
        s = 1 if m["when"] == "later" else -1
        return [x + y - m["S"], (x + s * t) - k * (y + s * t)]

    def fmt(self, m: Mapping[str, Any], x: Fraction, y: Fraction) -> tuple[dict[str, Any], str]:
        v = x if m["ask"] == "A" else y
        text = f"{fstr(v)} years"
        return pair_rec(x, y, text), text

    def wrongs(self, m: Mapping[str, Any], x: Fraction, y: Fraction) -> list[tuple[str, Any]]:
        k, t, S = m["k"], m["t"], m["S"]
        s = 1 if m["when"] == "later" else -1
        mine, other = (x, y) if m["ask"] == "A" else (y, x)
        wrong_time = _safe(lambda: ref.cramer(ref.eqs([[1, 1, S], [1, -k, -(k - 1) * s * t]])))
        flipped = _safe(lambda: ref.cramer(ref.eqs([[1, 1, S], [-k, 1, (k - 1) * s * t]])))
        return [
            ("MC.PAIR.WORD_ASKED_OTHER_UNKNOWN", (y, x)),
            ("MC.PAIR.WORD_AGES_FUTURE_REPORTED", (mine + s * t, other) if m["ask"] == "A" else (other, mine + s * t)),
            ("MC.PAIR.WORD_AGES_SIGN_OF_TIME", wrong_time),
            ("MC.PAIR.WORD_AGES_RATIO_FLIPPED", flipped),
        ]

    def stem(self, m: Mapping[str, Any], p: Mapping[str, Any]) -> str:
        a, b = _PAIRS[m["who"]]
        who = a if m["ask"] == "A" else b
        t, k = m["t"], m["k"]
        if m["when"] == "later":
            link = pick(
                [f"{plural('year', t)} from now, {a}'s age will be {k} times {b}'s age.", f"After {plural('year', t)}, {a} will be exactly {k} times as old as {b}."],
                m,
            )
        else:
            link = pick(
                [f"{plural('year', t)} ago, {a}'s age was {k} times {b}'s age.", f"Before {plural('year', t)} passed, {a} was exactly {k} times as old as {b}."],
                m,
            )
        return f"The sum of the present ages of {a} and {b} is {m['S']} years. {link} Find the present age of {who}."

    def steps(self, m: Mapping[str, Any], x: Fraction, y: Fraction) -> list[str]:
        a, b = _PAIRS[m["who"]]
        k, t = m["k"], m["t"]
        later = m["when"] == "later"
        link = f"x + {t} = {k}(y + {t})" if later else f"x - {t} = {k}(y - {t})"
        return [
            f"Let {a}'s present age be x years and {b}'s be y years. Then x + y = {m['S']}.",
            f"{'Later' if later else 'Earlier'}: {link}, which gives {ref_text(self.rows_of(m)[1])}.",
            f"Solving the pair gives x = {fstr(x)} and y = {fstr(y)}.",
        ]

    def hints(self, p: Mapping[str, Any]) -> list[str]:
        return _hint_set(
            p,
            [
                "Give each person's present age its own letter before anything else.",
                "Turn each sentence of the problem into one relation between the two ages.",
                "Decide what x and y stand for, then write what each sentence says about them.",
                "Name the two unknown ages first.",
            ],
            "One sentence is about the ages now. The other concerns the ages at another time, so move each age by the stated years before comparing.",
            "Full method: name the ages, write the two relations, solve the pair, and check both sentences with your answer.",
        )


def ref_text(row: list[int]) -> str:
    a, b, c = row
    out = coef_text(a, "x", True) + coef_text(b, "y", False)
    return f"{out} = {c}"


# ---------------------------------------------------------------- fractions


class WordFraction(WordFamily):
    id = "lin_word_fraction"
    base = 0.5

    def model(self, p: Mapping[str, Any]) -> dict[str, Any]:
        n, d, u, w = p["n"], p["d"], p["u"], p["w"]
        if math.gcd(n, d) != 1 or d + w <= 0 or n + u <= 0 or w == 0:
            raise IllPosed("fraction_or_change_unusable")
        g = math.gcd(n + u, d + w)
        pp, qq = (n + u) // g, (d + w) // g
        if pp == qq:
            raise IllPosed("new_fraction_is_one")
        return {"family": self.id, "u": u, "w": w, "S": n + d, "p": pp, "q": qq}

    def solution(self, p: Mapping[str, Any]) -> tuple[Fraction, Fraction]:
        return F(p["n"]), F(p["d"])

    def rows_of(self, m: Mapping[str, Any]) -> list[list[int]]:
        return [[1, 1, m["S"]], [m["q"], -m["p"], m["p"] * m["w"] - m["q"] * m["u"]]]

    def story(self, m: Mapping[str, Any], x: Any, y: Any) -> list[Any]:
        return [x + y - m["S"], m["q"] * (x + m["u"]) - m["p"] * (y + m["w"])]

    def fmt(self, m: Mapping[str, Any], x: Fraction, y: Fraction) -> tuple[dict[str, Any], str]:
        text = f"{fstr(x)}/{fstr(y)}"
        return pair_rec(x, y, text), text

    def wrongs(self, m: Mapping[str, Any], x: Fraction, y: Fraction) -> list[tuple[str, Any]]:
        p, q, u, w, S = m["p"], m["q"], m["u"], m["w"], m["S"]
        misplaced = _safe(lambda: ref.cramer(ref.eqs([[1, 1, S], [q, -p, p * u - q * w]])))
        return [
            ("MC.PAIR.WORD_FRACTION_ROLES_SWAPPED", (y, x)),
            ("MC.PAIR.WORD_FRACTION_REPORTED_NEW", (F(p), F(q))),
            ("MC.PAIR.WORD_FRACTION_CHANGE_MISPLACED", misplaced),
            ("MC.PAIR.WORD_FRACTION_CHANGE_MISPLACED", (x, y + w)),
        ]

    def stem(self, m: Mapping[str, Any], p: Mapping[str, Any]) -> str:
        u, w = m["u"], m["w"]
        den = f"increased by {w}" if w > 0 else f"decreased by {-w}"
        num = f"increased by {u}" if u > 0 else f"decreased by {-u}"
        return pick(
            [
                f"The numerator and denominator of a fraction in its lowest terms add up to {m['S']}. When its numerator is {num} and its denominator is {den}, the fraction becomes {m['p']}/{m['q']}. What is the original fraction?",
                f"A fraction in lowest terms has numerator plus denominator equal to {m['S']}. If the numerator is {num} and the denominator is {den}, the new fraction is {m['p']}/{m['q']}. Find the original fraction.",
            ],
            m,
        )

    def steps(self, m: Mapping[str, Any], x: Fraction, y: Fraction) -> list[str]:
        return [
            f"Let the fraction be x/y. Then x + y = {m['S']}.",
            f"After the change the fraction is (x + {m['u']})/(y + {m['w']}) = {m['p']}/{m['q']}, so {ref_text(self.rows_of(m)[1])}.",
            f"Solving the pair gives x = {fstr(x)} and y = {fstr(y)}, so the fraction is {fstr(x)}/{fstr(y)}.",
        ]

    def hints(self, p: Mapping[str, Any]) -> list[str]:
        return _hint_set(
            p,
            [
                "Let the numerator be x and the denominator be y.",
                "Write what the sum of the two parts tells you about x and y.",
                "Name the numerator and denominator, then turn each sentence into one relation.",
                "Start with one letter for the top of the fraction and one for the bottom.",
            ],
            "The new fraction equals the stated value, so multiply out the two sides to remove the fractions before solving.",
            "Full method: name the numerator and denominator, write the sum relation, write the relation for the new fraction without fractions, solve the pair, then state the fraction.",
        )


# ---------------------------------------------------------------- boat in a stream

_BOATS = ["boat", "launch", "motorboat"]


class WordStream(WordFamily):
    id = "lin_word_stream"
    base = 0.5

    def model(self, p: Mapping[str, Any]) -> dict[str, Any]:
        x, y, t1, t2, ask, ctx = p["x"], p["y"], p["t1"], p["t2"], p["ask"], p["ctx"]
        if y >= x:
            raise IllPosed("stream_not_slower_than_boat")
        return {"family": self.id, "t1": t1, "t2": t2, "D1": (x - y) * t1, "D2": (x + y) * t2, "ask": ask, "ctx": ctx}

    def solution(self, p: Mapping[str, Any]) -> tuple[Fraction, Fraction]:
        return F(p["x"]), F(p["y"])

    def rows_of(self, m: Mapping[str, Any]) -> list[list[int]]:
        return [[m["t1"], -m["t1"], m["D1"]], [m["t2"], m["t2"], m["D2"]]]

    def story(self, m: Mapping[str, Any], x: Any, y: Any) -> list[Any]:
        return [m["t1"] * (x - y) - m["D1"], m["t2"] * (x + y) - m["D2"]]

    def fmt(self, m: Mapping[str, Any], x: Fraction, y: Fraction) -> tuple[dict[str, Any], str]:
        text = f"{fstr(x if m['ask'] == 'boat' else y)} km/h"
        return pair_rec(x, y, text), text

    def wrongs(self, m: Mapping[str, Any], x: Fraction, y: Fraction) -> list[tuple[str, Any]]:
        t1, t2, D1, D2 = m["t1"], m["t2"], m["D1"], m["D2"]
        reversed_ = _safe(lambda: ref.cramer(ref.eqs([[t1, t1, D1], [t2, -t2, D2]])))
        up, down = F(D1, t1), F(D2, t2)
        double = (up + down, y) if m["ask"] == "boat" else (x, down - up)
        avg = F(D1 + D2, t1 + t2)
        return [
            ("MC.PAIR.WORD_STREAM_REVERSED", reversed_),
            ("MC.PAIR.WORD_ASKED_OTHER_UNKNOWN", (y, x)),
            ("MC.PAIR.WORD_STREAM_NOT_HALVED", double),
            ("MC.PAIR.WORD_STREAM_AVERAGE", (avg, y) if m["ask"] == "boat" else (x, avg)),
        ]

    def stem(self, m: Mapping[str, Any], p: Mapping[str, Any]) -> str:
        boat = _BOATS[m["ctx"]]
        goal = f"the speed of the {boat} in still water" if m["ask"] == "boat" else "the speed of the stream"
        return pick(
            [
                f"A {boat} goes {m['D1']} km upstream in {plural('hour', m['t1'])} and {m['D2']} km downstream in {plural('hour', m['t2'])}. Find {goal}.",
                f"On a river, a {boat} covers {m['D1']} km against the current in {plural('hour', m['t1'])} and {m['D2']} km with the current in {plural('hour', m['t2'])}. What is {goal}?",
            ],
            m,
        )

    def steps(self, m: Mapping[str, Any], x: Fraction, y: Fraction) -> list[str]:
        t1, t2, D1, D2 = m["t1"], m["t2"], m["D1"], m["D2"]
        return [
            f"Let the still-water speed be x km/h and the stream speed y km/h. Upstream the speed is x - y, downstream it is x + y.",
            f"Distance = speed × time gives {ref_text(self.rows_of(m)[0])} and {ref_text(self.rows_of(m)[1])}.",
            f"Dividing out the hours: x - y = {fstr(F(D1, t1))} and x + y = {fstr(F(D2, t2))}, so x = {fstr(x)} and y = {fstr(y)}.",
        ]

    def hints(self, p: Mapping[str, Any]) -> list[str]:
        return _hint_set(
            p,
            [
                "Upstream the stream works against the boat and downstream it works with the boat.",
                "Give the still-water speed one letter and the stream speed another.",
                "The speed over the ground is different upstream and downstream. Write each one.",
                "Think about what the stream does to the speed on each trip.",
            ],
            "Distance equals speed times time on each trip. That gives one relation for the upstream trip and one for the downstream trip.",
            "Full method: name the two speeds, write the upstream and downstream speeds, use distance = speed × time twice, solve the pair, and answer the quantity asked.",
        )


# ---------------------------------------------------------------- cost of items

_ITEMS = [("pen", "notebook"), ("cup", "plate"), ("ruler", "pencil case")]


class WordCost(WordFamily):
    id = "lin_word_cost"
    base = 0.4

    def model(self, p: Mapping[str, Any]) -> dict[str, Any]:
        x, y, cnt, ask, ctx = p["x"], p["y"], p["cnt"], p["ask"], p["ctx"]
        pn, qn, rn, sn = (int(ch) for ch in str(cnt))
        if pn * sn - qn * rn == 0:
            raise IllPosed("pair_has_no_unique_solution")
        return {"family": self.id, "c": [pn, qn, rn, sn], "R": pn * x + qn * y, "T": rn * x + sn * y, "ask": ask, "ctx": ctx}

    def solution(self, p: Mapping[str, Any]) -> tuple[Fraction, Fraction]:
        return F(p["x"]), F(p["y"])

    def rows_of(self, m: Mapping[str, Any]) -> list[list[int]]:
        pn, qn, rn, sn = m["c"]
        return [[pn, qn, m["R"]], [rn, sn, m["T"]]]

    def story(self, m: Mapping[str, Any], x: Any, y: Any) -> list[Any]:
        pn, qn, rn, sn = m["c"]
        return [pn * x + qn * y - m["R"], rn * x + sn * y - m["T"]]

    def fmt(self, m: Mapping[str, Any], x: Fraction, y: Fraction) -> tuple[dict[str, Any], str]:
        v = {"item1": x, "item2": y, "both": x + y}[m["ask"]]
        text = f"{fstr(v)} rupees"
        return pair_rec(x, y, text), text

    def wrongs(self, m: Mapping[str, Any], x: Fraction, y: Fraction) -> list[tuple[str, Any]]:
        pn, qn, rn, sn = m["c"]
        R, T = m["R"], m["T"]
        swapped = _safe(lambda: ref.cramer(ref.eqs([[qn, pn, R], [rn, sn, T]])))
        avg = F(R + T, pn + qn + rn + sn)
        avg1 = F(R, pn + qn)
        both = m["ask"] == "both"
        return [
            ("MC.PAIR.WORD_COST_COUNTS_SWAPPED", swapped),
            ("MC.PAIR.WORD_ASKED_OTHER_UNKNOWN", (x, F(0)) if both else (y, x)),
            ("MC.PAIR.WORD_COST_AVERAGE", (avg, F(0)) if both else (avg, avg)),
            ("MC.PAIR.WORD_COST_AVERAGE", (avg1, F(0)) if both else (avg1, avg1)),
            ("MC.PAIR.WORD_ASKED_OTHER_UNKNOWN", (y, F(0)) if both else (y, y)),
        ]

    def stem(self, m: Mapping[str, Any], p: Mapping[str, Any]) -> str:
        a, b = _ITEMS[m["ctx"]]
        pn, qn, rn, sn = m["c"]
        goal = {"item1": f"one {a}", "item2": f"one {b}", "both": f"one {a} and one {b} together"}[m["ask"]]
        return pick(
            [
                f"{plural(a, pn)} and {plural(b, qn)} cost {m['R']} rupees. {plural(a, rn)} and {plural(b, sn)} cost {m['T']} rupees. Find the cost of {goal}.",
                f"A shop sells {plural(a, pn)} with {plural(b, qn)} for {m['R']} rupees, and {plural(a, rn)} with {plural(b, sn)} for {m['T']} rupees. What is the cost of {goal}?",
            ],
            m,
        )

    def steps(self, m: Mapping[str, Any], x: Fraction, y: Fraction) -> list[str]:
        a, b = _ITEMS[m["ctx"]]
        rows = self.rows_of(m)
        return [
            f"Let one {a} cost x rupees and one {b} cost y rupees.",
            f"The two bills give {ref_text(rows[0])} and {ref_text(rows[1])}.",
            f"Solving the pair gives x = {fstr(x)} and y = {fstr(y)}.",
        ]

    def hints(self, p: Mapping[str, Any]) -> list[str]:
        return _hint_set(
            p,
            [
                "Give the price of one of each item its own letter.",
                "Each bill is the total of the count of each item times its price.",
                "Decide what x and y stand for before writing any relation.",
                "Write what each shop bill says about the two prices.",
            ],
            "Multiply each count by the price of the same item, add the two amounts, and set that equal to the bill.",
            "Full method: name the two prices, write one relation for each bill, solve the pair, then give the quantity the question asks for.",
        )


# ---------------------------------------------------------------- rectangle

_SHAPES = ["garden", "poster", "field"]


class WordRect(WordFamily):
    id = "lin_word_rect"
    base = 0.45

    def model(self, p: Mapping[str, Any]) -> dict[str, Any]:
        w, k, e, ask, ctx = p["w"], p["k"], p["e"], p["ask"], p["ctx"]
        length = k * w + e
        return {"family": self.id, "k": k, "e": e, "P": 2 * (length + w), "ask": ask, "ctx": ctx}

    def solution(self, p: Mapping[str, Any]) -> tuple[Fraction, Fraction]:
        return F(p["k"] * p["w"] + p["e"]), F(p["w"])

    def rows_of(self, m: Mapping[str, Any]) -> list[list[int]]:
        return [[2, 2, m["P"]], [1, -m["k"], m["e"]]]

    def story(self, m: Mapping[str, Any], x: Any, y: Any) -> list[Any]:
        return [2 * (x + y) - m["P"], x - (m["k"] * y + m["e"])]

    def fmt(self, m: Mapping[str, Any], x: Fraction, y: Fraction) -> tuple[dict[str, Any], str]:
        if m["ask"] == "area":
            text = f"{fstr(x * y)} square metres"
        else:
            text = f"{fstr(x if m['ask'] == 'length' else y)} metres"
        return pair_rec(x, y, text), text

    def wrongs(self, m: Mapping[str, Any], x: Fraction, y: Fraction) -> list[tuple[str, Any]]:
        P, k, e = m["P"], m["k"], m["e"]
        as_sum = _safe(lambda: ref.cramer(ref.eqs([[1, 1, P], [1, -k, e]])))
        less = _safe(lambda: ref.cramer(ref.eqs([[2, 2, P], [1, -k, -e]])))
        semi = F(P, 2)
        out: list[tuple[str, Any]] = [
            ("MC.PAIR.WORD_RECT_PERIMETER_AS_SUM", as_sum),
            ("MC.PAIR.WORD_RECT_MORE_THAN_AS_LESS", less),
        ]
        if m["ask"] == "area":
            # area = x * y, so (value, 1) shows "value" as the area
            out.append(("MC.PAIR.WORD_RECT_AREA_AS_SUM", (x + y, F(1))))
            out.append(("MC.PAIR.WORD_ASKED_OTHER_UNKNOWN", (x, F(1))))
        else:
            out.append(("MC.PAIR.WORD_ASKED_OTHER_UNKNOWN", (y, x)))
            out.append(("MC.PAIR.WORD_RECT_STOPPED_AT_SEMIPERIMETER", (semi, y) if m["ask"] == "length" else (x, semi)))
        return out

    def stem(self, m: Mapping[str, Any], p: Mapping[str, Any]) -> str:
        shape = _SHAPES[m["ctx"]]
        k, e = m["k"], m["e"]
        link = f"{e} metres more than its width" if k == 1 else f"{e} metres more than {k} times its width"
        goal = {"length": f"the length of the {shape}", "width": f"the width of the {shape}", "area": f"the area of the {shape}"}[m["ask"]]
        return pick(
            [
                f"The perimeter of a rectangular {shape} is {m['P']} metres. Its length is {link}. Find {goal}.",
                f"A rectangular {shape} has perimeter {m['P']} metres, and its length is {link}. What is {goal}?",
            ],
            m,
        )

    def steps(self, m: Mapping[str, Any], x: Fraction, y: Fraction) -> list[str]:
        rows = self.rows_of(m)
        last = {"length": f"The length is {fstr(x)} metres.", "width": f"The width is {fstr(y)} metres.", "area": f"The area is {fstr(x)} × {fstr(y)} = {fstr(x * y)} square metres."}[m["ask"]]
        return [
            "Let the length be x metres and the width y metres. The perimeter counts every side.",
            f"The two facts give {ref_text(rows[0])} and {ref_text(rows[1])}.",
            f"Solving the pair gives x = {fstr(x)} and y = {fstr(y)}. {last}",
        ]

    def hints(self, p: Mapping[str, Any]) -> list[str]:
        return _hint_set(
            p,
            [
                "Give the length one letter and the width another.",
                "The perimeter of any rectangle adds all four sides.",
                "Write what the perimeter tells you and what the length says about the width.",
                "Name the two sides first, then turn each fact into one relation.",
            ],
            "Two lengths and two widths make up the perimeter, so the perimeter is twice the sum of length and width.",
            "Full method: name the sides, write the perimeter relation and the relation between length and width, solve the pair, then answer what is asked.",
        )


# ---------------------------------------------------------------- reciprocals


def _recip_text(a: Any, b: Any, c: Any, xs: str, ys: str) -> str:
    out = f"{a}/{xs}" + (" + " if b > 0 else " - ") + f"{abs(b)}/{ys}"
    return f"{out} = {fstr(c)}"


class RecipBase(Family):
    base = 0.55
    sumdiff = False

    def _params(self, p: Mapping[str, Any]) -> tuple[int, int, int, int, int, int]:
        return p["x"], p["y"], p["a"], p["b"], p["d"], p["e"]

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:
        x, y, a, b, d, e = self._params(p)
        s_, t_ = (x + y, x - y) if self.sumdiff else (x, y)
        if 0 in (s_, t_) or a * e - b * d == 0:
            raise IllPosed("pair_unusable")
        u, v = F(1, s_), F(1, t_)
        c1, c2 = a * u + b * v, d * u + e * v
        rows = [[a, b, fstr(c1)], [d, e, fstr(c2)]]
        model = {"family": self.id, "rows": rows, "sd": 1 if self.sumdiff else 0}
        spec = system_spec(rows, model, names=("u", "v"))

        def rec_of(xv: Fraction, yv: Fraction, uv: Fraction, vv: Fraction) -> dict[str, Any]:
            return {"values": {"u": fstr(uv), "v": fstr(vv)}, "value": f"x = {fstr(xv)}, y = {fstr(yv)}"}

        def from_uv(uv: Fraction, vv: Fraction, sd: int) -> dict[str, Any]:
            s, t = 1 / uv, 1 / vv
            xv, yv = ((s + t) / 2, (s - t) / 2) if sd else (s, t)
            return rec_of(xv, yv, uv, vv)

        def closed(sp: Mapping[str, Any]) -> Any:
            mm = sp["model"]
            return from_uv(*ref.cramer(ref.eqs([[r[0], r[1], r[2]] for r in mm["rows"]])), mm["sd"])

        def by_sympy(sp: Mapping[str, Any]) -> Any:
            mm = sp["model"]
            big_x, big_y = sympy.symbols("X Y")
            den1, den2 = (big_x + big_y, big_x - big_y) if mm["sd"] else (big_x, big_y)
            eqs = [
                sympy.Rational(r[0]) / den1 + sympy.Rational(r[1]) / den2 - sympy.Rational(F(r[2]).numerator, F(r[2]).denominator)
                for r in mm["rows"]
            ]
            sol = sympy.solve(eqs, [big_x, big_y], dict=True)
            if len(sol) != 1:
                raise ValueError("not one solution")
            xv, yv = ref._rat(sol[0][big_x]), ref._rat(sol[0][big_y])
            s, t = (xv + yv, xv - yv) if mm["sd"] else (xv, yv)
            return rec_of(xv, yv, 1 / s, 1 / t)

        def scan(sp: Mapping[str, Any]) -> Any:
            mm = sp["model"]
            (a1, b1, k1), (a2, b2, k2) = [(F(r[0]), F(r[1]), F(r[2])) for r in mm["rows"]]
            sd = mm["sd"]

            def y_of_x(xv: Fraction) -> Fraction | None:
                # the first relation fixes 1/(second denominator); recover y from it
                s = xv
                if sd:
                    return None  # handled below
                rest = (k1 - a1 / s) / b1
                return None if rest == 0 else 1 / rest

            if not sd:
                def resid(xv: Fraction, yv: Fraction) -> list[Fraction]:
                    return [a1 / xv + b1 / yv - k1, a2 / xv + b2 / yv - k2]

                xv, yv = ref.scan(resid, y_of_x)
                return rec_of(xv, yv, 1 / xv, 1 / yv)

            # sum and difference: scan x + y = s over the grid, t from the first relation
            hits = []
            for s in ref.GRID:
                if s == 0:
                    continue
                rest = (k1 - a1 / s) / b1
                if rest == 0:
                    continue
                t = 1 / rest
                if a2 / s + b2 / t == k2:
                    hits.append((s, t))
            if len(hits) != 1:
                raise ValueError(f"{len(hits)} grid solutions")
            s, t = hits[0]
            return rec_of((s + t) / 2, (s - t) / 2, 1 / s, 1 / t)

        methods = [
            method("maths.lin2.recip_rows", "closed_form", "reciprocal_substitution", closed),
            method("maths.lin2.recip_sympy", "sympy.solve", "", by_sympy),
            method("maths.lin2.recip_grid", "grid_search", "", scan),
        ]
        key = rec_of(F(x), F(y), u, v)
        key_text = f"x = {x}, y = {y}"
        wrong_pairs = self.wrongs(x, y, s_, t_, rows, u, v)
        wrong = [
            (mc, {"values": {"u": fstr(xv), "v": fstr(yv)}, "value": f"x = {fstr(xv)}, y = {fstr(yv)}"}, f"x = {fstr(xv)}, y = {fstr(yv)}")
            for mc, (xv, yv) in wrong_pairs
            if nice(xv) and nice(yv)
        ]
        e1 = _recip_text(a, b, c1, *self.denoms())
        e2 = _recip_text(d, e, c2, *self.denoms())
        stem = pick(
            [f"Solve for x and y: {e1} and {e2}.", f"Reduce the pair {e1}, {e2} to a pair of linear equations and solve it for x and y."],
            {"x": x, "y": y, "a": a},
        )
        steps = self.steps(a, b, d, e, u, v, s_, t_, x, y)
        return make(
            tpl,
            spec=spec,
            key=key,
            witness={"values": key["values"]},
            key_text=key_text,
            wrong=wrong,
            stem=stem,
            steps=steps,
            hints=self.hints(p),
            methods=methods,
            difficulty=clamp_difficulty(self.base, x, y, a, steps=4),
            role="transfer",
            prediction="What new letters could make both relations linear?",
            slug_text=slug(x, y, a, b, d, e),
            nsteps=len(steps),
        )

    def denoms(self) -> tuple[str, str]:  # pragma: no cover
        raise NotImplementedError

    def wrongs(self, x: int, y: int, s: int, t: int, rows: list[list[Any]], u: Fraction, v: Fraction) -> list[tuple[str, tuple[Fraction, Fraction]]]:  # pragma: no cover
        raise NotImplementedError

    def steps(self, a: int, b: int, d: int, e: int, u: Fraction, v: Fraction, s: int, t: int, x: int, y: int) -> list[str]:  # pragma: no cover
        raise NotImplementedError

    def hints(self, p: Mapping[str, Any]) -> list[str]:  # pragma: no cover
        raise NotImplementedError


class RecipPair(RecipBase):
    id = "lin_recip_pair"

    def denoms(self) -> tuple[str, str]:
        return "x", "y"

    def wrongs(self, x: int, y: int, s: int, t: int, rows: list[list[Any]], u: Fraction, v: Fraction) -> list[tuple[str, tuple[Fraction, Fraction]]]:
        linear = _safe(lambda: ref.cramer(ref.eqs(rows)))
        out: list[tuple[str, tuple[Fraction, Fraction]]] = [
            ("MC.PAIR.RECIP_ANSWER_IS_RECIPROCAL", (u, v)),
            ("MC.PAIR.RECIP_ONE_NOT_INVERTED", (F(x), v)),
            ("MC.PAIR.RECIP_ONE_NOT_INVERTED", (u, F(y))),
            ("MC.PAIR.XY_SWAPPED", (F(y), F(x))),
        ]
        if linear is not None:
            out.insert(2, ("MC.PAIR.RECIP_TREATED_AS_LINEAR", linear))
        return out

    def steps(self, a: int, b: int, d: int, e: int, u: Fraction, v: Fraction, s: int, t: int, x: int, y: int) -> list[str]:
        r1, r2 = (a, b), (d, e)
        return [
            "Put 1/x = u and 1/y = v. Both relations become linear in u and v.",
            f"They read {lin_uv(*r1, self.c(u, v, r1))} and {lin_uv(*r2, self.c(u, v, r2))}.",
            f"Solving gives u = {fstr(u)} and v = {fstr(v)}.",
            f"Turn back: x = 1/u = {x} and y = 1/v = {y}.",
        ]

    @staticmethod
    def c(u: Fraction, v: Fraction, r: tuple[int, int]) -> Fraction:
        return r[0] * u + r[1] * v

    def hints(self, p: Mapping[str, Any]) -> list[str]:
        return _hint_set(
            p,
            [
                "Replace each reciprocal by new letters so that the relations become linear.",
                "Notice that x and y only appear as one over x and one over y.",
                "Try new letters for one over x and for one over y.",
                "Rewrite the pair so that it has no unknowns in the denominators.",
            ],
            "Solve the new linear pair, then remember that the new letters are reciprocals, so finish by turning them back.",
            "Full method: put u for one over x and v for one over y, solve the linear pair in u and v, then take reciprocals to get x and y and check in the original relations.",
        )


def lin_uv(a: Any, b: Any, c: Any) -> str:
    out = coef_text(a, "u", True) + coef_text(b, "v", False)
    return f"{out} = {fstr(c)}"


class RecipSumDiff(RecipBase):
    id = "lin_recip_sumdiff"
    sumdiff = True
    base = 0.65

    def denoms(self) -> tuple[str, str]:
        return "(x + y)", "(x - y)"

    def wrongs(self, x: int, y: int, s: int, t: int, rows: list[list[Any]], u: Fraction, v: Fraction) -> list[tuple[str, tuple[Fraction, Fraction]]]:
        return [
            ("MC.PAIR.RECIP_SUMDIFF_STOPPED_EARLY", (F(s), F(t))),
            ("MC.PAIR.RECIP_SUMDIFF_NOT_HALVED", (F(s + t), F(s - t))),
            ("MC.PAIR.RECIP_SUMDIFF_SIGN_OF_Y", (F(x), F(-y))),
            ("MC.PAIR.XY_SWAPPED", (F(y), F(x))),
            ("MC.PAIR.RECIP_ANSWER_IS_RECIPROCAL", (u, v)),
        ]

    def steps(self, a: int, b: int, d: int, e: int, u: Fraction, v: Fraction, s: int, t: int, x: int, y: int) -> list[str]:
        return [
            "Put 1/(x + y) = u and 1/(x - y) = v. Both relations become linear in u and v.",
            f"They read {lin_uv(a, b, a * u + b * v)} and {lin_uv(d, e, d * u + e * v)}.",
            f"Solving gives u = {fstr(u)} and v = {fstr(v)}, so x + y = {s} and x - y = {t}.",
            f"Add and subtract: x = ({s} + ({t}))/2 = {x} and y = ({s} - ({t}))/2 = {y}.",
        ]

    def hints(self, p: Mapping[str, Any]) -> list[str]:
        return _hint_set(
            p,
            [
                "The two denominators repeat. Give each one its own new letter.",
                "Replace one over the sum and one over the difference by new letters.",
                "Start by naming the two repeated reciprocals so that the relations become linear.",
                "Look for the parts that appear in both relations and rename them.",
            ],
            "After solving for the new letters, take reciprocals to find the sum and the difference, then use those two to find x and y.",
            "Full method: rename the two reciprocals, solve the linear pair, invert to get the sum and the difference of x and y, then add and subtract and halve.",
        )


WORD_FAMILIES: dict[str, Family] = {
    f.id: f
    for f in (
        WordAges(),
        WordFraction(),
        WordStream(),
        WordCost(),
        WordRect(),
        RecipPair(),
        RecipSumDiff(),
    )
}
