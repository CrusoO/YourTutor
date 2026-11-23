# ruff: noqa: E501
"""The Class 10 maths catalog: every template, skill, misconception and overlay in one place.

`python -m app.factory.lanes.maths.emit --root <content/cbse/10/maths>` writes the YAML files from
this catalog (skills, templates, misconceptions, overlays). Stamped items are written only by the
factory CLI. A test compares the files on disk with this catalog so they cannot drift.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.factory.kernel.certify import box_axes
from app.factory.kernel.exact import chash
from app.factory.lanes.maths import catalog_ap, catalog_lin2, catalog_quad, catalog_trig
from app.factory.lanes.maths.core import IllPosed, distinct_wrong

# The lane's chapter refs (kept: they sit inside every template hash and certificate) name chapters
# by book number. A student reaches a chapter through the curriculum registry, whose overlay ids
# are below; chapters without an entry have no curriculum chapter yet and keep their own id.
OVERLAY_IDS: dict[str, str] = {
    "cbse.10.maths.ch04": "cbse.10.maths.quadratic",
    "cbse.10.maths.ch05": "cbse.10.maths.ap",
    "cbse.10.maths.ch11": "cbse.10.maths.trig_applications",
}

CHAPTERS: dict[str, dict[str, str]] = {
    "cbse.10.maths.ch03": {"key": "pair_of_linear_equations",
                           "title": "Pair of Linear Equations in Two Variables"},
    "cbse.10.maths.ch04": {"key": "quadratic_equations", "title": "Quadratic Equations"},
    "cbse.10.maths.ch05": {"key": "arithmetic_progressions", "title": "Arithmetic Progressions"},
    "cbse.10.maths.ch09": {"key": "introduction_to_trigonometry",
                           "title": "Introduction to Trigonometry"},
    "cbse.10.maths.ch10": {"key": "trigonometric_identities", "title": "Trigonometric Identities"},
    "cbse.10.maths.ch11": {"key": "heights_and_distances",
                           "title": "Heights and Distances (Some Applications of Trigonometry)"},
}  # fmt: skip

# Class 8 and 9 skills the Class 10 graph depends on. Stubs: no items, status draft.
PREREQUISITES: list[tuple[str, str, list[int], list[str]]] = [
    ("MATH.ARITH.INTEGERS.OPERATIONS", "Add, subtract, multiply and divide integers", [8, 9], []),
    ("MATH.ARITH.SQUARES_ROOTS", "Use squares, square roots and perfect squares", [8], []),
    ("MATH.ARITH.FRACTIONS_SIMPLIFY", "Simplify and compare fractions", [8], []),
    (
        "MATH.ARITH.SPEED_DISTANCE_TIME",
        "Use speed, distance and time together",
        [8],
        ["MATH.ARITH.FRACTIONS_SIMPLIFY"],
    ),
    (
        "MATH.ALG.INVERSE_OPERATIONS",
        "Undo an operation by doing the same inverse operation to both sides",
        [8, 9],
        ["MATH.ARITH.INTEGERS.OPERATIONS"],
    ),
    (
        "MATH.ALG.SUBSTITUTE",
        "Substitute numbers into an expression",
        [8, 9],
        ["MATH.ARITH.INTEGERS.OPERATIONS"],
    ),
    (
        "MATH.ALG.LIN1.SOLVE_TWO_STEP",
        "Solve a two-step linear equation",
        [8, 9],
        ["MATH.ALG.INVERSE_OPERATIONS"],
    ),
    (
        "MATH.ALG.LIN1.WORD_PROBLEMS",
        "Turn a word problem into a linear equation and solve it",
        [9],
        ["MATH.ALG.LIN1.SOLVE_TWO_STEP"],
    ),
    (
        "MATH.ALG.LIN2.SOLVE_PAIR",
        "Solve two linear equations in two unknowns",
        [9, 10],
        ["MATH.ALG.LIN1.SOLVE_TWO_STEP"],
    ),
    (
        "MATH.ALG.EXPAND_BRACKETS",
        "Multiply out brackets and collect like terms",
        [8, 9],
        ["MATH.ARITH.INTEGERS.OPERATIONS"],
    ),
    (
        "MATH.ALG.FACTORISE_COMMON",
        "Factorise by taking out a common factor",
        [8, 9],
        ["MATH.ALG.EXPAND_BRACKETS"],
    ),
    (
        "MATH.NUM.PATTERNS_RULES",
        "Describe a number pattern with a rule",
        [8, 9],
        ["MATH.ARITH.INTEGERS.OPERATIONS"],
    ),
    (
        "MATH.NUM.SURDS_SIMPLIFY",
        "Simplify square roots and surds",
        [9],
        ["MATH.ARITH.SQUARES_ROOTS"],
    ),
    (
        "MATH.GEO.PYTHAGORAS_USE",
        "Use the relation between the three sides of a right triangle",
        [8, 9],
        ["MATH.ARITH.SQUARES_ROOTS"],
    ),
    (
        "MATH.GEO.RIGHT_TRIANGLE_SIDES",
        "Name the hypotenuse and the sides opposite and next to an angle",
        [9],
        [],
    ),
    ("MATH.GEO.ALTERNATE_ANGLES", "Use alternate angles on parallel lines", [9], []),
]


def all_templates() -> list[dict[str, Any]]:
    from app.factory.lanes.maths.lane import FAMILIES

    out = [
        *catalog_quad.TEMPLATES,
        *catalog_ap.TEMPLATES,
        *catalog_trig.TEMPLATES,
        *catalog_lin2.TEMPLATES,
    ]
    for t in out:  # the template records the generator version it was written for
        t["family_version"] = FAMILIES[t["family"]].version
    return out


def skills_of_chapter(chapter: str) -> list[str]:
    seen: list[str] = []
    for t in all_templates():
        if t["syllabus"]["chapter_ref"] == chapter and t["skill_id"] not in seen:
            seen.append(t["skill_id"])
    return seen


def skill_records() -> list[dict[str, Any]]:
    """Every skill (Class 10 and the prerequisite stubs) as plain dicts, misconceptions filled in
    from what the families actually generate."""
    used = used_misconceptions()
    out: list[dict[str, Any]] = []

    def record(sid: str, title: str, band: list[int], prereq: list[str]) -> dict[str, Any]:
        return {
            "id": sid,
            "title": {"en": title},
            "grade_band": band,
            "subject": "math",
            "prerequisites": prereq,
            "related": [],
            "misconceptions": sorted(used.get(sid, [])),
            "bkt": {"p_init": 0.2, "p_learn": 0.15, "p_slip": 0.1, "p_guess": 0.25},
            "status": "draft",
        }

    for suffix, title, band, prereq, _ in catalog_quad.SKILLS:
        out.append(record(catalog_quad.P + suffix, title, band, prereq))
    for suffix, title, band, prereq, _ in catalog_ap.SKILLS:
        out.append(record(catalog_ap.P + suffix, title, band, prereq))
    for sid, title, band, prereq in catalog_trig.SKILLS:
        out.append(record(sid, title, band, prereq))
    for suffix, title, band, prereq, _ in catalog_lin2.SKILLS:
        out.append(record(catalog_lin2.P + suffix, title, band, prereq))
    stubs = [record(sid, title, band, prereq) for sid, title, band, prereq in PREREQUISITES]
    return [*out, *stubs]


def used_misconceptions() -> dict[str, set[str]]:
    """Misconception ids the families really put on options, per skill (scans every box)."""
    from app.factory.lanes.maths.lane import LANE

    found: dict[str, set[str]] = defaultdict(set)
    for t in all_templates():
        axes = box_axes(t["box"])
        total = 1
        for _, vals in axes:
            total *= len(vals)
        step = max(1, total // 4000)
        for index in range(0, total, step):
            params: dict[str, Any] = {}
            rest = index
            for name, vals in reversed(axes):
                rest, pos = divmod(rest, len(vals))
                params[name] = vals[pos]
            try:
                built = LANE._build(t, params)  # type: ignore[attr-defined]
            except IllPosed:
                continue
            for mc, _, _ in distinct_wrong(built.answer, built.key_text, built.wrong, chash):
                found[t["skill_id"]].add(mc)
    return dict(found)


def overlay_records() -> list[dict[str, Any]]:
    out = []
    for ref, info in CHAPTERS.items():
        out.append(
            {
                "id": OVERLAY_IDS.get(ref, ref),
                "curriculum_id": "cbse",
                "grade": 10,
                "chapter": info["key"],
                "skill_ids": skills_of_chapter(ref),
                "live": False,
                "section_map": {},
            }
        )
    return out
