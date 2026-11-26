"""facts: rule-based extraction of constants, formulas and defined terms from book text.

Limits: this reads text lines, not layout. Superscripts and fractions that the PDF stores as
separate glyphs are lost or garbled, so a value like 10 to the power -19 may be missed or read
wrong. Only a number followed by a known unit, shortly after a keyword, counts as a constant.
Formulas are short lines of the form `X = Y`. Defined terms use three fixed phrases. Expect gaps
(nothing from diagrams, tables or images) and some noise; this is a first filter, not a database.
"""

from __future__ import annotations

import re
from typing import Any

from app.bookcheck.settings import Settings
from app.bookcheck.store import iter_pages, load_books, write_json
from app.bookcheck.text import snippet

KEYWORDS = (
    "value", "speed", "velocity", "charge", "mass", "acceleration", "density", "gravity",
    "constant", "wavelength", "frequency", "temperature", "resistance", "voltage", "pressure",
    "energy", "force", "weight", "height", "distance", "time", "current", "power",
)  # fmt: skip
UNITS = (
    "m/s2", "m/s^2", "m/s", "km/h", "kg/m3", "kg/m^3", "g/cm3", "g/cm^3", "J/kg", "N/m2",
    "kg", "mg", "cm", "mm", "km", "ms", "min", "Hz", "Pa", "mol", "ohm", "ml", "mL", "kJ",
    "kWh", "eV", "amu", "K", "N", "J", "W", "V", "A", "C", "m", "s", "g", "L", "h", "%", "°C",
)  # fmt: skip
_UNIT_RE = "|".join(re.escape(u) for u in sorted(UNITS, key=len, reverse=True))
NUMBER = r"[-+−]?\d+(?:\.\d+)?(?:\s*(?:x|×|\*)\s*10\s*\^?\s*[-−–]?\d+)?"
CONST = re.compile(rf"(?P<num>{NUMBER})\s*(?P<unit>{_UNIT_RE})(?![\w])")
KEYWORD_RE = re.compile(r"\b(" + "|".join(KEYWORDS) + r")\b|\b(g)\s*=\s*$", re.I)
GENERIC = frozenset({"value", "constant"})  # on many lines; never enough to match
SCI = re.compile(r"^([-+−]?\d+(?:\.\d+)?)\s*(?:x|×|\*)\s*10\s*\^?\s*([-−–]?\d+)$")
FORMULA = re.compile(
    r"^\s*([A-Za-z][A-Za-z0-9_]{0,10}(?:\s*[-+*/]\s*[A-Za-z0-9]+)?)\s*=\s*(.{1,40})$"
)
DEFINED = re.compile(
    r"(?P<term>[A-Za-z][A-Za-z \-]{2,50}?)\s+(?:is defined as|is called|is known as)\s+(?P<rest>.{3,120})",  # noqa: E501
    re.I,
)
WINDOW = 60  # characters before a number searched for a keyword


def parse_number(raw: str) -> float | None:
    raw = raw.replace("−", "-").replace("–", "-").strip()
    sci = SCI.match(raw)
    try:
        if sci:
            return float(sci.group(1)) * 10 ** int(sci.group(2))
        return float(raw)
    except ValueError:
        return None


def norm_unit(unit: str) -> str:
    return unit.replace("^", "").replace("²", "2").replace("³", "3")


def extract_consts(text: str) -> list[dict[str, Any]]:
    """Numbers with units that follow a keyword, from free text (a book line or our item)."""
    found = []
    for match in CONST.finditer(text):
        before = text[max(0, match.start() - WINDOW) : match.start()]
        hits = list(KEYWORD_RE.finditer(before))
        if not hits:
            continue
        found_words = [(h.group(1) or h.group(2)).casefold() for h in hits]
        keyword = found_words[-1]
        value = parse_number(match.group("num"))
        if value is None:
            continue
        found.append(
            {
                "keyword": keyword,
                "keywords": sorted(set(found_words) - GENERIC),
                "value": value,
                "unit": norm_unit(match.group("unit")),
            }
        )
    return found


def extract_page(page: int, text: str) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            continue
        for const in extract_consts(line):
            facts.append({"kind": "const", "page": page, "snippet": snippet(line), **const})
        formula = FORMULA.match(line)
        if formula and len(line.split()) <= 10:
            facts.append({"kind": "formula", "page": page, "snippet": snippet(line)})
        defined = DEFINED.search(line)
        if defined:
            facts.append(
                {
                    "kind": "term",
                    "page": page,
                    "term": defined.group("term").strip().casefold(),
                    "snippet": snippet(line),
                }
            )
    return facts


def run_facts(settings: Settings) -> dict[str, int]:
    counts = {"books": 0, "constants": 0, "formulas": 0, "terms": 0}
    for book in load_books(settings):
        facts: list[dict[str, Any]] = []
        for page, text in iter_pages(settings, book.sha):
            facts.extend(extract_page(page, text))
        write_json(
            settings.out_dir / "facts" / f"{book.sha}.json", {"sha": book.sha, "facts": facts}
        )
        counts["books"] += 1
        for fact in facts:
            key = {"const": "constants", "formula": "formulas", "term": "terms"}[fact["kind"]]
            counts[key] += 1
    return counts
