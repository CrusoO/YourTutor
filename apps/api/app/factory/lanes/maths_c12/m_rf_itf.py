# ruff: noqa: E501
"""Relations and functions, inverse trigonometric functions."""

from __future__ import annotations

import itertools
import math
from collections.abc import Mapping
from fractions import Fraction
from functools import cache
from typing import Any

import sympy
from sympy.functions.combinatorial.numbers import bell, stirling

from app.factory.lanes.maths_c12 import kit
from app.factory.lanes.maths_c12.core import (
    Built,
    F,
    IllPosed,
    case,
    fr,
    hints3,
    model,
    poly_text,
    sup,
)  # fmt: skip

CH = "cbse.12.maths."
RF, ITF = CH + "relations_functions", CH + "inverse_trig"


def slug(*parts: Any) -> str:
    return "_".join(str(x).replace("-", "m").replace("/", "d").replace("√", "r") for x in parts)


# ================================================================ RF.COUNT_MAPS

KINDS = [
    "functions",
    "injective",
    "surjective",
    "relations",
    "reflexive",
    "symmetric",
    "equivalence",
]


@cache
def _brute_relations_on(m: int, kind: str) -> int:
    pairs = [(i, j) for i in range(m) for j in range(m)]
    count = 0
    for mask in range(1 << len(pairs)):
        rel = {pairs[b] for b in range(len(pairs)) if mask >> b & 1}
        refl = all((i, i) in rel for i in range(m))
        symm = all((j, i) in rel for (i, j) in rel)
        if kind == "reflexive":
            count += refl
        elif kind == "symmetric":
            count += symm
        elif refl and symm and all((i, k) in rel for (i, j) in rel for (j2, k) in rel if j == j2):
            count += 1
    return count


