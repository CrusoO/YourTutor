# ruff: noqa: E501
"""Shared plumbing for the Class 10 chemistry lane: what a family returns, methods, helpers.

A FAMILY is one question model (for example "balance a reaction from a closed table"). It builds an
item from a parameter tuple and returns a `Built` record; the lane turns that into an ItemContext
for the factory pipeline. Everything the lane writes is DATA: only the kernel mints certificates.

Balance and mass families go to the kernel's stoichiometry verifier. Everything else is encoded as
an exact linear relation (the algebra domain), which proves the key satisfies that relation; the
independent Methods then recompute the answer from the spec alone, and a disagreement is never
outvoted.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from app.content.language import lint_item_texts
from app.content.leak import hint_leaks_answer


class IllPosed(Exception):  # noqa: N818 - a refusal reason, not an error
    """The parameter tuple does not make a good item. The message is the counted reason."""


@dataclass
class Built:
    spec: dict[str, Any]
    answer: dict[str, Any]
    witness: dict[str, Any]
    stem: str
    steps: list[str]
    hints: list[str]
    # (misconception id, answer record, option text), in priority order; the lane takes the first
    # three whose records and texts differ from the key and from each other.
    wrong: list[tuple[str, dict[str, Any], str]]
    key_text: str
    tokens: list[str]
    difficulty: float
    role: str
    prediction: str
    methods: list[Any]
    slug: str
    tags: list[str] = field(default_factory=list)


class FnMethod:
    """An independent method: a pure function of the spec. Deep-copyable (fault injection)."""

    def __init__(
        self,
        id: str,  # noqa: A002
        group: str,
        technique: str,
        fn: Callable[[Mapping[str, Any]], Any],
    ) -> None:
        self.id, self.version, self.independence_group, self.technique = id, "1", group, technique
        self.fn = fn

    def solve(self, spec: Mapping[str, Any]) -> Any:
        return self.fn(spec)


class Family:
    id = ""
    version = "1"

    def build(self, tpl: Mapping[str, Any], p: Mapping[str, Any]) -> Built:  # pragma: no cover
        raise NotImplementedError


# ---------------------------------------------------------------- kernel encodings


def linear_spec(
    var: str, coeff: int | str, const: int | str, chem: dict[str, Any]
) -> dict[str, Any]:
    """One unknown, one exact equation `coeff * var = const`, plus the chemistry payload."""
    return {
        "domain": "algebra",
        "kind": "linear_system",
        "variables": [var],
        "equations": [{"coeffs": [str(coeff)], "const": str(const)}],
        "chem": chem,
    }


def linear_answer(var: str, value: int | str) -> dict[str, Any]:
    return {"values": {var: str(value)}}


def balance_spec(
    left: list[str], right: list[str], chem: dict[str, Any] | None = None
) -> dict[str, Any]:
    species = [{"formula": f, "side": "L"} for f in left] + [
        {"formula": f, "side": "R"} for f in right
    ]
    spec: dict[str, Any] = {"domain": "stoichiometry", "kind": "balance", "species": species}
    if chem is not None:
        spec["chem"] = chem
    return spec


# ---------------------------------------------------------------- text helpers

_LETTER = re.compile(r"option\s+[a-d]", re.IGNORECASE)


def hint_problems(stem: str, hints: list[str], tokens: list[str]) -> str | None:
    """Lane-side lint, so a bad text is a counted refusal and never a silent pass."""
    if len(hints) != 3:
        return "needs_three_hints"
    for hint in hints[:2]:
        if _LETTER.search(hint):
            return "hint_names_an_option_letter"
    errors, _ = lint_item_texts(stem=stem, hints=hints)
    if errors:
        return "language_lint:" + errors[0].split(" ")[0]
    for hint in hints[:2]:
        for token in tokens:
            if hint_leaks_answer(hint, token):
                return "hint_would_leak_key"
    return None


def distinct_wrong(
    key: dict[str, Any],
    key_text: str,
    wrong: list[tuple[str, dict[str, Any], str]],
    chash: Callable[[Any], str],
) -> list[tuple[str, dict[str, Any], str]]:
    """First three candidates that differ from the key and from each other (record and text)."""
    seen_rec, seen_txt = {chash(key)}, {key_text}
    picked: list[tuple[str, dict[str, Any], str]] = []
    for mc, rec, text in wrong:
        h = chash(rec)
        if h in seen_rec or text in seen_txt:
            continue
        seen_rec.add(h)
        seen_txt.add(text)
        picked.append((mc, rec, text))
        if len(picked) == 3:
            break
    return picked


def name_tokens(name: str) -> list[str]:
    """Tokens a hint must not contain. Locant lists such as 2,2- are dropped: the leak checker cannot read them."""
    if re.search(r"\d,\d", name):
        return [re.sub(r"^[\d,]+-", "", name)]
    return [name]


def pick(variants: list[str], p: Mapping[str, Any]) -> str:
    """A deterministic variant of a phrase from the parameters (never random)."""
    key = int(hashlib.sha256(repr(sorted(p.items())).encode()).hexdigest()[:8], 16)
    return variants[key % len(variants)]


def difficulty(base: float, steps: int = 0, size: int = 0) -> float:
    return round(min(0.95, max(0.05, base + 0.03 * steps + 0.01 * size)), 3)
