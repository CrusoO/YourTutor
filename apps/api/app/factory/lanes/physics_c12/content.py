# ruff: noqa: E501
"""Skill graph, misconceptions, overlays and template files for Class 12 physics numericals.

All titles and explanations are original wording. Only syllabus FACTS (chapter and topic names)
are used as input. Everything is `status: draft`; nothing here is reviewed by a person.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.factory.lanes.physics_c12.kit import (
    CHAPTER_TITLES,
    CHAPTERS,
    GRADE,
    MC_PREFIX,
    TITLES,
    chapter_id,
)
from app.factory.lanes.physics_c12.models import ALL_MODELS
from app.factory.lanes.physics_c12.templates import TEMPLATES

BKT = {"p_init": 0.3, "p_learn": 0.15, "p_slip": 0.1, "p_guess": 0.25}
P = "PHY.C12.PREREQ."

# (id, title, grade band) -- prerequisite stubs from Classes 8 to 11
PREREQS: list[tuple[str, str, list[int]]] = [
    (P + "SCI_NOTATION", "Read and compute with numbers written with powers of ten", [9, 10]),
    (
        P + "REARRANGE_FORMULA",
        "Rearrange a formula by doing the same operation to each side",
        [8, 9],
    ),
    (
        P + "UNIT_PREFIXES",
        "Change between a unit and its milli, micro, kilo and mega forms",
        [8, 9],
    ),
    (P + "RECIPROCALS", "Add fractions and take the reciprocal of a sum", [8, 9]),
    (P + "SERIES_RESISTORS", "Add resistances that are joined end to end", [10]),
    (P + "PARALLEL_RESISTORS", "Combine resistances that share both ends", [10]),
    (P + "RATIO_PROPORTION", "Direct and inverse proportion as a ratio", [8, 9]),
    (P + "RIGHT_TRIANGLES", "Use the square of the longest side of a right triangle", [9, 10]),
    (P + "LENS_BASICS", "Focal length, radius of curvature and the thin lens in Class 10", [10]),
    (P + "POWERS_OF_TWO", "Powers of two and halving a number again and again", [8, 9]),
    (P + "COUNTING_RULES", "Count the ways n choices can each be one of two values", [9, 10]),
]

# a misconception with a specific wording; every other one gets a pattern text (see _pattern)
_TEXT: dict[str, tuple[str, str]] = {
    "FORMULA_INVERTED": (
        "Uses the relation upside down",
        "You may have divided the wrong way round. Check which quantity belongs on top.",
    ),
    "MULTIPLIED_NOT_DIVIDED": (
        "Multiplies where the relation divides",
        "You may have multiplied when you should divide.",
    ),
    "DIVIDED_NOT_MULTIPLIED": (
        "Divides where the relation multiplies",
        "You may have divided when you should multiply.",
    ),
    "UNIT_PREFIX_SLIP": (
        "Slips by a power of ten between a unit and its prefixed form",
        "You may have forgotten to change the unit, so the answer is out by a power of ten.",
    ),
    "POWER_OF_TEN_SLIP": (
        "Slips by a power of ten",
        "You may have slipped on a power of ten somewhere in the calculation.",
    ),
    "DISTANCE_NOT_SQUARED": (
        "Uses the distance once where the law needs its square",
        "You may have written r where the inverse square law needs r squared.",
    ),
    "ROOT_FORGOTTEN": (
        "Stops before the square root",
        "You may have stopped one step early. The last step is the square root.",
    ),
    "SINE_FORGOTTEN": (
        "Leaves out the sine of the angle",
        "You may have dropped sin(angle) from the relation. The angle matters.",
    ),
    "SERIES_RULE_USED": (
        "Uses the series rule for a parallel connection",
        "You may have used the rule for the other connection.",
    ),
    "PARALLEL_RULE_USED": (
        "Uses the parallel rule for a series connection",
        "You may have used the rule for the other connection.",
    ),
    "HALF_FORGOTTEN": (
        "Leaves out the one half",
        "You may have dropped the factor one half from the formula.",
    ),
    "FORGOT_FINAL_RECIPROCAL": (
        "Stops before the final reciprocal",
        "You may have added the fractions but forgot to flip the total.",
    ),
    "INTERNAL_RESISTANCE_IGNORED": (
        "Ignores the internal resistance of the cell",
        "You may have used only the outside resistor. The cell has resistance too.",
    ),
    "EMF_TAKEN_AS_TERMINAL": (
        "Takes the emf as the terminal voltage",
        "You may have forgotten the voltage lost inside the cell while it supplies a current.",
    ),
    "TURNS_RATIO_INVERTED": (
        "Turns the ratio of turns upside down",
        "You may have put the turns of the wrong coil on top.",
    ),
    "VOLTAGE_RATIO_USED_FOR_CURRENT": (
        "Uses the voltage ratio for the current",
        "You may have used the voltage ratio. In an ideal transformer the current ratio is the opposite of the voltage ratio.",
    ),
    "WORK_FUNCTION_ADDED": (
        "Adds the work function to the photon energy",
        "You may have added where the electron loses the work function.",
    ),
    "WORK_FUNCTION_IGNORED": (
        "Ignores the work function",
        "You may have used the whole photon energy as the kinetic energy.",
    ),
    "QUANTUM_NUMBER_NOT_SQUARED": (
        "Uses n where the model needs n squared",
        "You may have used n once. The energy and the radius depend on n squared.",
    ),
    "REACTANCES_ADDED_TO_RESISTANCE": (
        "Adds resistance and reactance like plain resistances",
        "You may have added R and the reactances directly. They combine as the sides of a right triangle.",
    ),
    "HALVED_ONCE_ONLY": (
        "Halves only once",
        "You may have halved the sample one time. It halves once in every half-life.",
    ),
    "RECIPROCAL_FORGOTTEN": (
        "Forgets the reciprocal",
        "You may have left out the 1 over the product, or the final flip.",
    ),
    "COSINE_NOT_SQUARED": (
        "Uses the cosine once where Malus's law needs its square",
        "You may have used cos(angle) without squaring it.",
    ),
    "TOTAL_CURRENT_USED": (
        "Divides by the whole current instead of the shunt current",
        "You may have divided by the whole current. The shunt carries only the extra current, the total minus the galvanometer current.",
    ),
}


def _humanize(name: str) -> str:
    text = name.replace("_", " ").lower()
    return text[0].upper() + text[1:]


def _pattern(name: str) -> tuple[str, str]:
    title = _humanize(name)
    if name.endswith("UNIT_SLIP"):
        why = "You may have used a number without changing its unit first. Change every quantity to SI units before you substitute."
    elif name.endswith(("FORGOTTEN", "IGNORED", "LEFT_OUT")):
        why = "You may have left out a quantity or factor that the relation needs. Check that every symbol in the relation is used."
    elif "NOT_SQUARED" in name or name == "SQUARE_FORGOTTEN":
        why = "You may have used a quantity once where the relation needs its square."
    elif "SQUARED" in name or "CUBED" in name:
        why = "You may have raised to a power a quantity that the relation uses once."
    elif "ADDED" in name:
        why = "You may have added quantities that the relation combines in another way."
    elif "SUBTRACTED" in name:
        why = "You may have subtracted where the relation does not."
    elif name.endswith("COPIED") or name.endswith("ONLY") or name.endswith("ONLY_USED"):
        why = "You may have written down one given quantity as the answer. Use the relation that links all of them."
    elif (
        name.endswith(("_USED", "USED_AS_K", "USED_FOR_SUSCEPTIBILITY"))
        or "RULE" in name
        or "FORMULA" in name
    ):
        why = "You may have used a relation that belongs to a different situation. Check what each formula describes."
    elif "SWAPPED" in name or "INVERTED" in name or "RECIPROCAL" in name:
        why = (
            "You may have put two quantities in each other's places, or turned a ratio upside down."
        )
    elif "MULTIPLIED" in name:
        why = (
            "You may have multiplied quantities that the relation divides, or the other way round."
        )
    elif "DIVIDED" in name:
        why = "You may have divided quantities that the relation multiplies."
    else:
        why = "You may have slipped in this step. Compare each step with the relation and check the units."
    return title, why


def mc_name(mc_id: str) -> str:
    return mc_id.rsplit(".", 1)[1]


def used_misconceptions() -> dict[str, str]:
    """misconception id -> the first skill whose models use it (its remedial skill)."""
    out: dict[str, str] = {}
    for model in ALL_MODELS.values():
        for variant in model.variants.values():
            for mc, _ in variant.wrongs:
                out.setdefault(mc, model.skill)
        out.setdefault(f"{MC_PREFIX}.UNIT_PREFIX_SLIP", model.skill)
        out.setdefault(f"{MC_PREFIX}.POWER_OF_TEN_SLIP", model.skill)
    return out


def skill_misconceptions(skill_id: str) -> list[str]:
    ids: set[str] = set()
    for model in ALL_MODELS.values():
        if model.skill == skill_id:
            ids = {mc for v in model.variants.values() for mc, _ in v.wrongs}
            ids |= {f"{MC_PREFIX}.UNIT_PREFIX_SLIP", f"{MC_PREFIX}.POWER_OF_TEN_SLIP"}
    return sorted(ids)


def skill_docs() -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for sid, title, grades in PREREQS:
        docs.append({"id": sid, "title": {"en": title}, "grade_band": grades, "subject": "physics",
                     "prerequisites": [], "misconceptions": [], "bkt": BKT, "status": "draft"})  # fmt: skip
    for model in ALL_MODELS.values():
        title, prereqs = TITLES[model.id]
        docs.append({"id": model.skill, "title": {"en": title}, "grade_band": [GRADE], "subject": "physics",
                     "prerequisites": list(prereqs), "misconceptions": skill_misconceptions(model.skill),
                     "bkt": BKT, "status": "draft"})  # fmt: skip
    return docs


def misconception_docs() -> list[dict[str, Any]]:
    docs = []
    for mc, skill in sorted(used_misconceptions().items()):
        title, expl = _TEXT.get(mc_name(mc)) or _pattern(mc_name(mc))
        docs.append({"id": mc, "title": {"en": title}, "explanation": {"en": expl},
                     "remedial_skill": skill, "status": "draft"})  # fmt: skip
    return docs


def overlay_docs() -> list[dict[str, Any]]:
    out = []
    for area, key in CHAPTERS.items():
        skills = [m.skill for m in ALL_MODELS.values() if m.chapter == chapter_id(area)]
        out.append({"id": chapter_id(area), "curriculum_id": "cbse", "grade": GRADE, "chapter": key,
                    "skill_ids": skills, "live": False, "section_map": {}})  # fmt: skip
    return out


def curriculum_entry() -> str:
    """The curriculum book entry (append-only text for content/curricula/cbse/curriculum.yaml)."""
    first = chapter_id(next(iter(CHAPTERS)))
    lines = [
        f"  - id: cbse.{GRADE}.physics",
        f"    grade: {GRADE}",
        "    subject: physics",
        f"    default_chapter_id: {first}",
        "    chapters:",
    ]
    for area, key in CHAPTERS.items():
        cid = chapter_id(area)
        lines += [
            f"      - id: {cid}",
            f"        overlay_id: {cid}",
            f"        chapter_key: {key}",
            f'        titles: {{en: "{CHAPTER_TITLES[area]}"}}',
        ]
    return "\n".join(lines) + "\n"


def _dump(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8",
                    newline="\n")  # fmt: skip


def template_path(root: Path, template_id: str) -> Path:
    return root / "factory" / "templates" / f"{template_id}.yaml"


def write_content(root: Path) -> dict[str, int]:
    """Write skills, misconceptions, overlays and templates under `root` (idempotent)."""
    for doc in skill_docs():
        _dump(root / "skills" / f"{doc['id'].lower()}.yaml", doc)
    for doc in misconception_docs():
        _dump(root / "misconceptions" / f"{doc['id'].lower()}.yaml", doc)
    for doc in overlay_docs():
        _dump(root / "overlays" / f"{doc['id']}.yaml", doc)
    for tpl in TEMPLATES.values():
        _dump(template_path(root, tpl["id"]), tpl)
    return {"skills": len(PREREQS) + len(ALL_MODELS), "misconceptions": len(misconception_docs()),
            "overlays": len(CHAPTERS), "templates": len(TEMPLATES)}  # fmt: skip
