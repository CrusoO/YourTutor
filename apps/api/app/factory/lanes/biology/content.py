# ruff: noqa: E501
"""Skill graph, misconceptions, overlays and template files for the Class 10 biology lane.

All titles and explanations are original wording; only chapter names are syllabus facts. Everything
is `status: draft` and nothing here has been reviewed by a person.
"""

from __future__ import annotations

import functools
import itertools
from pathlib import Path
from typing import Any

import yaml

from app.factory.kernel.certify import box_axes
from app.factory.lanes.biology.common import AREA_OF_CHAPTER, CHAPTERS
from app.factory.lanes.biology.models import ALL_MODELS, MISC
from app.factory.lanes.biology.templates import all_templates

BKT = {"p_init": 0.3, "p_learn": 0.15, "p_slip": 0.1, "p_guess": 0.25}
CHAPTER_KEYS = {
    CHAPTERS["HERED"]: "heredity",
    CHAPTERS["ENV"]: "environment",
    CHAPTERS["REPRO"]: "reproduction",
    CHAPTERS["LIFE"]: "life_processes",
}
P = "BIO.PREREQ."
PREREQS: list[tuple[str, str, list[int]]] = [
    (P + "RATIO_FRACTION", "Write a ratio in lowest terms and a part as a fraction", [8, 9]),
    (
        P + "PROBABILITY_BASICS",
        "Probability as favourable outcomes out of all equally likely outcomes",
        [8, 9],
    ),
    (P + "POWERS", "Repeated multiplication and powers of a number", [8, 9]),
    (P + "PERCENT_OF", "Find a percentage or a tenth of a quantity", [8, 9]),
    (P + "RATE_UNITS", "Use a rate and change between hours and minutes", [8, 9]),
    (P + "READ_CHAIN", "Read a food chain as a line of who eats whom", [8, 9]),
    (P + "CELLS_DIVIDE", "Living things are made of cells, and cells divide", [8, 9]),
    (P + "INHERIT_BASICS", "Offspring get one allele for each gene from each parent", [8, 9]),
    (P + "FORMULA_ATOMS", "Read a chemical formula and count its atoms", [8, 9]),
]
# the Class 8-9 stubs each model rests on, by model id
_BASE = {
    "HERED.MONO_RATIO": ["INHERIT_BASICS", "RATIO_FRACTION"],
    "HERED.MONO_PROB": ["PROBABILITY_BASICS"],
    "HERED.DI_RATIO": ["INHERIT_BASICS", "RATIO_FRACTION"],
    "HERED.DI_PROB": ["PROBABILITY_BASICS", "RATIO_FRACTION"],
    "HERED.TEST_CROSS": ["INHERIT_BASICS"],
    "HERED.COUNTS_MONO": ["RATIO_FRACTION", "PERCENT_OF"],
    "HERED.COUNTS_DI": ["RATIO_FRACTION"],
    "HERED.GAMETES": ["INHERIT_BASICS", "POWERS"],
    "HERED.SEX_SEQ": ["PROBABILITY_BASICS", "POWERS"],
    "ENV.TEN_PERCENT": ["PERCENT_OF", "READ_CHAIN"],
    "ENV.ENERGY_LOST": ["PERCENT_OF", "READ_CHAIN"],
    "ENV.TROPHIC": ["READ_CHAIN"],
    "ENV.CONC_CHAIN": ["POWERS", "READ_CHAIN"],
    "REPRO.FISSION": ["POWERS", "CELLS_DIVIDE", "RATE_UNITS"],
    "REPRO.CHROMOSOMES": ["CELLS_DIVIDE", "POWERS"],
    "REPRO.FRAGMENTS": ["CELLS_DIVIDE"],
    "LIFE.EQUATION": ["FORMULA_ATOMS", "RATIO_FRACTION"],
    "LIFE.RATES": ["RATE_UNITS"],
}