def _count_formula(md: Mapping[str, Any]) -> int:
    k, m, n = md["kind"], md["m"], md["n"]
    if k == "functions":
        return int(n**m)
    if k == "injective":
        return math.perm(n, m)
    if k == "surjective":
        return sum((-1) ** i * math.comb(n, i) * (n - i) ** m for i in range(n + 1))
    if k == "relations":
        return 2 ** (m * n)
    if k == "reflexive":
        return 2 ** (m * m - m)
    if k == "symmetric":
        return 2 ** (m * (m + 1) // 2)
    row = [1]  # Bell numbers by the triangle recurrence
    for _ in range(m):
        nxt = [row[-1]]
        for x in row:
            nxt.append(nxt[-1] + x)
        row = nxt
    return row[0]


def _count_brute(md: Mapping[str, Any]) -> int:
    k, m, n = md["kind"], md["m"], md["n"]
    if k in ("functions", "injective", "surjective"):
        total = 0
        for f in itertools.product(range(n), repeat=m):
            img = set(f)
            total += (
                1 if k == "functions" else (len(img) == m if k == "injective" else len(img) == n)
            )
        return total
    if k == "relations":
        return sum(1 for _ in range(1 << (m * n)))
    return _brute_relations_on(m, k)


def _count_sympy(md: Mapping[str, Any]) -> int:
    k, m, n = md["kind"], sympy.Integer(md["m"]), sympy.Integer(md["n"])
    val: Any = {
        "functions": lambda: n**m,
        "injective": lambda: sympy.ff(n, m),
        "surjective": lambda: sympy.factorial(n) * stirling(m, n),
        "relations": lambda: sympy.Integer(2) ** (m * n),
        "reflexive": lambda: sympy.Integer(2) ** (m * m - m),
        "symmetric": lambda: sympy.Integer(2) ** sympy.binomial(m + 1, 2),
        "equivalence": lambda: bell(m),
    }[k]()
    return int(val)


_COUNT_STEMS = {
    "functions": "How many different functions can be defined from a set of {m} elements to a set of {n} elements?",
    "injective": "How many one-one functions are there from a set of {m} elements into a set of {n} elements?",
    "surjective": "How many onto functions are there from a set of {m} elements onto a set of {n} elements?",
    "relations": "How many different relations can be defined from a set of {m} elements to a set of {n} elements?",
    "reflexive": "How many reflexive relations are there on a set of {m} elements?",
    "symmetric": "How many symmetric relations are there on a set of {m} elements?",
    "equivalence": "How many equivalence relations are there on a set of {m} elements?",
}
_COUNT_STEP = {
    "functions": "Each of the {m} elements has {n} choices for its image, so there are {n}{m_sup} functions.",
    "injective": "Choose distinct images in turn: {n} choices, then one fewer each time, for {m} elements. The count is {key}.",
    "surjective": "Count all functions, then remove those that miss one or more elements of the target (inclusion and exclusion). The count is {key}.",
    "relations": "A relation is any subset of the {mn} ordered pairs, and each pair is in or out, so there are 2{mn_sup} relations.",
    "reflexive": "The {m} pairs with equal entries must be in. Each of the other {off} ordered pairs is free, so there are 2{off_sup} relations.",
    "symmetric": "Choose each unordered pair, including the {m} pairs with equal entries, freely: {tri} choices, so 2{tri_sup} relations.",
    "equivalence": "An equivalence relation is the same as a way to split the set into groups. Count the splittings: {key}.",
}


@model(
    "RF.COUNT_MAPS", chapter=RF, title="Count functions and relations between small finite sets",
    prereq=["MATH.C12.PRE.SETS_FUNCTIONS"], marks=2, technique="count_by_rule",
    box={"kind": {"choices": KINDS}, "m": {"min": 2, "max": 5}, "n": {"min": 2, "max": 5}},
)  # fmt: skip
def count_maps(p: Mapping[str, Any]) -> Built:
    kind, m, n = str(p["kind"]), int(p["m"]), int(p["n"])
    if kind in ("reflexive", "symmetric", "equivalence") and (n != 2 or m > 4):
        raise IllPosed("unused_or_too_large_parameter")
    if kind == "injective" and m > n:
        raise IllPosed("no_one_one_function_exists")
    if kind == "surjective" and m < n:
        raise IllPosed("no_onto_function_exists")
    if kind == "relations" and m * n > 12:
        raise IllPosed("box_too_large_to_enumerate")
    md = {"kind": kind, "m": m, "n": n}
    key = _count_formula(md)
    allrel = 2 ** (m * m)
    wrong: list[tuple[str, int]] = {
        "functions": [
            ("MC.C12.RF.BASE_EXPONENT_SWAPPED", m**n),
            ("MC.C12.RF.PRODUCT_NOT_POWER", m * n),
            ("MC.C12.RF.ALL_RELATIONS_COUNTED", 2 ** (m * n)),
            ("MC.C12.RF.SUM_FOR_COUNT", m + n),
        ],
        "injective": [
            ("MC.C12.RF.ORDER_IGNORED", math.comb(n, m)),
            ("MC.C12.RF.REPEATS_ALLOWED", n**m),
            ("MC.C12.RF.PRODUCT_NOT_POWER", m * n),
            ("MC.C12.RF.BASE_EXPONENT_SWAPPED", m**n),
        ],
        "surjective": [
            ("MC.C12.RF.ALL_FUNCTIONS_COUNTED", n**m),
            ("MC.C12.RF.STOPPED_AFTER_ONE_SUBTRACTION", n**m - n * (n - 1) ** m),
            ("MC.C12.RF.CHOSE_ONE_PREIMAGE_ONLY", math.comb(m, n) * math.factorial(n)),
            ("MC.C12.RF.ORDER_IGNORED", math.comb(m, n)),
        ],
        "relations": [
            ("MC.C12.RF.PRODUCT_NOT_POWER", m * n),
            ("MC.C12.RF.SUBSETS_OF_EACH_SET", 2**m * 2**n),
            ("MC.C12.RF.COUNTED_FUNCTIONS_ONLY", n**m),
            ("MC.C12.RF.BASE_EXPONENT_SWAPPED", m**n),
        ],
        "reflexive": [
            ("MC.C12.RF.ALL_RELATIONS_COUNTED", allrel),
            ("MC.C12.RF.COUNTED_DIAGONAL_CHOICES", 2**m),
            ("MC.C12.RF.FORGOT_ORDERED_PAIRS", 2 ** (m * (m - 1) // 2)),
            ("MC.C12.RF.PRODUCT_NOT_POWER", m * m - m),
        ],
        "symmetric": [
            ("MC.C12.RF.ALL_RELATIONS_COUNTED", allrel),
            ("MC.C12.RF.DIAGONAL_OMITTED", 2 ** (m * (m - 1) // 2)),
            ("MC.C12.RF.COUNTED_DIAGONAL_CHOICES", 2**m),
            ("MC.C12.RF.PRODUCT_NOT_POWER", m * (m + 1) // 2),
        ],
        "equivalence": [
            ("MC.C12.RF.COUNTED_SUBSETS_NOT_PARTITIONS", 2**m),
            ("MC.C12.RF.PERMUTATIONS_COUNTED", math.factorial(m)),
            ("MC.C12.RF.ALL_RELATIONS_COUNTED", allrel),
            ("MC.C12.RF.SUM_FOR_COUNT", m + 1),
        ],
    }[kind]
    step = _COUNT_STEP[kind].format(
        m=m, n=n, m_sup=sup(m), mn=m * n, mn_sup=sup(m * n), off=m * m - m, off_sup=sup(m * m - m),
        tri=m * (m + 1) // 2, tri_sup=sup(m * (m + 1) // 2), key=key,
    )  # fmt: skip
    return case(
        fam="RF.COUNT_MAPS", md=md, names=["count"], value=key, stem=_COUNT_STEMS[kind].format(m=m, n=n),
        steps=["Decide what must be chosen and how many independent choices there are.", step, f"So the number is {key}."],
        hints=hints3(
            p,
            ["Ask what has to be decided for each element, and how many options it has.", "Think about what you are counting: separate choices that multiply, or whole sets of pairs.", "Name the objects being counted before you reach for any formula."],
            "Write down the choices one by one and combine them with the multiplication rule, or count subsets of pairs where each pair is in or out.",
            "Full method: identify the objects, list the free choices, multiply their counts, and test your rule on a very small set you can list by hand.",
        ),
        wrong=wrong, base=0.35, role="apply", prediction="Will the count be small or large? Roughly how many digits?",
        slug=slug(kind, m, n), mags=[key % 1000], nsteps=3,
        methods=[
            ("c12.rf.formula", "closed_form", "count_by_rule", _count_formula),
            ("c12.rf.enumeration", "enumeration", "", _count_brute),
            ("c12.rf.sympy", "sympy.combinatorics", "", _count_sympy),
        ],
    )  # fmt: skip


# ================================================================ RF.COMPOSE_AT


def _compose_formula(md: Mapping[str, Any]) -> Fraction:
    def f(x: Fraction) -> Fraction:
        return md["a"] * x * x + md["b"]

    def g(x: Fraction) -> Fraction:
        return md["c"] * x + md["d"]

    t = F(md["t"])
    return f(g(t)) if md["order"] == "fog" else g(f(t))


def _compose_polynomial(md: Mapping[str, Any]) -> Fraction:
    f = [F(md["b"]), F(0), F(md["a"])]
    g = [F(md["d"]), F(md["c"])]
    outer, inner = (f, g) if md["order"] == "fog" else (g, f)
    composed = [F(0)]
    for k, coeff in enumerate(outer):
        composed = kit.padd(composed, kit.pscale(kit.ppow(inner, k), coeff))
    return kit.pval(composed, F(md["t"]))


def _compose_sympy(md: Mapping[str, Any]) -> Fraction:
    x = sympy.Symbol("x")
    f = md["a"] * x**2 + md["b"]
    g = md["c"] * x + md["d"]
    expr = f.subs(x, g) if md["order"] == "fog" else g.subs(x, f)
    return kit.unsp(sympy.expand(expr).subs(x, md["t"]))


@model(
    "RF.COMPOSE_AT", chapter=RF, title="Evaluate a composite of two functions at a point",
    prereq=["MATH.C12.PRE.SETS_FUNCTIONS"], marks=2, technique="substitute_inside_out",
    box={"a": {"choices": [1, 2, 3]}, "b": {"choices": [-2, 1, 3]}, "c": {"choices": [-1, 2, 3]},
         "d": {"choices": [-2, 1, 4]}, "t": {"choices": [-2, 1, 3]}, "order": {"choices": ["fog", "gof"]}},
)  # fmt: skip
def compose_at(p: Mapping[str, Any]) -> Built:
    a, b, c, d, t, order = (p[k] for k in ("a", "b", "c", "d", "t", "order"))
    md = {"a": a, "b": b, "c": c, "d": d, "t": t, "order": order}
    f_txt, g_txt = poly_text([b, 0, a]), poly_text([d, c])

    def fg(x: int) -> int:
        return int(a * x * x + b)

    def gg(x: int) -> int:
        return int(c * x + d)

    key = _compose_formula(md)
    name = "(f ∘ g)" if order == "fog" else "(g ∘ f)"
    other = gg(fg(t)) if order == "fog" else fg(gg(t))
    inner_val = gg(t) if order == "fog" else fg(t)
    wrong = [
        ("MC.C12.RF.COMPOSITION_ORDER_REVERSED", other),
        ("MC.C12.RF.COMPOSITION_AS_PRODUCT", fg(t) * gg(t)),
        ("MC.C12.RF.COMPOSITION_AS_SUM", fg(t) + gg(t)),
        ("MC.C12.RF.INNER_VALUE_NOT_USED", fg(t) if order == "fog" else gg(t)),
    ]
    return case(
        fam="RF.COMPOSE_AT", md=md, names=["value"], value=key,
        stem=f"Let f be the function x → {f_txt} and g the function x → {g_txt}. Find the value of {name}({t}).",
        steps=[f"{name} means: apply the right-hand function first, then the left-hand one.", f"The inner value is {inner_val}.", f"Apply the outer function to {inner_val}: the result is {fr(key)}."],
        hints=hints3(p, ["Which function acts first in this composite?", "Read the composite from the inside out.", "Decide the order of the two functions before you substitute."],
                     "Work out the inner function at the given number, then use that result as the input of the outer function.",
                     "Full method: evaluate the function nearest the number, write the result down, then put it into the other function and simplify carefully."),
        wrong=wrong, base=0.3, role="apply", prediction="Which function do you apply first?",
        slug=slug(a, b, c, d, t, order), mags=[a, c, t], nsteps=3,
        methods=[("c12.rf.compose.inside_out", "closed_form", "substitute_inside_out", _compose_formula),
                 ("c12.rf.compose.polynomial", "polynomial_composition", "", _compose_polynomial),
                 ("c12.rf.compose.sympy", "sympy.subs", "", _compose_sympy)],
    )  # fmt: skip


# ================================================================ ITF.PRINCIPAL

_SIN_TAB = {0: "0", 30: "1/2", 45: "√2/2", 60: "√3/2", 90: "1"}
_TAN_TAB = {0: "0", 30: "1/√3", 45: "1", 60: "√3"}
_SYM = {
    "0": (sympy.Integer(0), 0.0), "1/2": (sympy.Rational(1, 2), 0.5),
    "√2/2": (sympy.sqrt(2) / 2, math.sqrt(2) / 2), "√3/2": (sympy.sqrt(3) / 2, math.sqrt(3) / 2),
    "1": (sympy.Integer(1), 1.0), "1/√3": (sympy.sqrt(3) / 3, 1 / math.sqrt(3)),
    "√3": (sympy.sqrt(3), math.sqrt(3)),
}  # fmt: skip
_ARG_OK = {
    "asin": ["0", "1/2", "√2/2", "√3/2", "1"],
    "acos": ["0", "1/2", "√2/2", "√3/2", "1"],
    "atan": ["0", "1/√3", "1", "√3"],
}
_FN_TXT = {"asin": "sin⁻¹", "acos": "cos⁻¹", "atan": "tan⁻¹"}


def _sym_arg(v: str) -> tuple[Any, float]:
    s, fl = _SYM[v.lstrip("-")]
    return (-s, -fl) if v.startswith("-") else (s, fl)


def _itf_table(md: Mapping[str, Any]) -> Fraction:
    fn, v = md["fn"], md["v"]
    neg, mag = v.startswith("-"), v.lstrip("-")
    if fn == "asin":
        base = F(next(d for d, s in _SIN_TAB.items() if s == mag), 180)
        out = -base if neg else base
    elif fn == "atan":
        base = F(next(d for d, s in _TAN_TAB.items() if s == mag), 180)
        out = -base if neg else base
    else:  # acos on [0, pi]: cos d = sin (90 - d)
        base = F(90 - next(d for d, s in _SIN_TAB.items() if s == mag), 180)
        out = 1 - base if neg else base
    return out * (2 if md["ask"] == "twice" else 1)


def _itf_sympy(md: Mapping[str, Any]) -> Fraction:
    arg = _sym_arg(md["v"])[0]
    ang = {"asin": sympy.asin, "acos": sympy.acos, "atan": sympy.atan}[md["fn"]](arg)
    return kit.unsp(sympy.simplify(ang / sympy.pi)) * (2 if md["ask"] == "twice" else 1)


def _itf_float(md: Mapping[str, Any]) -> Fraction:
    x = _sym_arg(md["v"])[1]
    ang = {"asin": math.asin, "acos": math.acos, "atan": math.atan}[md["fn"]](x)
    return kit.to_frac(ang / math.pi, 24, 1e-9) * (2 if md["ask"] == "twice" else 1)


def pi_text(q: Fraction) -> str:
    if q == 0:
        return "0"
    num, den = abs(q.numerator), q.denominator
    body = ("" if num == 1 else str(num)) + "π" + (f"/{den}" if den > 1 else "")
    return ("-" if q < 0 else "") + body


@model(
    "ITF.PRINCIPAL", chapter=ITF, title="Find the principal value of an inverse trigonometric function",
    prereq=["MATH.C12.PRE.STANDARD_ANGLES"], marks=1, technique="standard_angle_table",
    box={"fn": {"choices": ["asin", "acos", "atan"]},
         "v": {"choices": ["0", "1/2", "√2/2", "√3/2", "1", "1/√3", "√3", "-1/2", "-√2/2", "-√3/2", "-1", "-1/√3", "-√3"]},
         "ask": {"choices": ["value", "twice"]}},
)  # fmt: skip
def itf_principal(p: Mapping[str, Any]) -> Built:
    fn, v, ask = str(p["fn"]), str(p["v"]), str(p["ask"])
    if v.lstrip("-") not in _ARG_OK[fn]:
        raise IllPosed("argument_outside_the_standard_set_for_this_function")
    md = {"fn": fn, "v": v, "ask": ask}
    key = _itf_table(md)
    k = 2 if ask == "twice" else 1
    base = key / k
    neg = v.startswith("-")
    if fn == "acos":
        range_slip = base - 1 if neg else -base
    else:
        range_slip = (-1 - base) if neg else (1 - base)
    wrong = [
        ("MC.C12.ITF.OUT_OF_PRINCIPAL_RANGE", range_slip * k),
        ("MC.C12.ITF.COMPLEMENT_USED", (F(1, 2) - base) * k),
        ("MC.C12.ITF.SIGN_OF_ARGUMENT_IGNORED", (-base if base != 0 else F(1, 2)) * k),
        ("MC.C12.ITF.STANDARD_ANGLE_MISREMEMBERED", (base + F(1, 6)) * k),
    ]
    inner = f"{_FN_TXT[fn]}({v})"
    asked = inner if ask == "value" else f"2 × {inner}"
    return case(
        fam="ITF.PRINCIPAL", md=md, names=["multiple_of_pi"], value=key, fmt=lambda vv: pi_text(vv[0]),
        stem=f"Find the principal value of {asked}. Give your answer in radians.",
        steps=["Recall the range of principal values for this function.", f"Find the angle in that range whose ratio equals {v}: it is {pi_text(base)}.", f"The asked value is {pi_text(key)}."],
        hints=hints3(p, ["Which interval of angles does this inverse function return?", "The answer must lie in the principal range, not just be any angle with that ratio.", "First decide the allowed range, then search it."],
                     "Recall the standard angles and their ratios, then pick the one inside the principal range whose ratio matches.",
                     "Full method: state the principal range, match the ratio to a standard angle, use the sign of the argument to place it in the right part of the range, give it in radians, then apply any multiplier asked."),
        wrong=wrong, base=0.2, role="recall", prediction="In which quadrant should the angle sit?",
        slug=slug(fn, v, ask), nsteps=2,
        methods=[("c12.itf.table", "exact_table", "standard_angle_table", _itf_table),
                 ("c12.itf.sympy", "sympy.symbolic", "", _itf_sympy),
                 ("c12.itf.float", "numeric_float", "", _itf_float)],
    )  # fmt: skip


# ================================================================ ITF.TRIG_OF_INVERSE

TRIPLES = [(3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25), (20, 21, 29)]


def _sqrt_exact(v: Fraction) -> Fraction:
    n, d = math.isqrt(v.numerator), math.isqrt(v.denominator)
    if n * n != v.numerator or d * d != v.denominator:
        raise ValueError("not a perfect square")
    return Fraction(n, d)


def _sc(inner: str, x: Fraction) -> tuple[Fraction, Fraction]:
    w = _sqrt_exact(1 - x * x)
    return (x, w) if inner == "asin" else (w, x)  # (sin, cos) of the principal angle


def _outer(outer: str, s: Fraction, c: Fraction) -> Fraction:
    if outer == "tan":
        return s / c
    return {"sin": s, "cos": c, "sin2": 2 * s * c, "cos2": c * c - s * s}[outer]


def _tio_hand(md: Mapping[str, Any]) -> Fraction:
    s, c = _sc(md["inner"], F(md["num"] * md["sign"], md["den"]))
    return _outer(md["outer"], s, c)


def _tio_sympy(md: Mapping[str, Any]) -> Fraction:
    x = sympy.Rational(md["sign"] * md["num"], md["den"])
    th = sympy.asin(x) if md["inner"] == "asin" else sympy.acos(x)
    expr = {"sin": sympy.sin(th), "cos": sympy.cos(th), "tan": sympy.tan(th),
            "sin2": sympy.sin(2 * th), "cos2": sympy.cos(2 * th)}[md["outer"]]  # fmt: skip
    return kit.unsp(sympy.simplify(sympy.expand_trig(expr)))


def _tio_float(md: Mapping[str, Any]) -> Fraction:
    x = md["sign"] * md["num"] / md["den"]
    th = math.asin(x) if md["inner"] == "asin" else math.acos(x)
    val = {"sin": math.sin(th), "cos": math.cos(th), "tan": math.tan(th),
           "sin2": math.sin(2 * th), "cos2": math.cos(2 * th)}[md["outer"]]  # fmt: skip
    return kit.to_frac(val, 5000, 1e-9)


@model(
    "ITF.TRIG_OF_INVERSE", chapter=ITF, title="Evaluate a trigonometric ratio of an inverse trigonometric value",
    prereq=["MATH.C12.PRE.STANDARD_ANGLES"], marks=2, technique="right_triangle",
    box={"t": {"min": 0, "max": 4}, "inner": {"choices": ["asin", "acos"]},
         "outer": {"choices": ["sin", "cos", "tan", "sin2", "cos2"]}, "sign": {"choices": [1, -1]},
         "leg": {"choices": [0, 1]}},
)  # fmt: skip
def trig_of_inverse(p: Mapping[str, Any]) -> Built:
    a, b, c = TRIPLES[int(p["t"])]
    num = (a, b)[int(p["leg"])]
    inner, outer, sign = str(p["inner"]), str(p["outer"]), int(p["sign"])
    md = {"num": num, "den": c, "inner": inner, "outer": outer, "sign": sign}
    x = F(sign * num, c)
    s, co = _sc(inner, x)
    if outer == "tan" and co == 0:
        raise IllPosed("tangent_undefined")
    key = _tio_hand(md)
    wrong_vals = [
        (
            "MC.C12.ITF.RANGE_SIGN_IGNORED",
            _outer(outer, s, abs(co)) if (co < 0 or inner == "acos") else -key,
        ),
        ("MC.C12.ITF.RATIO_INVERTED", (1 / key) if key != 0 else key + 1),
        ("MC.C12.ITF.ARGUMENT_REUSED_AS_RATIO", x),
        (
            "MC.C12.ITF.DOUBLE_ANGLE_AS_DOUBLE",
            2 * s if outer == "sin2" else (2 * co if outer == "cos2" else -key),
        ),
        (
            "MC.C12.ITF.LEGS_SWAPPED",
            _outer(outer, co, s) if not (outer == "tan" and s == 0) else key + 1,
        ),
    ]
    inner_txt = f"{_FN_TXT[inner]}({fr(x)})"
    if outer in ("sin2", "cos2"):
        stem = f"Find the exact value of {outer[:3]}(2 × {inner_txt})."
    else:
        stem = f"Find the exact value of {outer}({inner_txt})."
    return case(
        fam="ITF.TRIG_OF_INVERSE", md=md, names=["value"], value=key, stem=stem,
        steps=["Let the angle be the inverse trigonometric value, so its sine or cosine is the given fraction.", f"Draw a right triangle: the third side comes from the Pythagorean theorem, and the principal range fixes the sign (sine {fr(s)}, cosine {fr(co)}).", f"Read off the asked ratio: {fr(key)}."],
        hints=hints3(p, ["Name the angle first, then think of the right triangle it makes.", "The principal range tells you whether the missing ratio is positive or negative.", "Find the other two ratios of the angle before you do anything else."],
                     "Call the angle theta, use the Pythagorean relation to get the missing ratio, fix its sign by the principal range, then build the asked ratio.",
                     "Full method: set theta equal to the inverse function value, find sine and cosine of theta exactly using the right triangle and the principal range, then compute the asked expression, using the double angle identity if the angle is doubled."),
        wrong=wrong_vals, base=0.4, role="apply", prediction="Is the answer positive or negative?",
        slug=slug(c, num, inner, outer, sign), mags=[c], nsteps=3,
        methods=[("c12.itf.triangle", "closed_form", "right_triangle", _tio_hand),
                 ("c12.itf.trig.sympy", "sympy.symbolic", "", _tio_sympy),
                 ("c12.itf.trig.float", "numeric_float", "", _tio_float)],
    )  # fmt: skip
