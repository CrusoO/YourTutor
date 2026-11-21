"""Code-built explainer stories for common maths questions (no model, no guessing).

A question that matches one of six families is turned into an engine `story` request by code
alone: the numbers are read with a strict parser (never `eval`), every number and step is
recomputed with the allowlist parser or sympy, and the story's `checked` role goes only on values
the code verified. A question that matches no family returns None, so the caller falls back to
the model-backed story or to the plain "not available yet" message.

Families (tried most specific first): the sign flip of `x - a = 0`, a quadratic with real rational
roots, a linear equation `ax + b = c` with a whole-number answer, Pythagoras with a whole-number
side, the area or circumference of a circle, and whole-number addition or subtraction on a number
line. Narration follows the explainer pattern: a hook question, an example before the rule, one
idea per scene, a worked example, a one-line recap and a last "your turn" sentence with no digit.

Nothing here logs or stores the question; the output is a pure function of the parsed numbers.
"""

from __future__ import annotations

import copy
import math
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import sympy

from app.content.math_parse import ParseError, expressions_equivalent
from app.content.stem_solve import Unsolvable, solve_extracted, substitution_holds

MAX_DIGITS = 3  # a number of four digits or more is "huge": no template
MAX_RESIDUE_WORDS = 18  # words around the maths; a long essay is not a maths question
MAX_SENTENCE_WORDS = 26
VARIABLES = "xyz"

_SCENE_ROLES = ("hook", "build", "build", "reveal", "wrap")


@dataclass(frozen=True)
class TemplateStory:
    """A story built by code and the values the code checked (their spoken form)."""

    family: str
    story: dict[str, Any]
    verified: list[str]


# ── spoken numbers ───────────────────────────────────────────────────────────

_ONES = (
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
    "fifteen sixteen seventeen eighteen nineteen"
).split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def say(n: int) -> str:
    """A whole number in words, up to 999 either side of zero (the parser allows no more)."""
    if n < 0:
        return "negative " + say(-n)
    if n < 20:
        return _ONES[n]
    if n < 100:
        tens, ones = divmod(n, 10)
        return _TENS[tens] + (f" {_ONES[ones]}" if ones else "")
    hundreds, rest = divmod(n, 100)
    return f"{_ONES[hundreds]} hundred" + (f" {say(rest)}" if rest else "")


def say_q(q: sympy.Rational) -> str:
    """A rational number in words: "three", "negative one over two"."""
    q = sympy.Rational(q)
    if q.q == 1:
        return say(int(q.p))
    return f"{say(int(q.p))} over {say(int(q.q))}"


def tex_q(q: sympy.Rational) -> str:
    q = sympy.Rational(q)
    if q.q == 1:
        return str(int(q.p))
    sign = "-" if q.p < 0 else ""
    return f"{sign}\\frac{{{abs(int(q.p))}}}{{{int(q.q)}}}"


# ── reading the question ─────────────────────────────────────────────────────


def _prep(question: str) -> str | None:
    """Lower-case ASCII text with one minus and one times sign; None when it is not plain maths.

    Unicode digits become ASCII, `x²` becomes `x^2`. A decimal number or a number of four digits
    or more returns None (not supported: never guess)."""
    out = []
    for ch in question:
        out.append(str(unicodedata.digit(ch)) if ch.isdecimal() else ch)
    text = "".join(out)
    for src, dst in (("−", "-"), ("–", "-"), ("—", "-"), ("×", "*"), ("·", "*"), ("²", "^2")):
        text = text.replace(src, dst)
    text = text.replace("**", "^").lower()
    text = " ".join(text.split())
    if not text or re.search(r"\d\s*[.,]\s*\d", text) or re.search(r"\d{4,}", text):
        return None
    return text


def _residue_ok(text: str, span: tuple[int, int]) -> bool:
    """The words outside the matched maths are few, so the text is a maths question."""
    rest = text[: span[0]] + " " + text[span[1] :]
    return len(re.findall(r"[a-z]+", rest)) <= MAX_RESIDUE_WORDS


_TERM = r"(?:\d+\s*\*?\s*)?[xyz](?:\s*\^\s*2)?|\d+"
_POLY = rf"[+-]?\s*(?:{_TERM})(?:\s*[+-]\s*(?:{_TERM}))*"
_EQUATION = re.compile(rf"(?<![\w.^])({_POLY})\s*=\s*({_POLY})(?![\w.^])")
_ONE_TERM = re.compile(rf"([+-]?)\s*({_TERM})")


def _poly(side: str) -> tuple[str | None, dict[int, int]]:
    """(variable or None, {power: coefficient}) of one side of an equation."""
    var: str | None = None
    coeffs: dict[int, int] = {}
    for sign, term in _ONE_TERM.findall(side):
        term = re.sub(r"\s+", "", term).replace("*", "")
        match = re.fullmatch(r"(\d*)([xyz])(?:\^2)?", term)
        if match:
            letter = match.group(2)
            if var not in (None, letter):
                raise ValueError("two unknowns")
            var = letter
            power = 2 if "^2" in term else 1
            value = int(match.group(1)) if match.group(1) else 1
        else:
            power, value = 0, int(term)
        coeffs[power] = coeffs.get(power, 0) + (-value if sign == "-" else value)
    return var, coeffs


def _equation(
    text: str,
) -> tuple[str, dict[int, int], dict[int, int], tuple[int, int]] | None:
    """The single one-unknown equation in the text: (variable, left, right, span)."""
    found = list(_EQUATION.finditer(text))
    if len(found) != 1:
        return None
    match = found[0]
    try:
        lv, left = _poly(match.group(1))
        rv, right = _poly(match.group(2))
    except ValueError:
        return None
    if lv and rv and lv != rv:
        return None
    var = lv or rv
    if var is None:
        return None
    return var, left, right, match.span()


# ── the verified-input helpers ───────────────────────────────────────────────


