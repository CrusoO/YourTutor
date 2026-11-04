"""Layer 1 of distress detection: a deterministic lexicon (English, Hindi, Hinglish).

Pure and offline. The text is normalised first (lowercase, zero-width characters removed, digits
and symbols used as letters mapped, repeated letters collapsed, punctuation dropped), then looked
up as whole-word phrases. The lexicon is data in `config/distress_lexicon.yaml`. See that file for
the phrase syntax and the review status of the Hindi and Hinglish lists (draft: not yet reviewed
by a native speaker).

Nothing here logs or stores the text it is given.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from app.registries.paths import config_dir

URGENT = "urgent"
CONCERN = "concern"
NONE = "none"

_ZERO_WIDTH = re.compile("[​-‏‪-‮⁠-⁤﻿­͏]")
_SYMBOL_AS_LETTER = {"@": "a", "$": "s", "!": "i"}
_SYMBOL_BETWEEN_LETTERS = re.compile(r"(?<=[a-z])[@$!](?=[a-z])")
_DIGIT_TOKEN = re.compile(r"(?=[^\s]*[a-z])(?=[^\s]*\d)[^\s]+")
_DIGITS = {"0": "o", "3": "e", "4": "a", "5": "s", "7": "t"}
_SPACED_LETTERS = re.compile(r"(?<![^\W\d_])(?:[^\W\d_] ){2,}[^\W\d_](?![^\W\d_])")
_REPEATS = re.compile(r"(.)\1+")
_NUKTA = "़"
_CHANDRABINDU = "ँ"
_ANUSVARA = "ं"


def _map_digits(token: str, one: str) -> str:
    return "".join({**_DIGITS, "1": one}.get(ch, ch) for ch in token)


def _digit_mapper(one: str) -> Callable[[re.Match[str]], str]:
    return lambda m: _map_digits(m.group(0), one)


def _clean(text: str) -> str:
    """Lowercase, no zero-width marks, Devanagari nukta and chandrabindu folded, no punctuation."""
    t = unicodedata.normalize("NFKC", text).lower()
    t = _ZERO_WIDTH.sub("", t)
    t = t.replace(_NUKTA, "").replace(_CHANDRABINDU, _ANUSVARA)
    t = _SYMBOL_BETWEEN_LETTERS.sub(lambda m: _SYMBOL_AS_LETTER[m.group(0)], t)
    t = t.replace("'", "").replace("’", "").replace("‘", "")
    out: list[str] = []
    for ch in t:
        cat = unicodedata.category(ch)
        # Letters, combining marks (Devanagari vowel signs) and digits stay; the rest is a gap.
        out.append(ch if cat[0] in "LMN" else " ")
    return " ".join("".join(out).split())


def _squeeze(t: str) -> str:
    return " ".join(_REPEATS.sub(r"\1", t).split())


def variants(text: str) -> tuple[str, ...]:
    """The normal forms of a text to look phrases up in (one, or a few when it is ambiguous)."""
    cleaned = _clean(text)
    forms = {cleaned}
    if _DIGIT_TOKEN.search(cleaned):
        for one in ("i", "l"):
            forms.add(_DIGIT_TOKEN.sub(_digit_mapper(one), cleaned))
    joined = {_SPACED_LETTERS.sub(lambda m: m.group(0).replace(" ", ""), f) for f in forms}
    return tuple(sorted({_squeeze(f) for f in forms | joined}))


def normalise(text: str) -> str:
    """The first normal form of a text (see `variants` for the full set used in matching)."""
    return variants(text)[0]


def _expand(pattern: str) -> list[str]:
    """`(a|b)` groups (nestable) expanded to every alternative; an empty alternative is allowed."""
    out: list[list[str]] = [[]]
    i = 0
    while i < len(pattern):
        if pattern[i] == "(":
            depth, j = 1, i + 1
            while depth:
                depth += {"(": 1, ")": -1}.get(pattern[j], 0)
                j += 1
            inner, options, level, start = pattern[i + 1 : j - 1], [], 0, 0
            for k, ch in enumerate(inner):
                level += {"(": 1, ")": -1}.get(ch, 0)
                if ch == "|" and level == 0:
                    options.append(inner[start:k])
                    start = k + 1
            options.append(inner[start:])
            choices = [x for opt in options for x in _expand(opt)]
            out = [prev + [c] for prev in out for c in choices]
            i = j
        else:
            for prev in out:
                prev.append(pattern[i])
            i += 1
    return ["".join(parts) for parts in out]


@dataclass(frozen=True)
class Detection:
    risk: str  # none | concern | urgent
    category: str = ""
    layer: int = 1


NO_RISK = Detection(NONE)


@dataclass(frozen=True)
class _Entry:
    category: str
    risk: str
    language: str


@dataclass(frozen=True)
class Lexicon:
    exact: dict[tuple[str, ...], _Entry]  # token tuple -> entry
    prefixes: tuple[tuple[tuple[str, ...], _Entry], ...]  # last token is a stem
    squashed: tuple[str, ...]
    max_tokens: int
    status: dict[str, str]
    phrase_count: int

    def match(self, text: str) -> Detection:
        best: _Entry | None = None
        for form in variants(text):
            tokens = tuple(form.split())
            hit = self._match_tokens(tokens)
            if hit is not None and (best is None or (hit.risk == URGENT and best.risk != URGENT)):
                best = hit
            if best is not None and best.risk == URGENT:
                break
        if best is None:
            glued = "".join(variants(text)[0].split())
            if any(s in glued for s in self.squashed):
                return Detection(URGENT, "suicide")
            return NO_RISK
        return Detection(best.risk, best.category)

    def _match_tokens(self, tokens: tuple[str, ...]) -> _Entry | None:
        found: _Entry | None = None
        n = len(tokens)
        for size in range(1, min(self.max_tokens, n) + 1):
            for start in range(n - size + 1):
                entry = self.exact.get(tokens[start : start + size])
                if entry is not None:
                    if entry.risk == URGENT:
                        return entry
                    found = found or entry
        for stem, entry in self.prefixes:
            k = len(stem)
            for start in range(n - k + 1):
                window = tokens[start : start + k]
                if window[:-1] == stem[:-1] and window[-1].startswith(stem[-1]):
                    if entry.risk == URGENT:
                        return entry
                    found = found or entry
        return found


def load_lexicon(root: Path | None = None) -> Lexicon:
    data = yaml.safe_load(((root or config_dir()) / "distress_lexicon.yaml").read_text("utf-8"))
    exact: dict[tuple[str, ...], _Entry] = {}
    prefixes: list[tuple[tuple[str, ...], _Entry]] = []
    count = 0
    for category, block in data["categories"].items():
        risk = str(block["risk"])
        for language in ("en", "hi", "hinglish"):
            entry = _Entry(category, risk, language)
            for raw in block.get(language, ()):
                for phrase in _expand(str(raw).strip()):
                    prefix = phrase.rstrip().endswith("*")
                    tokens = tuple(_squeeze(_clean(phrase.rstrip().rstrip("*"))).split())
                    if not tokens:
                        continue
                    count += 1
                    if prefix:
                        prefixes.append((tokens, entry))
                    else:
                        current = exact.get(tokens)
                        # An urgent reading of the same words beats a concern one.
                        if current is None or (risk == URGENT and current.risk != URGENT):
                            exact[tokens] = entry
    squashed = tuple("".join(_squeeze(_clean(str(s))).split()) for s in data.get("squashed", ()))
    return Lexicon(
        exact=exact,
        prefixes=tuple(sorted(set(prefixes), key=lambda p: (p[1].category, p[0]))),
        squashed=squashed,
        max_tokens=max((len(k) for k in exact), default=1),
        status={str(k): str(v) for k, v in (data.get("status") or {}).items()},
        phrase_count=count,
    )


@lru_cache(maxsize=1)
def default_lexicon() -> Lexicon:
    return load_lexicon()


def detect(text: str, lexicon: Lexicon | None = None) -> Detection:
    """Layer 1: the risk in a student's text, from the lexicon alone."""
    return (lexicon or default_lexicon()).match(text)
