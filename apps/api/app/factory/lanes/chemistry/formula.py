"""Chemical formula helpers for the chemistry lane (own code; the kernel parser is not imported).

`atoms` reads a formula with one stack and a tokeniser. `atoms_expanded` is a second, different
route (rewrite every bracket as repeated text, then count), used as the independent method in the
atom-counting family. Neither is trusted by the kernel.
"""

from __future__ import annotations

import re
from collections import Counter

_TOKEN = re.compile(r"([A-Z][a-z]?)(\d*)|(\()|\)(\d*)")
_WHOLE = re.compile(r"(?:[A-Z][a-z]?\d*|\(|\)\d*)+")
_INNER = re.compile(r"\(([A-Za-z0-9]*)\)(\d*)")


def atoms(formula: str) -> dict[str, int]:
    if not _WHOLE.fullmatch(formula):
        raise ValueError(f"bad formula {formula!r}")
    stack: list[Counter[str]] = [Counter()]
    for match in _TOKEN.finditer(formula):
        symbol, digits, opening = match.group(1), match.group(2), match.group(3)
        if symbol:
            stack[-1][symbol] += int(digits or 1)
        elif opening:
            stack.append(Counter())
        else:
            if len(stack) < 2:
                raise ValueError("unbalanced brackets")
            inner = stack.pop()
            times = int(match.group(4) or 1)
            for sym, n in inner.items():
                stack[-1][sym] += n * times
    if len(stack) != 1:
        raise ValueError("unbalanced brackets")
    return dict(stack[0])


def atoms_expanded(formula: str) -> dict[str, int]:
    text = formula
    while "(" in text:
        new = _INNER.sub(lambda m: m.group(1) * int(m.group(2) or 1), text)
        if new == text:
            raise ValueError("bad brackets")
        text = new
    if ")" in text:
        raise ValueError("bad brackets")
    out: Counter[str] = Counter()
    pos = 0
    for match in re.finditer(r"([A-Z][a-z]?)(\d*)", text):
        if match.start() != pos:
            raise ValueError("bad formula")
        out[match.group(1)] += int(match.group(2) or 1)
        pos = match.end()
    if pos != len(text):
        raise ValueError("bad formula")
    return dict(out)


def is_element(formula: str) -> bool:
    """True for a single-element formula such as Zn, O2, Cl2, P."""
    return len(atoms(formula)) == 1


def equation_text(
    left: list[str],
    right: list[str],
    coeffs: list[int] | None = None,
) -> str:
    """`2 H2 + O2 → 2 H2O`. coeffs None prints bare formulas."""
    species = left + right
    cs = coeffs if coeffs is not None else [1] * len(species)

    def one(i: int) -> str:
        return species[i] if cs[i] == 1 else f"{cs[i]} {species[i]}"

    lhs = " + ".join(one(i) for i in range(len(left)))
    rhs = " + ".join(one(i) for i in range(len(left), len(species)))
    return f"{lhs} → {rhs}"