def _lin_text(var: str, a: int, b: int, c: int) -> str:
    return f"{a}*{var}+({b})={c}"


def _tex_term(coef: int, var: str) -> str:
    return var if coef == 1 else f"-{var}" if coef == -1 else f"{coef}{var}"


def _signed(n: int) -> str:
    return f"+{n}" if n > 0 else str(n)


# ── scene building blocks ────────────────────────────────────────────────────


def _shape(kind: str, s: int, **fields: Any) -> dict[str, Any]:
    shape: dict[str, Any] = {"kind": kind, **fields}
    shape["in"] = {"s": s}
    return shape


def _circle(s: int, cx: float, cy: float, r: float, color: str, **extra: Any) -> dict[str, Any]:
    return _shape("circle", s, cx=cx, cy=cy, r=r, color=color, fill=color, **extra)


def _rect(
    s: int, x: float, y: float, w: float, h: float, color: str, **extra: Any
) -> dict[str, Any]:
    return _shape("rect", s, x=x, y=y, w=w, h=h, color=color, fill=color, round=1, **extra)


def _arrow(
    s: int, x1: float, y1: float, x2: float, y2: float, color: str, **extra: Any
) -> dict[str, Any]:
    return _shape(
        "arrow", s, x1=x1, y1=y1, x2=x2, y2=y2, color=color, fill="none", how="draw", **extra
    )


def _line(s: int, x1: float, y1: float, x2: float, y2: float, color: str, **extra: Any) -> dict:
    return _shape("line", s, x1=x1, y1=y1, x2=x2, y2=y2, color=color, fill="none", **extra)


def _math(
    s: int, x: float, y: float, latex: str, color: str = "ink", size: float = 3.6, **extra: Any
) -> dict[str, Any]:
    return _shape(
        "math", s, x=x, y=y, latex=latex, size=size, anchor="middle", color=color, how="write",
        **extra,
    )  # fmt: skip


def _text(s: int, x: float, y: float, text: str, color: str = "soft", **extra: Any) -> dict:
    return _shape(
        "text", s, x=x, y=y, text=text, size=3.2, anchor="middle", color=color, fill="none",
        how="fade", **extra,
    )  # fmt: skip


def _move(shape: dict[str, Any], s: int, dx: float, dy: float = 0, dur: int = 1000) -> None:
    """Give a shape a motion cue: it moves by (dx, dy) when sentence `s` starts."""
    shape.setdefault("moves", []).append(
        {"at": {"s": s}, "dur": dur, "dx": dx, "dy": dy, "ease": "smooth"}
    )


