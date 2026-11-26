# ruff: noqa: E501
"""The Class 12 maths catalog: chapters, skills, misconceptions and overlays derived from the models.

`python -m app.factory.lanes.maths_c12.emit --root <content/cbse/12/maths>` writes the YAML files.
Stamped items are written only by the factory CLI. A test compares the files on disk with this
catalog so they cannot drift.
"""

from __future__ import annotations

import itertools
from collections import defaultdict
from typing import Any

from app.factory.kernel.certify import box_axes
from app.factory.kernel.exact import chash
from app.factory.lanes.maths.core import IllPosed, distinct_wrong
from app.factory.lanes.maths_c12.core import MODELS
from app.factory.lanes.maths_c12.template import all_templates

CH = "cbse.12.maths."
CHAPTERS: dict[str, dict[str, str]] = {
    CH + "relations_functions": {"key": "relations_functions", "title": "Relations and Functions"},
    CH + "inverse_trig": {"key": "inverse_trig", "title": "Inverse Trigonometric Functions"},
    CH + "matrices": {"key": "matrices", "title": "Matrices"},
    CH + "determinants": {"key": "determinants", "title": "Determinants"},
    CH + "continuity_differentiability": {"key": "continuity_differentiability", "title": "Continuity and Differentiability"},
    CH + "applications_derivatives": {"key": "applications_derivatives", "title": "Applications of Derivatives"},
    CH + "integrals": {"key": "integrals", "title": "Integrals"},
    CH + "applications_integrals": {"key": "applications_integrals", "title": "Applications of Integrals"},
    CH + "differential_equations": {"key": "differential_equations", "title": "Differential Equations"},
    CH + "vectors": {"key": "vectors", "title": "Vectors"},
    CH + "three_d_geometry": {"key": "three_d_geometry", "title": "Three Dimensional Geometry"},
    CH + "linear_programming": {"key": "linear_programming", "title": "Linear Programming"},
    CH + "probability": {"key": "probability", "title": "Probability"},
}  # fmt: skip

# Earlier-grade skills the Class 12 graph depends on. Stubs: no items, status draft.
PREREQUISITES: list[tuple[str, str, list[int], list[str]]] = [
    ("MATH.C12.PRE.INTEGER_ARITHMETIC", "Add, subtract, multiply and divide integers and fractions", [8, 9], []),
    ("MATH.C12.PRE.LINEAR_EQUATIONS", "Solve a linear equation in one unknown", [8, 9], ["MATH.C12.PRE.INTEGER_ARITHMETIC"]),
    ("MATH.C12.PRE.SETS_FUNCTIONS", "Describe sets, ordered pairs and simple functions", [11], ["MATH.C12.PRE.INTEGER_ARITHMETIC"]),
    ("MATH.C12.PRE.STANDARD_ANGLES", "Use the trigonometric ratios of 0, 30, 45, 60 and 90 degrees", [10], ["MATH.C12.PRE.INTEGER_ARITHMETIC"]),
    ("MATH.C12.PRE.DIFFERENTIATE_POWERS", "Differentiate a power of x and a sum of powers", [11], ["MATH.C12.PRE.LINEAR_EQUATIONS"]),
    ("MATH.C12.PRE.INTEGRATE_POWERS", "Integrate a power of x and a sum of powers", [11], ["MATH.C12.PRE.DIFFERENTIATE_POWERS"]),
    ("MATH.C12.PRE.COORDINATES_3D", "Place points and write vectors using three coordinates", [11], ["MATH.C12.PRE.INTEGER_ARITHMETIC"]),
    ("MATH.C12.PRE.FRACTIONS_PROBABILITY", "Find the probability of a simple event as a fraction", [9, 10], ["MATH.C12.PRE.INTEGER_ARITHMETIC"]),
]  # fmt: skip

# Within-lane prerequisite edges (model short name -> earlier model short names).
EXTRA_PREREQ: dict[str, list[str]] = {
    "DET.ADJOINT_ENTRY": ["DET.VALUE"], "DET.INVERSE_2X2": ["DET.VALUE"], "DET.SOLVE_SYSTEM": ["DET.VALUE", "MAT.PRODUCT"],
    "AOD.TANGENT_NORMAL": ["DIFF.POLY_AT"], "AOD.CUBIC_EXTREMA": ["DIFF.POLY_AT"], "DIFF.IMPLICIT_AT": ["DIFF.POLY_AT"],
    "AAI.AREA_CURVES": ["INT.DEFINITE_POLY"], "DE.PARTICULAR": ["INT.DEFINITE_POLY"],
    "ITF.TRIG_OF_INVERSE": ["ITF.PRINCIPAL"], "MAT.SYMMETRIC_UNKNOWN": ["MAT.PRODUCT"],
    "VEC.CROSS_TRIPLE": ["VEC.ANGLE_COS"], "GEO3D.POINT_PLANE": ["VEC.ANGLE_COS"], "RF.COMPOSE_AT": ["RF.COUNT_MAPS"],
}  # fmt: skip


def _slug(identifier: str) -> str:
    return identifier.lower().replace(".", "_")


def humanize(mc: str) -> tuple[str, str]:
    """A plain title and a kind explanation made from a misconception id (draft wording)."""
    words = mc.split(".")[-1].replace("_", " ").lower()
    title = words[0].upper() + words[1:]
    return title, f"This option matches a common slip: {words}. Go back to that step and check it."


def used_misconceptions() -> dict[str, set[str]]:
    """Misconception ids the models really put on options, per skill (scans every box)."""
    from app.factory.lanes.maths_c12.lane import LANE

    found: dict[str, set[str]] = defaultdict(set)
    for t in all_templates():
        axes = box_axes(t["box"])
        for combo in itertools.product(*[v for _, v in axes]):
            params = {n: c for (n, _), c in zip(axes, combo, strict=True)}
            try:
                built = LANE._build(t, params)  # type: ignore[attr-defined]
            except IllPosed:
                continue
            for mc, _, _ in distinct_wrong(built.answer, built.key_text, built.wrong, chash):
                found[t["skill_id"]].add(mc)
    return dict(found)


def skill_records() -> list[dict[str, Any]]:
    used = used_misconceptions()

    def record(
        sid: str, title: str, band: list[int], prereq: list[str], mcs: list[str]
    ) -> dict[str, Any]:
        return {
            "id": sid, "title": {"en": title}, "grade_band": band, "subject": "math",
            "prerequisites": prereq, "related": [], "misconceptions": sorted(mcs),
            "bkt": {"p_init": 0.2, "p_learn": 0.15, "p_slip": 0.1, "p_guess": 0.25}, "status": "draft",
        }  # fmt: skip

    out = []
    for short, spec in MODELS.items():
        pre = list(spec.prereq) + ["MATH.C12." + e for e in EXTRA_PREREQ.get(short, [])]
        out.append(record(spec.skill_id, spec.title, [12], pre, list(used.get(spec.skill_id, []))))
    out += [record(sid, title, band, pre, []) for sid, title, band, pre in PREREQUISITES]
    return out


def overlay_records() -> list[dict[str, Any]]:
    out = []
    for ref, info in CHAPTERS.items():
        skills = [s.skill_id for s in MODELS.values() if s.chapter == ref]
        out.append(
            {
                "id": ref,
                "curriculum_id": "cbse",
                "grade": 12,
                "chapter": info["key"],
                "skill_ids": skills,
                "live": False,
                "section_map": {},
            }
        )
    return out
