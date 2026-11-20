# ruff: noqa: E501
"""Skill graph, misconceptions, overlays and template files for CBSE Class 10 physics numericals.

All titles and explanations are original wording. Only syllabus FACTS (chapter and topic names)
are used as input. Everything is `status: draft`; nothing here is reviewed by a person.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.factory.lanes.physics.models import ALL_MODELS
from app.factory.lanes.physics.templates import TEMPLATES

ELEC_CH = "cbse.10.physics.electricity"
LIGHT_CH = "cbse.10.physics.light"
BKT = {"p_init": 0.3, "p_learn": 0.15, "p_slip": 0.1, "p_guess": 0.25}

# (id, title, grade band, prerequisites) -- prerequisite stubs from Classes 8 and 9
PREREQS: list[tuple[str, str, list[int], str]] = [
    (
        "PHY.PREREQ.UNIT_PREFIXES",
        "Change between a unit and its milli, kilo and centi forms",
        [8, 9],
        "Class 8-9 measurement",
    ),  # noqa: E501
    (
        "PHY.PREREQ.REARRANGE_FORMULA",
        "Rearrange a formula by doing the same operation to each side",
        [8, 9],
        "Class 8-9 algebra",
    ),  # noqa: E501
    (
        "PHY.PREREQ.RATIO_PROPORTION",
        "Direct and inverse proportion as a factor",
        [8, 9],
        "Class 8 ratio",
    ),  # noqa: E501
    (
        "PHY.PREREQ.RECIPROCALS",
        "Add fractions and take the reciprocal of a sum",
        [8, 9],
        "Class 8 fractions",
    ),  # noqa: E501
    (
        "PHY.PREREQ.SIGNED_NUMBERS",
        "Use positive and negative numbers for direction on a line",
        [8, 9],
        "Class 8 integers",
    ),  # noqa: E501
    (
        "PHY.PREREQ.SCI_NOTATION",
        "Read and compute with numbers written with powers of ten",
        [8, 9],
        "Class 8-9 exponents",
    ),  # noqa: E501
    (
        "PHY.PREREQ.CIRCUIT_BASICS",
        "Name the parts of a simple circuit and how a meter is connected",
        [8, 9],
        "Class 8-9 science",
    ),  # noqa: E501
    (
        "PHY.PREREQ.LIGHT_BASICS",
        "Light travels in straight lines, reflects and bends at a surface",
        [8, 9],
        "Class 8-9 science",
    ),  # noqa: E501
]
P = "PHY.PREREQ."

SKILLS: list[tuple[str, str, list[str]]] = [
    (
        "PHY.ELEC.CHARGE_CURRENT",
        "Relate charge, current and time",
        [P + "CIRCUIT_BASICS", P + "REARRANGE_FORMULA", P + "UNIT_PREFIXES"],
    ),
    (
        "PHY.ELEC.CHARGE_COUNT",
        "Count the electrons that carry a given charge",
        ["PHY.ELEC.CHARGE_CURRENT", P + "SCI_NOTATION"],
    ),
    (
        "PHY.ELEC.POT_DIFF",
        "Relate potential difference, work done and charge",
        [P + "CIRCUIT_BASICS", P + "REARRANGE_FORMULA"],
    ),
    (
        "PHY.ELEC.OHM_LAW",
        "Use V = I x R to find a voltage, a current or a resistance",
        [
            "PHY.ELEC.POT_DIFF",
            "PHY.ELEC.CHARGE_CURRENT",
            P + "REARRANGE_FORMULA",
            P + "UNIT_PREFIXES",
        ],
    ),
    (
        "PHY.ELEC.RESISTIVITY",
        "Find the resistance or length of a wire from its resistivity",
        ["PHY.ELEC.OHM_LAW", P + "RATIO_PROPORTION", P + "UNIT_PREFIXES"],
    ),
    (
        "PHY.ELEC.RESIST_FACTORS",
        "Predict how resistance changes when a wire's length or area changes",
        ["PHY.ELEC.RESISTIVITY", P + "RATIO_PROPORTION"],
    ),
    ("PHY.ELEC.SERIES", "Combine resistors in series", ["PHY.ELEC.OHM_LAW"]),
    ("PHY.ELEC.PARALLEL", "Combine resistors in parallel", ["PHY.ELEC.OHM_LAW", P + "RECIPROCALS"]),
    (
        "PHY.ELEC.SERIES_CIRCUIT",
        "Find current and voltage shares in a series circuit",
        ["PHY.ELEC.SERIES", "PHY.ELEC.OHM_LAW"],
    ),
    (
        "PHY.ELEC.PARALLEL_CIRCUIT",
        "Find branch and total currents in a parallel circuit",
        ["PHY.ELEC.PARALLEL", "PHY.ELEC.OHM_LAW"],
    ),
    (
        "PHY.ELEC.MIXED_NETWORK",
        "Reduce a series and parallel network step by step",
        ["PHY.ELEC.SERIES_CIRCUIT", "PHY.ELEC.PARALLEL_CIRCUIT"],
    ),
    (
        "PHY.ELEC.POWER",
        "Find electric power, current or resistance from P = V x I and its forms",
        ["PHY.ELEC.OHM_LAW"],
    ),
    (
        "PHY.ELEC.POWER_SCALING",
        "Predict how power or heat changes when a quantity is scaled",
        ["PHY.ELEC.POWER", P + "RATIO_PROPORTION"],
    ),
    (
        "PHY.ELEC.ENERGY_KWH",
        "Find electrical energy in joules and in kilowatt-hours",
        ["PHY.ELEC.POWER", P + "UNIT_PREFIXES"],
    ),
    (
        "PHY.ELEC.HEATING",
        "Find the heat produced by a current in a resistor",
        ["PHY.ELEC.POWER", "PHY.ELEC.ENERGY_KWH"],
    ),
    (
        "PHY.LIGHT.SIGN_CONVENTION",
        "Give distances the right sign in the Cartesian convention",
        [P + "SIGNED_NUMBERS", P + "LIGHT_BASICS"],
    ),
    (
        "PHY.LIGHT.MIRROR_FOCAL",
        "Relate the focal length and radius of curvature of a mirror",
        ["PHY.LIGHT.SIGN_CONVENTION"],
    ),
    (
        "PHY.LIGHT.MIRROR_FORMULA",
        "Use the mirror formula for image, object or focal distance",
        ["PHY.LIGHT.MIRROR_FOCAL", P + "RECIPROCALS", P + "REARRANGE_FORMULA"],
    ),
    (
        "PHY.LIGHT.MIRROR_MAGNIFICATION",
        "Find the magnification, image height or image distance for a mirror",
        ["PHY.LIGHT.MIRROR_FORMULA", P + "RATIO_PROPORTION"],
    ),
    (
        "PHY.LIGHT.IMAGE_NATURE",
        "Decide the nature of an image from the signs of v and m",
        ["PHY.LIGHT.MIRROR_MAGNIFICATION", "PHY.LIGHT.LENS_MAGNIFICATION"],
    ),
    (
        "PHY.LIGHT.LENS_FORMULA",
        "Use the thin lens formula for image, object or focal distance",
        ["PHY.LIGHT.SIGN_CONVENTION", P + "RECIPROCALS", P + "REARRANGE_FORMULA"],
    ),
    (
        "PHY.LIGHT.LENS_MAGNIFICATION",
        "Find the magnification, image height or image distance for a lens",
        ["PHY.LIGHT.LENS_FORMULA"],
    ),
    (
        "PHY.LIGHT.LENS_POWER",
        "Relate the power and focal length of a lens",
        ["PHY.LIGHT.LENS_FORMULA", P + "UNIT_PREFIXES"],
    ),
    (
        "PHY.LIGHT.LENS_COMBINATION",
        "Add the powers of thin lenses in contact",
        ["PHY.LIGHT.LENS_POWER"],
    ),
    (
        "PHY.LIGHT.REFRACTIVE_INDEX",
        "Relate refractive index and the speed of light in a medium",
        [P + "SCI_NOTATION", P + "RATIO_PROPORTION", P + "LIGHT_BASICS"],
    ),
    (
        "PHY.LIGHT.SNELL",
        "Use the ratio of sines to find an index or a sine",
        ["PHY.LIGHT.REFRACTIVE_INDEX", P + "RATIO_PROPORTION"],
    ),
    (
        "PHY.LIGHT.RELATIVE_INDEX",
        "Find the refractive index of one medium relative to another",
        ["PHY.LIGHT.REFRACTIVE_INDEX"],
    ),
]

# misconception id -> (title, explanation); the title names the wrong procedure
_TEXT: dict[str, tuple[str, str]] = {
    "FORMULA_INVERTED": (
        "Uses the relation upside down",
        "You may have divided the wrong way round.",
    ),  # noqa: E501
    "MULTIPLIED_NOT_DIVIDED": (
        "Multiplies where the relation divides",
        "You may have multiplied when you should divide.",
    ),  # noqa: E501
    "DIVIDED_NOT_MULTIPLIED": (
        "Divides where the relation multiplies",
        "You may have divided the two numbers when you should multiply them.",
    ),  # noqa: E501
    "ADDED_NOT_MULTIPLIED": (
        "Adds the quantities",
        "You may have added numbers that have different units. Use the formula that links them.",
    ),  # noqa: E501
    "TIME_UNIT_SLIP": (
        "Uses minutes as if they were seconds",
        "You may have used minutes where the formula needs seconds.",
    ),  # noqa: E501
    "SERIES_PARALLEL_SWAPPED": (
        "Swaps the series and parallel rules",
        "You may have mixed up the rules for series and parallel.",
    ),  # noqa: E501
    "PARALLEL_RESISTANCES_ADDED": (
        "Adds resistances that are in parallel",
        "You may have added the resistances. For parallel, add their fractions 1/R.",
    ),  # noqa: E501
    "FORGOT_FINAL_RECIPROCAL": (
        "Stops before the final reciprocal",
        "You may have added the fractions but forgot to flip the total.",
    ),  # noqa: E501
    "PARALLEL_AVERAGED": (
        "Averages the parallel resistances",
        "You may have taken the average of two resistors in parallel.",
    ),  # noqa: E501
    "TWO_RESISTOR_SHORTCUT_ON_THREE": (
        "Uses the two-resistor shortcut on three resistors",
        "You may have used the two-resistor shortcut and ignored the third.",
    ),  # noqa: E501
    "CURRENT_NOT_SQUARED": (
        "Forgets to square the current",
        "You may have used I once. The formula needs I squared.",
    ),  # noqa: E501
    "VOLTAGE_NOT_SQUARED": (
        "Forgets to square the voltage",
        "You may have used V where the formula needs V squared.",
    ),  # noqa: E501
    "POWER_AS_V_OVER_I": (
        "Writes power as V divided by I",
        "You may have divided voltage by current. Power needs them multiplied.",
    ),  # noqa: E501
    "ROOT_FORGOTTEN": (
        "Forgets the square root",
        "You may have stopped at P over R. Now take the square root.",
    ),  # noqa: E501
    "AREA_DIRECT_NOT_INVERSE": (
        "Treats area as directly proportional to resistance",
        "You may have put the area on top. A thicker wire gives less resistance.",
    ),  # noqa: E501
    "AREA_UNIT_SLIP": (
        "Uses square millimetres as square metres",
        "You may have left the area in the wrong unit. Change it to square metres.",
    ),  # noqa: E501
    "ONLY_LENGTH_COUNTED": (
        "Counts only the change in length",
        "You may have changed only the length. The area changes too.",
    ),  # noqa: E501
    "DIAMETER_AS_AREA": (
        "Treats a change in diameter as a change in area",
        "You may have used the diameter where the area is needed.",
    ),  # noqa: E501
    "SERIES_VOLTAGE_NOT_SHARED": (
        "Gives each series resistor the full battery voltage",
        "You may have forgotten that the battery voltage is shared in series.",
    ),  # noqa: E501
    "EQUAL_SHARE_ASSUMED": (
        "Splits the quantity equally",
        "You may have shared the voltage or current equally between unequal resistors.",
    ),  # noqa: E501
    "ONE_RESISTOR_ONLY": (
        "Uses one resistor instead of the combination",
        "You may have used one resistor and ignored the others.",
    ),  # noqa: E501
    "RESISTOR_LEFT_OUT": (
        "Leaves a resistor out of the sum",
        "You may have added only some of the resistors.",
    ),  # noqa: E501
    "WRONG_RESISTOR_USED": (
        "Uses the wrong resistor for the share",
        "You may have picked the other resistor when sharing the voltage.",
    ),  # noqa: E501
    "CURRENT_NOT_SPLIT": (
        "Gives a branch the whole current",
        "You may have forgotten that the current splits between the branches.",
    ),  # noqa: E501
    "ELECTRON_CHARGE_MISUSE": (
        "Multiplies by the electron charge instead of dividing",
        "You may have multiplied by e when you should divide by e.",
    ),  # noqa: E501
    "CHARGE_NOT_DIVIDED_BY_E": (
        "Gives the charge as the number of electrons",
        "You may have stopped at the total charge. Divide by the charge of one electron.",
    ),  # noqa: E501
    "POWER_OF_TEN_SLIP": (
        "Slips by a power of ten",
        "You may have slipped on a power of ten.",
    ),  # noqa: E501
    "TIME_LEFT_OUT": (
        "Leaves the time out",
        "You may have found the power and forgotten to use the time.",
    ),  # noqa: E501
    "DAYS_LEFT_OUT": (
        "Leaves the number of days out",
        "You may have found the energy for one day only.",
    ),  # noqa: E501
    "ONE_APPLIANCE_ONLY": (
        "Counts only one appliance",
        "You may have left out the second appliance.",
    ),  # noqa: E501
    "WRONG_QUANTITY_SQUARED": (
        "Squares the wrong quantity",
        "You may have squared the wrong quantity.",
    ),  # noqa: E501
    "POWER_FORMULA_MISMATCH": (
        "Mixes up the power formulas",
        "You may have used a power formula with the wrong two quantities.",
    ),  # noqa: E501
    "PD_FORMULA_MIXED": (
        "Multiplies work and charge for the potential difference",
        "You may have multiplied work by charge when you should divide.",
    ),  # noqa: E501
    "POWER_SCALES_LINEARLY": (
        "Assumes power scales in direct proportion",
        "You may have scaled the power by the same factor. It goes up with the square.",
    ),  # noqa: E501
    "UNIT_PREFIX_SLIP": (
        "Slips by a thousand between a unit and its milli or kilo form",
        "You may have forgotten to change the unit. The answer is 1000 times off.",
    ),  # noqa: E501
    "U_SIGN_DROPPED": (
        "Uses u as a positive number",
        "You may have used a positive object distance. It must be negative.",
    ),  # noqa: E501
    "F_SIGN_WRONG": (
        "Gives the focal length the wrong sign",
        "You may have given the focal length the wrong sign.",
    ),  # noqa: E501
    "V_SIGN_DROPPED": (
        "Loses the sign of the image distance",
        "You may have given the image distance the wrong sign.",
    ),  # noqa: E501
    "MIRROR_LENS_FORMULA_MIXED": (
        "Uses the mirror formula for a lens, or the lens formula for a mirror",
        "You may have put the wrong sign in front of 1/u.",
    ),  # noqa: E501
    "RADIUS_FOCAL_CONFUSED": (
        "Confuses the radius of curvature with the focal length",
        "You may have used R for f, or doubled instead of halved.",
    ),  # noqa: E501
    "MAG_SIGN_DROPPED": (
        "Drops the minus sign in the mirror magnification",
        "You may have written m = v / u and left out the minus.",
    ),  # noqa: E501
    "MAG_INVERTED": (
        "Writes the magnification upside down",
        "You may have put object distance over image distance. Turn it round.",
    ),  # noqa: E501
    "MAG_INVERTED_SIGN_DROPPED": (
        "Inverts the magnification and loses its sign",
        "You may have used u over v with no minus sign.",
    ),  # noqa: E501
    "POWER_IN_CM": (
        "Uses the focal length in centimetres for the power",
        "You may have left the length in centimetres. The power is 100 times off.",
    ),  # noqa: E501
    "POWER_SIGN_IGNORED": (
        "Ignores the sign of the power",
        "You may have given a spreading (concave) lens a positive power.",
    ),  # noqa: E501
    "POWER_NOT_RECIPROCAL": (
        "Gives the focal length as the power",
        "You may have forgotten to flip the fraction.",
    ),  # noqa: E501
    "FOCAL_LENGTHS_ADDED": (
        "Adds focal lengths for lenses in contact",
        "You may have added the focal lengths. Add the powers instead.",
    ),  # noqa: E501
    "POWERS_MULTIPLIED": (
        "Multiplies the powers",
        "You may have multiplied the powers of two lenses. Add them instead.",
    ),  # noqa: E501
    "INDEX_INVERTED": (
        "Writes the refractive index upside down",
        "You may have flipped the speed ratio.",
    ),  # noqa: E501
    "SPEED_INCREASES_IN_DENSER_MEDIUM": (
        "Thinks light speeds up in a denser medium",
        "You may have multiplied the speed of light by the index. Divide instead.",
    ),  # noqa: E501
    "SNELL_INVERTED": (
        "Inverts the ratio of sines",
        "You may have put the two angle sines the wrong way round.",
    ),  # noqa: E501
    "SINES_SUBTRACTED": (
        "Subtracts or adds the sines",
        "You may have added or taken away the two sines. Divide them instead.",
    ),  # noqa: E501
    "SNELL_MULTIPLIED_WRONG_WAY": (
        "Multiplies where the ratio is needed",
        "You may have multiplied where you should divide.",
    ),  # noqa: E501
    "RELATIVE_INDEX_INVERTED": (
        "Inverts the relative refractive index",
        "You may have turned the ratio upside down for the second material.",
    ),  # noqa: E501
    "INDEX_DIFFERENCE_USED": (
        "Subtracts the indices",
        "You may have taken one number away from the other. Divide them instead.",
    ),  # noqa: E501
    "INDEX_PRODUCT_USED": (
        "Multiplies the indices",
        "You may have multiplied two numbers when you should divide them.",
    ),  # noqa: E501
    "V_SIGN_MEANING_REVERSED": (
        "Reads the sign of the image distance the wrong way round",
        "You may have mixed up real and not-real images.",
    ),  # noqa: E501
    "MAG_SIGN_MEANING_REVERSED": (
        "Reads the sign of the magnification the wrong way round",
        "You may have mixed up upright and upside down.",
    ),  # noqa: E501
    "SIZE_MEANING_REVERSED": (
        "Reads the size of the magnification the wrong way round",
        "You may have mixed up bigger and smaller.",
    ),  # noqa: E501
    "HEIGHT_NOT_USED": (
        "Gives the magnification where the image height is asked",
        "You may have forgotten to multiply by the height of the object.",
    ),  # noqa: E501
}


def mc_name(mc_id: str) -> str:
    return mc_id.rsplit(".", 1)[1]


def used_misconceptions() -> dict[str, str]:
    """misconception id -> the first skill whose models use it (its remedial skill)."""
    from app.factory.lanes.physics.build import _NAT_IDS

    out: dict[str, str] = {}
    for model in ALL_MODELS.values():
        for variant in model.variants.values():
            for mc, _ in variant.wrongs:
                out.setdefault(mc, model.skill)
        out.setdefault(f"{model.mc_prefix}.UNIT_PREFIX_SLIP", model.skill)
        if model.extra_wrongs:
            for p in ("object_distance", "focal", "image_real"):
                case = f"concave_mirror:{p}"
                for mc, _ in model.extra_wrongs(
                    {"case": case}, next(iter(model.variants.values()))
                ):  # noqa: E501
                    out.setdefault(mc, model.skill)
    for mc in _NAT_IDS:
        out.setdefault(mc, "PHY.LIGHT.IMAGE_NATURE")
    return out


def skill_misconceptions(skill_id: str) -> list[str]:
    return sorted(mc for mc, owner in _all_users().items() if skill_id in owner)


def _all_users() -> dict[str, set[str]]:
    users: dict[str, set[str]] = {}
    for model in ALL_MODELS.values():
        ids = {mc for v in model.variants.values() for mc, _ in v.wrongs}
        ids.add(f"{model.mc_prefix}.UNIT_PREFIX_SLIP")
        if model.extra_wrongs:
            for p in ("object_distance", "focal", "image_real"):
                ids |= {
                    mc
                    for mc, _ in model.extra_wrongs(
                        {"case": f"concave_mirror:{p}"}, next(iter(model.variants.values()))
                    )
                }
        if model.id == "LIGHT.MIRROR_NATURE":
            from app.factory.lanes.physics.build import _NAT_IDS

            ids |= set(_NAT_IDS)
        for mc in ids:
            users.setdefault(mc, set()).add(model.skill)
    return users


def skill_docs() -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for sid, title, grades, _ in PREREQS:
        docs.append(
            {
                "id": sid,
                "title": {"en": title},
                "grade_band": grades,
                "subject": "physics",
                "prerequisites": [],
                "misconceptions": [],
                "bkt": BKT,
                "status": "draft",
            }
        )
    for sid, title, prereqs in SKILLS:
        docs.append(
            {
                "id": sid,
                "title": {"en": title},
                "grade_band": [10],
                "subject": "physics",
                "prerequisites": prereqs,
                "misconceptions": skill_misconceptions(sid),
                "bkt": BKT,
                "status": "draft",
            }
        )
    return docs


def misconception_docs() -> list[dict[str, Any]]:
    docs = []
    for mc, skill in sorted(used_misconceptions().items()):
        title, expl = _TEXT[mc_name(mc)]
        docs.append(
            {
                "id": mc,
                "title": {"en": title},
                "explanation": {"en": expl},
                "remedial_skill": skill,
                "status": "draft",
            }
        )
    return docs


def overlay_docs() -> list[dict[str, Any]]:
    out = []
    for chapter, key in ((ELEC_CH, "electricity"), (LIGHT_CH, "light")):
        out.append({
            "id": chapter, "curriculum_id": "cbse", "grade": 10, "chapter": key,
            "skill_ids": [s for s, *_ in SKILLS if s.startswith(
                "PHY.ELEC." if key == "electricity" else "PHY.LIGHT.")],
            "live": False, "section_map": {},
        })  # fmt: skip
    return out


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
    return {"skills": len(SKILLS) + len(PREREQS), "misconceptions": len(misconception_docs()),
            "overlays": 2, "templates": len(TEMPLATES)}  # fmt: skip