def _scene(
    role: str,
    heading: str,
    sentences: list[str],
    visuals: list[dict[str, Any]],
    highlights: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    scene: dict[str, Any] = {
        "role": role,
        "heading": heading,
        "sentences": sentences,
        "visuals": visuals,
    }
    if highlights:
        scene["highlights"] = highlights
    return scene


def _hl(s: int, word: str, role: str) -> dict[str, Any]:
    return {"s": s, "word": word, "role": role}


def _wrap(recap: str, skill: str, formula: str) -> dict[str, Any]:
    """The closing scene: a one-line recap and a "your turn" sentence that names the skill."""
    formula_shape = _math(0, 50, 18, formula, "purple", 4, role="term")
    _move(formula_shape, 1, 0, -2, 700)
    return _scene(
        "wrap",
        "Your turn",
        [recap, f"Your turn: try {skill} in the app and work it out yourself."],
        [formula_shape],
        [],
    )


# ── family: the sign flip of x - a = 0 and x + a = 0 ─────────────────────────


def _sign_flip(var: str, a: int, sign: int) -> TemplateStory | None:
    """`var - a = 0` (sign=-1) or `var + a = 0` (sign=+1), with a from 1 to 999."""
    if not 1 <= a <= 999:
        return None
    op = "+" if sign > 0 else "-"
    equation = f"{var}{op}{a}=0"
    root = -sign * a  # x - 3 = 0 gives 3; x + 3 = 0 gives -3
    try:
        if solve_extracted(equation) != root or not substitution_holds(equation, str(root)):
            return None
    except (ParseError, Unsolvable):
        return None
    word = "minus" if sign < 0 else "plus"
    spoken = f"{var} {word} {say(a)} equals zero"
    ref = say(root)
    start = root + 3 if root >= 0 else root - 3
    lo, hi = min(root, start, 0) - 1, max(root, start, 0) + 1
    if hi - lo < 6:
        lo, hi = lo - 2, hi + 2
    span = hi - lo

    def at(v: float) -> float:
        return 10 + (v - lo) / span * 80

    def numberline(s: int) -> dict[str, Any]:
        return _shape(
            "numberline", s, x=10, y=28, w=80, min=lo, max=hi, step=1 if span <= 26 else 2,
            color="ink",
        )  # fmt: skip

    hook_eq = _math(0, 50, 14, f"{var}{op}{a}=0", "purple", 4.4, role="term")
    _move(hook_eq, 1, 0, -2, 800)
    hook = _scene(
        "hook",
        "Why does the sign flip?",
        [
            "Why does the sign seem to flip in an equation like this?",
            f"Take {spoken}.",
            f"Which number is {var}, and why is it not the one you first expect?",
        ],
        [hook_eq, _text(2, 50, 36, "a sign that seems to flip")],
    )
    friend = _circle(1, at(start), 22, 2.8, "blue", id="friend", label=var, labelPos="above")
    _move(friend, 3, at(root) - at(start), 0, 1500)
    target = _circle(2, at(root), 22, 2.8, "red", id="target", label="target", labelPos="below")
    distance = _arrow(2, at(start), 36, at(root), 36, "orange", label="distance")
    measure = (
        f"{var} minus {say(a)} tells us how far the friend is from {say(a)}."
        if sign < 0
        else f"{var} plus {say(a)} is {var} minus negative {say(a)}, so it tells us how far "
        f"the friend is from negative {say(a)}."
    )
    build1 = _scene(
        "build",
        "A friend on a line",
        [
            "Imagine a number line with a friend standing on it.",
            f"Call the friend's spot {var}.",
            measure,
            "When that distance is zero, the friend stands exactly on the target.",
        ],
        [numberline(0), friend, target, distance],
        [_hl(2, "far", "term")],
    )
    eq_shape = _math(0, 25, 16, f"{var}{op}{a}=0", "ink", 3.8)
    arrow = _arrow(1, 36, 16, 62, 16, "orange", label="zero distance")
    ans_shape = _math(1, 75, 16, f"{var}={root}", "green", 4.2, role="key")
    _move(ans_shape, 1, 0, -2, 700)
    rule = _scene(
        "build",
        "Where the target is",
        [
            f"Zero distance means {var} sits on {ref}.",
            f"So {var} equals {ref}.",
            "The sign flips because the equation measures distance from a number, "
            "and the target is the number that makes it zero.",
            "A common slip is to copy the number with the same sign it has in the equation.",
        ],
        [eq_shape, arrow, ans_shape],
        [_hl(3, "same sign", "look-again")],
    )
    check_shape = _math(1, 50, 26, f"{root}{op}{a}=0", "green", 4.2, role="checked")
    _move(check_shape, 2, 0, -2, 700)
    worked = _scene(
        "reveal",
        "Check the answer",
        [
            f"Let us check by putting {ref} in place of {var}.",
            f"{ref} {word} {say(a)} is zero.",
            f"So {var} equals {ref} is right.",
        ],
        [_math(0, 50, 12, f"{var}{op}{a}=0", "ink", 3.6), check_shape],
        [_hl(2, ref, "checked")],
    )
    wrap = _wrap(
        f"In short, the number that makes the sum zero is the answer: {var} equals {ref}.",
        "an equation like this",
        f"{var}{op}a=0",
    )
    title = f"Why {var} {word} {a} equals zero flips the sign"
    return TemplateStory(
        "sign_flip", {"title": title, "scenes": [hook, build1, rule, worked, wrap]}, [ref]
    )


# ── family: a linear equation ax + b = c ─────────────────────────────────────


def _linear(var: str, a: int, b: int, c: int) -> TemplateStory | None:
    if a == 0 or (a == 1 and b == 0):
        return None  # no unknown to find, or the answer is on show
    if max(abs(a), abs(b), abs(c)) > 999 or (c - b) % a != 0:
        return None
    x = (c - b) // a
    mid = c - b
    if abs(x) > 999:
        return None
    equation = _lin_text(var, a, b, c)
    try:
        solved = solve_extracted(equation)
        if solved != x or not substitution_holds(equation, str(x)):
            return None
        if not expressions_equivalent(str(mid), f"{c}-({b})"):
            return None
        if not expressions_equivalent(str(a * x), str(mid)):
            return None
    except (ParseError, Unsolvable):
        return None

    lat = f"{_tex_term(a, var)}{_signed(b) if b else ''}={c}"
    left_say = ("" if a == 1 else "negative " if a == -1 else f"{say(a)} ") + var
    left_say = left_say.strip()
    full_say = f"{left_say}{(' plus ' if b > 0 else ' minus ') + say(abs(b)) if b else ''}"
    eq_say = f"{full_say} equals {say(c)}"
    fwd: list[tuple[str, str, str, str]] = []  # (machine label, do, undo, undo label)
    if a != 1:
        fwd.append((f"×{a}", f"multiply it by {say(a)}", f"divide by {say(a)}", f"÷{a}"))
    if b != 0:
        if b > 0:
            fwd.append((f"+{b}", f"add {say(b)}", f"take away {say(b)}", f"−{b}"))
        else:
            fwd.append((f"−{-b}", f"take away {say(-b)}", f"add {say(-b)}", f"+{-b}"))
    ops_phrase = ", then ".join(o[1] for o in fwd)

    hook = _scene(
        "hook",
        "A hidden number",
        [
            "Can you find a hidden number from a clue?",
            f"Take the number {var}: {ops_phrase}, and you get {say(c)}.",
            f"Which number was {var}?",
        ],
        [
            _math(0, 50, 16, lat, "purple", 4.6, role="term"),
            _circle(2, 50, 33, 3, "blue", label="?"),
        ],
    )
    _move(hook["visuals"][1], 2, 0, -3, 800)

    machine_label = " ".join(o[0] for o in fwd)
    token = _circle(1, 14, 22, 2.6, "blue", id="token")
    _move(token, 2, 54, 0, 1600)
    machine = [
        _circle(0, 12, 22, 4, "blue", label=var, labelPos="below"),
        _arrow(1, 17, 22, 32, 22, "ink"),
        _rect(1, 32, 16, 34, 12, "teal", label=machine_label, labelPos="center"),
        _arrow(2, 66, 22, 82, 22, "ink"),
        _circle(2, 88, 22, 4, "green", label=str(c), labelPos="below"),
        token,
    ]
    build1 = _scene(
        "build",
        "A number machine",
        [
            "Picture a number machine with a slot on each side.",
            f"You drop in {var}, and the machine does its work: {ops_phrase}.",
            f"Out comes {say(c)}.",
            "Solving the equation means finding what went into the slot.",
        ],
        machine,
        [_hl(3, "equation", "term")],
    )

    steps: list[tuple[str, int]] = []
    value = c
    chain = [_circle(0, 14, 22, 4, "green", label=str(c), labelPos="below")]
    sentences = ["To find the input, run the machine backwards, undoing the last step first."]
    highlights: list[dict[str, Any]] = []
    undo_ops = list(reversed(fwd))
    px = 14.0
    gap = 68 / max(len(undo_ops), 1)
    for k, op in enumerate(undo_ops, 1):
        value = value - b if op[3].startswith(("−", "+")) else value // a
        steps.append((op[2], value))
        nx = px + gap
        chain.append(_arrow(k, px + 5, 22, nx - 5, 22, "orange", label=op[3]))
        last = k == len(undo_ops)
        chain.append(
            _circle(k, nx, 22, 4, "blue" if last else "green", label=str(value), labelPos="below")
        )
        sentences.append(f"{op[2].capitalize()}, and {say(value)} is left.")
        highlights.append(_hl(k, say(value), "checked"))
        px = nx
    sentences.append("The same move on both sides keeps the equation true.")
    _move(chain[-1], len(sentences) - 1, 0, -2, 700)
    rule = _scene("build", "Run it backwards", sentences, chain, highlights)

    m1 = _math(0, 50, 9, lat, "ink", 3.6)
    m2 = _math(1, 50, 17, f"{_tex_term(a, var)}={mid}" if b else lat, "ink", 3.6, role="checked")
    m3 = _math(2, 50, 25, f"{var}={x}", "green", 4.4, role="key")
    m4 = _math(3, 50, 34, f"{a}({x}){_signed(b) if b else ''}={c}", "ink", 3.4, role="checked")
    _move(m3, 2, 0, -1.5, 700)
    s_take = (
        f"Take away {say(b)} from both sides, which leaves {left_say} equals {say(mid)}."
        if b > 0
        else f"Add {say(-b)} to both sides, which leaves {left_say} equals {say(mid)}."
        if b < 0
        else f"There is nothing to add or take away, so {left_say} equals {say(mid)}."
    )
    s_div = (
        f"Divide both sides by {say(a)} and {var} equals {say(x)}."
        if a != 1
        else f"So {var} equals {say(x)}."
    )
    tail = f" plus {say(b)}" if b > 0 else f" minus {say(-b)}" if b < 0 else ""
    s_check = f"Check: {say(a)} times {say(x)}{tail} is {say(c)}, which matches."
    worked_shapes = [m1, m2, m3, m4]
    worked = _scene(
        "reveal",
        "Worked and checked",
        [f"Write it down: {eq_say}.", s_take, s_div, s_check],
        worked_shapes,
        [_hl(2, say(x), "checked")],
    )
    wrap = _wrap(
        "So: undo the last step first, then the one before, and treat both sides alike.",
        "a linear equation",
        "ax+b=c",
    )
    verified = sorted({say(x), say(mid)}, key=len)
    return TemplateStory(
        "linear",
        {"title": f"Solving {lat}"[:120], "scenes": [hook, build1, rule, worked, wrap]},
        verified,
    )


# ── family: a quadratic with real, rational roots ────────────────────────────


def _quad_latex(var: str, a: int, b: int, c: int) -> str:
    out = f"{'' if a == 1 else '-' if a == -1 else a}{var}^2"
    if b:
        out += ("+" if b > 0 else "-") + ("" if abs(b) == 1 else str(abs(b))) + var
    if c:
        out += _signed(c)
    return out


def _quad_say(var: str, a: int, b: int, c: int) -> str:
    lead = "negative " if a < 0 else ""
    out = f"{lead}{'' if abs(a) == 1 else say(abs(a)) + ' '}{var} squared"
    if b:
        out += (" plus " if b > 0 else " minus ") + ("" if abs(b) == 1 else say(abs(b)) + " ")
        out += var
    if c:
        out += (" plus " if c > 0 else " minus ") + say(abs(c))
    return out


def _bracket(var: str, root: sympy.Rational) -> tuple[str, str]:
    """(latex, spoken) of the bracket whose zero is `root`: (q x - p)."""
    p, q = int(root.p), int(root.q)
    lead = "" if q == 1 else str(q)
    if p == 0:
        return f"({lead}{var})", f"{'' if q == 1 else say(q) + ' '}{var}"
    tex = f"({lead}{var}{'-' if p > 0 else '+'}{abs(p)})"
    spoken = f"{'' if q == 1 else say(q) + ' '}{var} {'minus' if p > 0 else 'plus'} {say(abs(p))}"
    return tex, spoken


def _quadratic(var: str, a: int, b: int, c: int) -> TemplateStory | None:
    if a == 0 or max(abs(a), abs(b), abs(c)) > 999:
        return None
    disc = b * b - 4 * a * c
    if disc < 0:
        return None  # complex roots: no template
    root_d = math.isqrt(disc)
    if root_d * root_d != disc:
        return None  # irrational roots: no template
    r1, r2 = sorted((sympy.Rational(-b - root_d, 2 * a), sympy.Rational(-b + root_d, 2 * a)))
    equation = f"{a}*{var}^2+({b})*{var}+({c})=0"
    sym = sympy.Symbol(var)
    try:
        if set(sympy.solve(a * sym**2 + b * sym + c, sym)) != {r1, r2}:
            return None
        for r in {r1, r2}:
            if not substitution_holds(equation, str(r)):
                return None
    except (ParseError, Unsolvable):
        return None
    q1, q2 = int(r1.q), int(r2.q)
    k, rem = divmod(a, q1 * q2)
    if rem != 0:
        return None
    factored = k * (q1 * sym - int(r1.p)) * (q2 * sym - int(r2.p))
    if sympy.expand(factored) != sympy.expand(a * sym**2 + b * sym + c):
        return None
    t1, s1 = _bracket(var, r1)
    t2, s2 = _bracket(var, r2)
    lead_tex = "" if k == 1 else "-" if k == -1 else str(k)
    lead_say = "" if k == 1 else f"{say(k)} times "
    lat = _quad_latex(var, a, b, c) + "=0"
    eq_say = f"{_quad_say(var, a, b, c)} equals zero"
    double = r1 == r2
    w1, w2 = say_q(r1), say_q(r2)

    hook = _scene(
        "hook",
        "Zero from a product",
        [
            "If two numbers multiply to make zero, what must be true about them?",
            f"Could that one fact crack {eq_say}?",
        ],
        [_math(0, 50, 18, r"\square\times\square=0", "purple", 4.6, role="term")],
    )
    _move(hook["visuals"][0], 1, 0, -2, 800)
    zero_box = _rect(1, 20, 12, 22, 10, "orange", label="zero", labelPos="center")
    other = _rect(1, 58, 12, 22, 10, "blue", label="anything", labelPos="center")
    prod = _math(2, 50, 32, r"0\times\text{anything}=0", "ink", 3.6)
    _move(zero_box, 2, 0, 2, 700)
    build1 = _scene(
        "build",
        "Zero times anything",
        [
            "Try it with a product, which is what you get when you multiply.",
            "Any number times zero is zero.",
            "But two numbers that are not zero never multiply to make zero.",
            "So at least one of the two must itself be zero.",
        ],
        [zero_box, other, prod],
        [_hl(0, "product", "term")],
    )
    eq_shape = _math(0, 50, 10, lat, "ink", 3.8)
    fac_shape = _math(1, 50, 26, f"{lead_tex}{t1}{t2}=0", "green", 4.2, role="checked")
    down = _arrow(1, 50, 15, 50, 21, "orange", label="factor")
    _move(fac_shape, 2, 0, -1.5, 700)
    rule = _scene(
        "build",
        "Two brackets",
        [
            "Write the equation as brackets multiplied together.",
            f"Here that is {lead_say}{s1} times {s2}, equal to zero.",
            "Now one bracket must be zero, so we set each one to zero in turn.",
        ],
        [eq_shape, down, fac_shape],
    )
    m1 = _math(0, 30, 16, f"{var}={tex_q(r1)}", "green", 4.2, role="checked")
    m2 = _math(1, 70, 16, f"{var}={tex_q(r2)}", "green", 4.2, role="checked")
    both = f"{var}={tex_q(r1)}" if double else f"{var}={tex_q(r1)},\\ {tex_q(r2)}"
    m3 = _math(2, 50, 30, both, "ink", 3.8, role="key")
    _move(m3, 2, 0, -1.5, 700)
    if double:
        sentences = [
            f"The bracket {s1} is zero when {var} equals {w1}.",
            "The other bracket is the same one, so there is only one root.",
            f"Putting {w1} back in makes the equation zero, so it is checked.",
        ]
        shapes = [m1, m3]
        marks = [_hl(0, w1, "checked")]
    else:
        sentences = [
            f"The first bracket, {s1}, is zero when {var} equals {w1}.",
            f"The second, {s2}, is zero when {var} equals {w2}.",
            "Putting each root back in makes the equation zero, so both are checked.",
        ]
        shapes = [m1, m2, m3]
        marks = [_hl(0, w1, "checked"), _hl(1, w2, "checked")]
    worked = _scene("reveal", "Both roots", sentences, shapes, marks)
    wrap = _wrap(
        "In short, factor into brackets, then set each bracket to zero.",
        "a quadratic equation",
        r"(x-p)(x-q)=0",
    )
    return TemplateStory(
        "quadratic",
        {"title": f"Solving {lat}"[:120], "scenes": [hook, build1, rule, worked, wrap]},
        [w1] if double else [w1, w2],
    )


# ── family: Pythagoras with a whole-number side ──────────────────────────────


def _pythagoras(first: int, second: int, hyp_given: bool) -> TemplateStory | None:
    """Two whole-number sides: both legs (find the hypotenuse) or the hypotenuse and a leg."""
    if hyp_given:
        c, a = first, second
        if not 0 < a < c or c > 999:
            return None
        b2 = c * c - a * a
        b = math.isqrt(b2)
        if b * b != b2 or b == 0:
            return None
    else:
        a, b = first, second
        if a <= 0 or b <= 0 or max(a, b) > 999:
            return None
        c2 = a * a + b * b
        c = math.isqrt(c2)
        if c * c != c2:
            return None
    try:
        if not expressions_equivalent(f"{a}^2+{b}^2", f"{c}^2"):
            return None
        if sympy.sqrt(a * a + b * b) != c:
            return None
    except ParseError:
        return None
    # drawing: the right angle at the bottom left, legs a (across) and b (up)
    k = min(36 / a, 26 / b)
    x0, y0 = 12.0, 38.0
    pa, pb = x0 + a * k, y0 - b * k

    def triangle(s: int) -> list[dict[str, Any]]:
        return [
            _line(s, x0, y0, pa, y0, "blue", width=0.8, label="side", labelPos="below"),
            _line(s, x0, y0, x0, pb, "green", width=0.8, label="side", labelPos="left"),
            _line(s, pa, y0, x0, pb, "red", width=0.8, label="shortcut", labelPos="right"),
        ]

    def walker(s: int) -> dict[str, Any]:
        dot = _circle(s, x0, y0, 2.6, "orange", id="walker")
        _move(dot, s, a * k, 0, 1200)
        _move(dot, s + 1, 0, -b * k, 1200)
        return dot

    if hyp_given:
        q = [
            "How long is the missing side of a right angled triangle?",
            f"The long side across is {say(c)} and one short side is {say(a)}.",
            "Can we find the other short side without measuring it?",
        ]
    else:
        q = [
            "Is cutting straight across really shorter than going round two sides?",
            f"Walk {say(a)} along one side and {say(b)} along the next.",
            "How long is the straight shortcut?",
        ]
    hook = _scene("hook", "The shortcut", q, [*triangle(0), walker(1)])
    build1 = _scene(
        "build",
        "The longest side",
        [
            "Here is a triangle with one corner square, like the corner of a book.",
            "Walking along the two shorter sides takes longer than cutting straight across.",
            "The long side facing the square corner is called the hypotenuse.",
        ],
        [*triangle(0), walker(1)],
        [_hl(2, "hypotenuse", "term")],
    )
    s = 14 / c
    ya = 30.0
    sq_a = _rect(0, 12, ya - a * s, a * s, a * s, "blue", opacity=0.8)
    sq_b = _rect(1, 12 + a * s + 8, ya - b * s, b * s, b * s, "green", opacity=0.8)
    sq_c = _rect(2, 12 + a * s + b * s + 16, ya - c * s, c * s, c * s, "red", opacity=0.8)
    eq = _math(2, 50, 38, r"a^2+b^2=c^2", "purple", 4, role="key")
    _move(sq_a, 1, 0, 1, 700)
    rule = _scene(
        "build",
        "Squares on the sides",
        [
            "Build a square on one short side.",
            "Now build a square on the other short side.",
            "The two small squares together cover exactly the same area as the big square.",
        ],
        [sq_a, sq_b, sq_c, eq],
    )
    if not hyp_given:
        sent = [
            f"Square the first side: {say(a)} squared is {say(a * a)}.",
            f"Square the second: {say(b)} squared is {say(b * b)}.",
            f"Add them to get {say(a * a + b * b)}.",
            f"The hypotenuse is the number that squares to {say(c * c)}, so it is {say(c)}.",
        ]
        shapes = [
            _math(0, 30, 12, f"{a}^2={a * a}", "blue", 3.6, role="checked"),
            _math(1, 70, 12, f"{b}^2={b * b}", "green", 3.6, role="checked"),
            _math(2, 50, 24, f"{a * a}+{b * b}={c * c}", "ink", 3.8, role="checked"),
            _math(3, 50, 35, f"c={c}", "red", 4.4, role="key"),
        ]
        marks = [_hl(0, say(a * a), "checked"), _hl(1, say(b * b), "checked")]
        verified = [say(a * a), say(b * b), say(c * c), say(c)]
        title = f"Right triangle with sides {a} and {b}"
    else:
        sent = [
            f"Square the hypotenuse: {say(c)} squared is {say(c * c)}.",
            f"Square the known side: {say(a)} squared is {say(a * a)}.",
            f"Take one from the other to get {say(b * b)}.",
            f"The missing side is the number that squares to {say(b * b)}, so it is {say(b)}.",
        ]
        shapes = [
            _math(0, 30, 12, f"{c}^2={c * c}", "red", 3.6, role="checked"),
            _math(1, 70, 12, f"{a}^2={a * a}", "blue", 3.6, role="checked"),
            _math(2, 50, 24, f"{c * c}-{a * a}={b * b}", "ink", 3.8, role="checked"),
            _math(3, 50, 35, f"b={b}", "green", 4.4, role="key"),
        ]
        marks = [_hl(0, say(c * c), "checked"), _hl(1, say(a * a), "checked")]
        verified = [say(c * c), say(a * a), say(b * b), say(b)]
        title = f"Right triangle, long side {c} and short side {a}"
    _move(shapes[3], 3, 0, -1.5, 700)
    worked = _scene("reveal", "Worked and checked", sent, shapes, marks)
    wrap = _wrap(
        "In short, the squares on the two short sides add up to the square on the long side.",
        "a right triangle question",
        r"a^2+b^2=c^2",
    )
    return TemplateStory(
        "pythagoras",
        {"title": title, "scenes": [hook, build1, rule, worked, wrap]},
        sorted(set(verified), key=len),
    )


# ── family: area or circumference of a circle ────────────────────────────────


def _circle_family(radius: int, kind: str) -> TemplateStory | None:
    if not 1 <= radius <= 999:
        return None
    r = sympy.Symbol("r", positive=True)
    area = sympy.pi * r**2
    circ = 2 * sympy.pi * r
    try:
        if sympy.diff(area, r) != circ:  # the rim is how fast the area grows with the radius
            return None
        if not expressions_equivalent(f"{radius}^2", str(radius * radius)):
            return None
        coeff = radius * radius if kind == "area" else 2 * radius
        if (area if kind == "area" else circ).subs(r, radius) != coeff * sympy.pi:
            return None
    except ParseError:
        return None
    rs, cs = say(radius), say(coeff)
    ring = _circle(0, 28, 22, 10, "blue", opacity=0.35)
    rad_line = _line(1, 28, 22, 38, 22, "red", width=0.8, label="radius", labelPos="above")
    _move(ring, 1, 0, 1, 700)
    given = _math(1, 72, 22, f"r={radius}", "purple", 4.4, role="term")
    if kind == "area":
        hook = _scene(
            "hook",
            "Covering a circle",
            [
                "How many squares does it take to cover a circle?",
                f"Take a circle whose radius is {rs}.",
                "Can we count the cover without any measuring?",
            ],
            [ring, rad_line, given],
        )
        squares = [
            _circle(0, 20, 22, 8, "soft", opacity=0.4),
            _rect(1, 20, 14, 8, 8, "orange", opacity=0.8),
            _rect(2, 40, 14, 8, 8, "orange", opacity=0.8),
            _rect(2, 50, 14, 8, 8, "orange", opacity=0.8),
            _rect(2, 60, 14, 8, 8, "orange", opacity=0.8),
            _rect(3, 70, 14, 1.2, 8, "yellow"),
        ]
        _move(squares[1], 2, 20, 0, 1200)
        build1 = _scene(
            "build",
            "Squares on the radius",
            [
                "Build a square whose side is the radius.",
                "Now slide copies of that square over the circle.",
                "Three of them fit, with a small piece still left over.",
                "That sliver is a little more than a tenth of one square.",
            ],
            squares,
            [_hl(0, "radius", "term")],
        )
        rule_text = [
            "That count is a number called pi, which is a little more than three.",
            "So the area is pi times the radius times the radius.",
            "Radius times radius, because each square has the radius as its side.",
        ]
        formula = r"A=\pi r^2"
        worked_sentences = [
            f"Here the radius is {rs}, so the radius squared is {say(radius * radius)}.",
            f"Multiply by pi and the area is {cs} pi square units.",
            "The squared value and the product were worked out by code, so they are checked.",
        ]
        w_shapes = [
            _math(0, 50, 14, f"r^2={radius * radius}", "ink", 3.8, role="checked"),
            _math(1, 50, 28, rf"A={coeff}\pi", "green", 4.4, role="key"),
        ]
        w_marks = [_hl(0, say(radius * radius), "checked")]
        verified = [say(radius * radius), cs]
        skill, title = "an area question", f"Area of a circle with radius {radius}"
    else:
        hook = _scene(
            "hook",
            "Around the wheel",
            [
                "How far is it once around a circle?",
                f"Take a wheel whose radius is {rs}.",
                "Can we know that distance without a tape measure?",
            ],
            [ring, rad_line, given],
        )
        wheel = _circle(0, 14, 16, 5, "blue", id="wheel")
        _move(wheel, 1, 31.4, 0, 2400)
        ground = _line(1, 14, 21, 45.4, 21, "red", width=0.8, how="draw", label="distance")
        bar = _rect(2, 10, 28, 10, 3, "orange", label="diameter", labelPos="right")
        build1 = _scene(
            "build",
            "One full roll",
            [
                "Roll a wheel along the ground for one full turn.",
                "The ground it touched is as long as the circumference.",
                "Lay the diameter beside it and the roll is a little over three times as long.",
            ],
            [wheel, ground, bar],
            [_hl(1, "circumference", "term")],
        )
        rule_text = [
            "That count is a number called pi, a little more than three.",
            "So the circumference is pi times the diameter.",
            "The diameter is twice the radius, so it is two pi times the radius.",
        ]
        formula = r"C=2\pi r"
        worked_sentences = [
            f"The radius is {rs}, so the diameter is {say(2 * radius)}.",
            f"Multiply by pi and the circumference is {cs} pi units.",
            "The diameter and the product were worked out by code, so they are checked.",
        ]
        w_shapes = [
            _math(0, 50, 14, f"d={2 * radius}", "ink", 3.8, role="checked"),
            _math(1, 50, 28, rf"C={coeff}\pi", "green", 4.4, role="key"),
        ]
        w_marks = [_hl(0, say(2 * radius), "checked")]
        verified = [say(2 * radius), cs]
        skill, title = "a circumference question", f"Circumference of a circle, radius {radius}"
    f_shape = _math(1, 50, 24, formula, "green", 4.6, role="key")
    note = _text(0, 50, 10, "pi is about three and a bit")
    _move(f_shape, 1, 0, -2, 700)
    rule = _scene("build", "The rule", rule_text, [note, f_shape], [_hl(0, "pi", "term")])
    _move(w_shapes[1], 1, 0, -1.5, 700)
    worked = _scene("reveal", "Worked and checked", worked_sentences, w_shapes, w_marks)
    wrap = _wrap("In short, use pi and the radius, and say the unit.", skill, formula)
    return TemplateStory(
        "circle_" + kind,
        {"title": title, "scenes": [hook, build1, rule, worked, wrap]},
        sorted(set(verified), key=len),
    )


# ── family: whole numbers on a number line ───────────────────────────────────


def _number_line(a: int, op: str, b: int) -> TemplateStory | None:
    if abs(a) > 20 or abs(b) > 20 or b == 0:
        return None
    result = a + b if op == "+" else a - b
    try:
        if solve_extracted(f"{a}{op}({b})") != result:
            return None
    except (ParseError, Unsolvable):
        return None
    hops = b if op == "+" else -b  # positive: hop right
    if a + hops != result:
        return None
    lo, hi = min(a, result, 0) - 1, max(a, result, 0) + 1
    if hi - lo < 6:
        lo, hi = lo - 2, hi + 2
    span = hi - lo
    step = 1 if span <= 26 else 2

    def at(v: float) -> float:
        return 10 + (v - lo) / span * 80

    def numberline(s: int) -> dict[str, Any]:
        return _shape("numberline", s, x=10, y=28, w=80, min=lo, max=hi, step=step, color="ink")

    direction = "right" if hops > 0 else "left"
    count = abs(b)
    phrase = f"hop {say(count)} to the {direction}"
    sym = f"{a}{op}{f'({b})' if b < 0 else b}"
    start_dot = _circle(1, at(a), 22, 2.6, "blue", id="start", label="start", labelPos="above")
    _move(start_dot, 2, at(a + hops) - at(a), 0, 1500)
    hook = _scene(
        "hook",
        "Where do you land?",
        [
            "Where do you end up when you walk along a number line?",
            f"Start at {say(a)} and {phrase}.",
            "Which number do you land on?",
        ],
        [numberline(0), start_dot],
    )
    home = _circle(1, at(0), 22, 2.6, "orange", label="zero", labelPos="above")
    _move(home, 2, 0, -2, 600)
    road = _scene(
        "build",
        "A straight road",
        [
            "Picture a straight road with your home at the middle mark, zero.",
            "Walk to the right and the number gets bigger.",
            "Walk to the left and the number gets smaller.",
        ],
        [numberline(0), home],
        [_hl(0, "road", "term")],
    )
    if b < 0:
        sentence2 = (
            "A negative number turns the direction around: adding a negative hops left, "
            "and subtracting a negative hops right."
        )
    else:
        sentence2 = "The number after the sign says how many hops to take."
    add_arrow = _arrow(1, 30, 18, 46, 18, "green", label="add")
    sub_arrow = _arrow(1, 70, 18, 54, 18, "red", label="subtract")
    _move(add_arrow, 1, 0, -1.5, 600)
    rule = _scene(
        "build",
        "Right and left",
        ["Adding means hop right, and subtracting means hop left.", sentence2],
        [add_arrow, sub_arrow],
        [_hl(0, "hop", "term")],
    )
    end_dot = _circle(2, at(a), 22, 2.6, "green", id="walker")
    _move(end_dot, 2, at(result) - at(a), 0, 1500)
    hop_arrow = _arrow(1, at(a), 34, at(result), 34, "orange", label=f"{count} hops")
    answer = _math(2, 50, 12, f"{sym}={result}", "green", 4.4, role="key")
    worked = _scene(
        "reveal",
        "Worked and checked",
        [
            f"Start on {say(a)}.",
            f"Then {phrase}, one step at a time.",
            f"We land on {say(result)}, which the code also checked.",
        ],
        [numberline(0), hop_arrow, end_dot, answer],
        [_hl(2, say(result), "checked")],
    )
    wrap = _wrap(
        "In short, adding hops right, subtracting hops left, and a negative turns it around.",
        "a number line sum",
        r"a+b",
    )
    return TemplateStory(
        "number_line",
        {"title": f"{sym} on a number line", "scenes": [hook, road, rule, worked, wrap]},
        [say(result)],
    )


# ── dispatcher ───────────────────────────────────────────────────────────────

_CIRCLE_WORDS = re.compile(r"\bcircle|\bcircular\b")
_INT = re.compile(r"(?<![\w.])\d+(?![\w.])")
_NL_OPERAND = r"\(?\s*-?\s*\d{1,2}\s*\)?"
_NL_EXPR = re.compile(rf"(?<![\w.^*/)])({_NL_OPERAND})\s*([+-])\s*({_NL_OPERAND})(?![\w.^*/(])")


def _from_equation(text: str) -> TemplateStory | None:
    found = _equation(text)
    if found is None or not _residue_ok(text, found[3]):
        return None
    var, left, right, _ = found
    if not any(left.get(p) for p in (1, 2)) and any(right.get(p) for p in (1, 2)):
        left, right = right, left  # "7 = 2x + 3": the unknown side first
    if any(p for p, v in right.items() if p > 0 and v):
        return None  # an unknown on both sides: no template
    if left.get(2, 0):
        diff = {p: left.get(p, 0) - right.get(p, 0) for p in (0, 1, 2)}
        return _quadratic(var, diff[2], diff[1], diff[0])
    a1, a0, c = left.get(1, 0), left.get(0, 0), right.get(0, 0)
    if a1 == 1 and a0 != 0 and c == 0:
        return _sign_flip(var, abs(a0), 1 if a0 > 0 else -1)
    return _linear(var, a1, a0, c)


def _numbers(text: str) -> list[int]:
    return [int(n) for n in _INT.findall(text)]


def _from_pythagoras(text: str) -> TemplateStory | None:
    if not re.search(r"\btriangle\b|pythagor|hypotenuse", text):
        return None
    nums = _numbers(text)
    if len(nums) != 2:
        return None
    given = re.search(r"\bhypotenuse\s*(?:is|=|:|of|equals)?\s*(\d+)", text)
    if given:
        c = int(given.group(1))
        other = nums[1] if nums[0] == c else nums[0]
        return _pythagoras(c, other, True)
    if re.search(r"\b(missing|other|third|unknown)\b", text) and not re.search(
        r"\bhypotenuse\b", text
    ):
        return None  # which side is missing is not clear
    if re.search(r"\b(missing|other)\s+(side|leg)\b", text):
        return None
    return _pythagoras(nums[0], nums[1], False)


def _from_circle(text: str) -> TemplateStory | None:
    if not _CIRCLE_WORDS.search(text):
        return None
    wants_area = bool(re.search(r"\barea\b", text))
    wants_rim = bool(re.search(r"circumference|perimeter", text))
    if wants_area == wants_rim:
        return None  # both or neither: ask which
    nums = _numbers(text)
    if len(nums) != 1:
        return None
    n = nums[0]
    if re.search(r"\bdiameter\b", text) and not re.search(r"\bradius\b", text):
        if n % 2:
            return None
        n //= 2
    elif not re.search(r"\bradius\b|\br\s*=", text):
        return None
    return _circle_family(n, "area" if wants_area else "circumference")


def _from_number_line(text: str) -> TemplateStory | None:
    if re.search(r"[a-z]\s*[\^=]|\b[xyz]\b|[*/^]", text):
        return None
    found = list(_NL_EXPR.finditer(text))
    if len(found) != 1 or not _residue_ok(text, found[0].span()):
        return None
    if len(_numbers(text)) != 2:
        return None
    left, op, right = found[0].groups()
    try:
        a = int(re.sub(r"[()\s]", "", left))
        b = int(re.sub(r"[()\s]", "", right))
    except ValueError:
        return None
    return _number_line(a, op, b)


_BUILDERS: tuple[Callable[[str], TemplateStory | None], ...] = (
    _from_equation,
    _from_pythagoras,
    _from_circle,
    _from_number_line,
)


def _clean_check(built: TemplateStory) -> bool:
    """Fail closed: the story must pass the same checks a model-written one gets."""
    from app.explain.story import _quick_qa, handoff_issues, sanitise_roles

    scenes = copy.deepcopy(built.story["scenes"])
    if sanitise_roles(scenes, built.verified):
        return False
    if handoff_issues(scenes) or _quick_qa(scenes):
        return False
    for scene in built.story["scenes"]:
        for sentence in scene["sentences"]:
            if len(sentence.split()) > MAX_SENTENCE_WORDS:
                return False
    return len(scenes) >= 3


def build_template_story(question: str) -> TemplateStory | None:
    """A story for the question when it matches a family and every number checks out, else None."""
    text = _prep(question)
    if text is None:
        return None
    for build in _BUILDERS:
        try:
            built = build(text)
        except (ValueError, ArithmeticError, sympy.SympifyError):
            return None
        if built is not None:
            return built if _clean_check(built) else None
    return None
