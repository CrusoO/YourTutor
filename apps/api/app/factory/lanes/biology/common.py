"""Shared pieces of the biology lane: number text, the Draft an item model returns, option choice.

A model's `build` turns one parameter tuple into a `Draft` (spec, answer, witness, words and a
list of named wrong answers) or into a plain reason why the tuple makes a poor item. `finish`
turns a Draft into the final `Built` item: it picks three distinct named wrong options and refuses
a tuple whose hints would give the answer away. Everything is plain data; the checking code is in
methods.py and the kernel.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

from app.factory.kernel.exact import chash

CHAPTERS = {
    "HERED": "cbse.10.biology.heredity",
    "ENV": "cbse.10.biology.environment",
    "REPRO": "cbse.10.biology.reproduction",
    "LIFE": "cbse.10.biology.life_processes",
}
AREA_OF_CHAPTER = {v: k for k, v in CHAPTERS.items()}
NO_BOARD_WORDS = ("cbse", "ncert", "board", "textbook", "publisher", "syllabus", "exam")


def qs(x: Fraction | int) -> str:
    """Canonical exact text of a number (lowest terms), as stored in answers."""
    return str(Fraction(x))


def fr(x: Fraction) -> str:
    """A fraction as a learner writes it: 3/4, or a whole number."""
    x = Fraction(x)
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def dec(x: Fraction) -> str | None:
    """Plain decimal text of a terminating number (at most 4 places), else None."""
    x = Fraction(x)
    if x.denominator == 1:
        return str(x.numerator)
    d = x.denominator
    for p in (2, 5):
        while d % p == 0:
            d //= p
    if d != 1:
        return None
    for places in range(1, 5):
        scaled = x * 10**places
        if scaled.denominator == 1:
            sign = "-" if x < 0 else ""
            digits = str(abs(scaled.numerator)).rjust(places + 1, "0")
            return f"{sign}{digits[:-places]}.{digits[-places:]}"
    return None


_SINGULAR = {
    "molecules": "molecule", "hours": "hour", "minutes": "minute", "cells": "cell",
    "rounds": "round", "chromosomes": "chromosome", "organisms": "organism", "hydras": "hydra",
    "cuts": "cut", "beats": "beat", "breaths": "breath", "bubbles": "bubble", "types": "type",
    "boxes": "box", "kinds": "kind",
}  # fmt: skip


def plural(n: int | Fraction, singular: str) -> str:
    """`1 molecule`, `2 molecules`."""
    n = Fraction(n)
    word = singular if n == 1 else (singular if singular.endswith("offspring") else singular + "s")
    return f"{dec(n)} {word}"


def num_text(x: Fraction, unit: str = "") -> str:
    text = dec(x)
    if text is None:
        raise ValueError("not a terminating decimal")
    if unit and Fraction(x) == 1:
        head, _, tail = unit.partition(" ")
        unit = " ".join(p for p in (_SINGULAR.get(head, head), tail) if p)
    return f"{text} {unit}".strip()


def ratio_text(parts: Sequence[int]) -> str:
    return " : ".join(str(p) for p in parts)


_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten")


def words(n: int) -> str:
    """A small whole number in words, so a hint can say how many steps without a digit."""
    return _WORDS[n] if 0 <= n < len(_WORDS) else str(n)


def lower_first(text: str) -> str:
    return text[:1].lower() + text[1:]


def upper_first(text: str) -> str:
    return text[:1].upper() + text[1:]


def digest(params: Mapping[str, Any]) -> str:
    return hashlib.sha1(
        json.dumps(sorted((k, str(v)) for k, v in params.items())).encode()
    ).hexdigest()[:8]


def algebra_spec(
    find: str, coeff: Fraction, const: Fraction, bio: dict[str, Any]
) -> dict[str, Any]:
    """Kernel linear_system spec: coeff * find = const (the lane's stated relation)."""
    return {
        "domain": "algebra",
        "kind": "linear_system",
        "variables": [find],
        "equations": [{"coeffs": [qs(coeff)], "const": qs(const)}],
        "bio": bio,
    }


def number_answer(value: Fraction, unit: str = "", find: str = "x") -> dict[str, Any]:
    out: dict[str, Any] = {"values": {find: qs(value)}}
    if unit:
        out["unit"] = unit
    return out


@dataclass
class Draft:
    variant: str
    spec: dict[str, Any]
    answer: dict[str, Any]
    witness: dict[str, Any]
    stem: str
    hints: list[str]
    steps: list[str]
    key_text: str
    wrongs: list[tuple[str, dict[str, Any], str]]  # (procedure name, option value, option text)
    difficulty: float = 0.4
    role: str = "apply"
    prediction: str = "Before you work it out, roughly what size of answer do you expect?"
    tokens: list[str] = field(default_factory=list)  # strings hints 1 and 2 must not contain
    features: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Model:
    id: str  # e.g. HERED.MONO_RATIO
    skill: str  # BIO.HERED.MONO_RATIO
    chapter: str
    title: str  # plain skill title
    technique: str  # the allowed technique of method A
    technique_b: str
    group_a: str
    group_b: str
    box: Mapping[str, tuple[str, ...]]
    build: Callable[[Mapping[str, str]], Draft | str]
    solve_a: Callable[[Mapping[str, Any]], dict[str, Any]]
    solve_b: Callable[[Mapping[str, Any]], dict[str, Any]]
    prereqs: tuple[str, ...] = ()


@dataclass
class Built:
    model: Model
    draft: Draft
    item_id: str
    options: list[dict[str, Any]]


_NUM = re.compile(r"(?<![\d.])\d+(?:\.\d+)?(?![\d.])")


def _hint_leaks(hint: str, draft: Draft) -> bool:
    low = hint.lower()
    for token in (*draft.tokens, draft.key_text):
        t = token.strip()
        if not t:
            continue
        if _NUM.fullmatch(t):
            if re.search(rf"(?<![\d.]){re.escape(t)}(?![\d.])", low):
                return True
        elif re.search(rf"(?<![A-Za-z]){re.escape(t)}(?![A-Za-z])", hint):
            return True
    return False


def finish(
    model: Model, params: Mapping[str, Any], draft: Draft, resolve: Callable[[str], str]
) -> Built | str:
    chosen: list[tuple[str, dict[str, Any], str]] = []
    seen_values = {chash(draft.answer)}
    seen_texts = {draft.key_text.strip()}
    for allow_repeat in (False, True):
        for name, value, text in draft.wrongs:
            if len(chosen) == 3:
                break
            name = resolve(name)  # raises for a misconception nobody declared
            if chash(value) in seen_values or text.strip() in seen_texts:
                continue
            if not allow_repeat and name in {c[0] for c in chosen}:
                continue
            chosen.append((name, value, text))
            seen_values.add(chash(value))
            seen_texts.add(text.strip())
    if len(chosen) < 3:
        return "fewer_than_three_distinct_named_wrongs"
    if len(draft.hints) != 3:
        raise ValueError("three hints needed")
    if any(_hint_leaks(h, draft) for h in draft.hints):
        return "hint_contains_the_answer"
    options: list[dict[str, Any]] = [
        {"id": "key", "value": draft.answer, "text": draft.key_text, "procedure": "correct"}
    ]
    for i, (name, value, text) in enumerate(chosen, start=1):
        options.append({"id": f"d{i}", "value": value, "text": text, "procedure": name})
    item_id = f"ITM.{model.skill}.{draft.variant}.{digest(params)}"
    return Built(model, draft, item_id, options)


def numeric_draft(
    *,
    variant: str,
    bio: dict[str, Any],
    coeff: Fraction,
    const: Fraction,
    value: Fraction,
    unit: str,
    stem: str,
    hints: list[str],
    steps: list[str],
    wrongs: Sequence[tuple[str, Fraction]],
    difficulty: float = 0.4,
    role: str = "apply",
    prediction: str = "Before you work it out, roughly what size of answer do you expect?",
    features: Sequence[str] = (),
) -> Draft | str:
    """A numeric item: kernel relation coeff * x = const, answer value (with unit), named wrongs."""
    value = Fraction(value)
    text = dec(value)
    if value <= 0 or text is None:
        return "answer_is_not_a_clean_positive_number"
    options = []
    for name, wrong in wrongs:
        wrong = Fraction(wrong)
        if wrong <= 0 or dec(wrong) is None or wrong == value:
            continue
        options.append((name, number_answer(wrong, unit), num_text(wrong, unit)))
    return Draft(
        variant=variant,
        spec=algebra_spec("x", coeff, const, bio),
        answer=number_answer(value, unit),
        witness={"values": {"x": qs(value)}},
        stem=stem,
        hints=hints,
        steps=steps,
        key_text=num_text(value, unit),
        wrongs=options,
        difficulty=difficulty,
        role=role,
        prediction=prediction,
        tokens=[text],
        features=list(features),
    )
