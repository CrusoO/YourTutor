"""Plain-text maths: LaTeX a model still writes becomes text a student can read (x², (a)/(b))."""

from __future__ import annotations

import re

SUPERSCRIPTS = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
LATEX_WORDS = {
    "pm": "±", "neq": "≠", "ne": "≠", "leq": "≤", "le": "≤", "geq": "≥", "ge": "≥",
    "cdot": "·", "times": "×", "div": "÷", "pi": "π", "theta": "θ", "alpha": "α",
    "beta": "β", "gamma": "γ", "Delta": "Δ", "delta": "δ", "infty": "∞", "approx": "≈",
    "rightarrow": "→", "Rightarrow": "⇒", "to": "→", "ldots": "...", "dots": "...",
    "angle": "∠", "degree": "°", "circ": "°",
}  # fmt: skip

DELIMITERS = re.compile(r"\\[\[\]()]|\$\$|\$")
SIZING = re.compile(r"\\(?:left|right|big|Big|displaystyle)\b")
SPACING = re.compile(r"\\(?:qquad|quad)\b|\\[,;! ]")
KNOWN_WORDS = re.compile(
    r"\\(" + "|".join(sorted(LATEX_WORDS, key=len, reverse=True)) + r")(?![A-Za-z])"
)
FRACTION = re.compile(r"\\d?frac\{([^{}]*)\}\{([^{}]*)\}")
SQRT = re.compile(r"\\sqrt\{([^{}]*)\}")
TEXT = re.compile(r"\\(?:text|mathrm|mathbf|operatorname)\{([^{}]*)\}")
POWER = re.compile(r"\^\{?(-?\d+)\}?")
SUBSCRIPT = re.compile(r"_\{([^{}]*)\}")
COMMAND = re.compile(r"\\([A-Za-z]+)")


def _power(match: re.Match[str]) -> str:
    digits = match.group(1)
    if len(digits) == 1 and digits.isdigit():
        return digits.translate(SUPERSCRIPTS)
    return f"^({digits})"


def plain_math(text: str) -> str:
    text = DELIMITERS.sub("", text)
    text = SIZING.sub("", text)
    text = SPACING.sub(" ", text)
    text = KNOWN_WORDS.sub(lambda m: LATEX_WORDS[m.group(1)], text)
    text = SUBSCRIPT.sub(r"_\1", text)
    text = POWER.sub(_power, text)  # powers first, so roots and fractions have no inner braces
    for _ in range(4):  # nested fractions and roots
        text = FRACTION.sub(r"(\1)/(\2)", text)
        text = SQRT.sub(r"sqrt(\1)", text)
        text = TEXT.sub(r"\1", text)
    text = COMMAND.sub(r"\1", text)
    text = text.replace("{", "").replace("}", "").replace("\u2011", "-")
    return re.sub(r"[ \t]{2,}", " ", text)