def _model_rows() -> list[tuple[str, str, str, list[str]]]:
    """(skill id, title, chapter, prerequisites) for every model, in model order."""
    rows = []
    for model in ALL_MODELS.values():
        prereqs = [*model.prereqs, *(P + b for b in _BASE[model.id])]
        rows.append((model.skill, model.title, model.chapter, prereqs))
    return rows


@functools.cache
def _usage() -> dict[str, set[str]]:
    """misconception id -> the skills whose items use it, found by building every tuple."""
    from app.factory.lanes.biology.lane import LANE

    users: dict[str, set[str]] = {}
    templates = all_templates()
    for mid, template in templates.items():
        model = ALL_MODELS[mid]
        axes = box_axes(template["box"])
        for combo in itertools.product(*[v for _, v in axes]):
            params = {name: c for (name, _), c in zip(axes, combo, strict=True)}
            if LANE.well_posed(template, params) is not None:
                continue
            ctx = LANE.render(template, params)
            for option in ctx.options:
                if option["procedure"] != "correct":
                    users.setdefault(option["procedure"], set()).add(model.skill)
    return users


def used_misconceptions() -> dict[str, str]:
    """misconception id -> its remedial skill (the first skill, in model order, that uses it)."""
    order = [m.skill for m in ALL_MODELS.values()]
    return {mc: min(skills, key=order.index) for mc, skills in sorted(_usage().items())}


def skill_misconceptions(skill_id: str) -> list[str]:
    return sorted(mc for mc, skills in _usage().items() if skill_id in skills)


def mc_texts(mc_id: str) -> tuple[str, str]:
    _, _, area, name = mc_id.split(".")
    return MISC[area][name]


def skill_docs() -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for sid, title, grades in PREREQS:
        docs.append({"id": sid, "title": {"en": title}, "grade_band": grades, "subject": "biology",
                     "prerequisites": [], "misconceptions": [], "bkt": BKT, "status": "draft"})  # fmt: skip
    for sid, title, _, prereqs in _model_rows():
        docs.append({"id": sid, "title": {"en": title}, "grade_band": [10], "subject": "biology",
                     "prerequisites": prereqs, "misconceptions": skill_misconceptions(sid),
                     "bkt": BKT, "status": "draft"})  # fmt: skip
    return docs


def misconception_docs() -> list[dict[str, Any]]:
    docs = []
    for mc_id, skill in used_misconceptions().items():
        title, explanation = mc_texts(mc_id)
        docs.append({"id": mc_id, "title": {"en": title}, "explanation": {"en": explanation},
                     "remedial_skill": skill, "status": "draft"})  # fmt: skip
    return docs


def overlay_docs() -> list[dict[str, Any]]:
    out = []
    for chapter, key in CHAPTER_KEYS.items():
        out.append({
            "id": chapter, "curriculum_id": "cbse", "grade": 10, "chapter": key,
            "skill_ids": [sid for sid, _, ch, _ in _model_rows() if ch == chapter],
            "live": False, "section_map": {},
        })  # fmt: skip
    return out


def _dump(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8", newline="\n"
    )


def template_path(root: Path, template_id: str) -> Path:
    return root / "factory" / "templates" / f"{template_id}.yaml"


def write_content(root: Path) -> dict[str, int]:
    """Write skills, misconceptions, overlays and templates under `root` (idempotent)."""
    skills = skill_docs()
    for doc in skills:
        _dump(root / "skills" / f"{doc['id'].lower()}.yaml", doc)
    mcs = misconception_docs()
    for doc in mcs:
        _dump(root / "misconceptions" / f"{doc['id'].lower()}.yaml", doc)
    overlays = overlay_docs()
    for doc in overlays:
        _dump(root / "overlays" / f"{doc['id']}.yaml", doc)
    templates = all_templates()
    for tpl in templates.values():
        _dump(template_path(root, tpl["id"]), tpl)
    return {
        "skills": len(skills),
        "misconceptions": len(mcs),
        "overlays": len(overlays),
        "templates": len(templates),
    }


_ = AREA_OF_CHAPTER
