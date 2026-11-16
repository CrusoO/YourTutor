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
        "The student divides the two quantities the wrong way round, so the answer has the reciprocal size.",
    ),  # noqa: E501
    "MULTIPLIED_NOT_DIVIDED": (
        "Multiplies where the relation divides",
        "The student multiplies the two known quantities instead of dividing one by the other.",
    ),  # noqa: E501
    "DIVIDED_NOT_MULTIPLIED": (
        "Divides where the relation multiplies",
        "The student divides the two known quantities instead of multiplying them.",
    ),  # noqa: E501
    "ADDED_NOT_MULTIPLIED": (
        "Adds the quantities",
        "The student adds numbers that have different units instead of using the relation between them.",
    ),  # noqa: E501
    "TIME_UNIT_SLIP": (
        "Uses minutes as if they were seconds",
        "The student puts a time in minutes straight into a formula that needs seconds.",
    ),  # noqa: E501
    "SERIES_PARALLEL_SWAPPED": (
        "Swaps the series and parallel rules",
        "The student uses the reciprocal rule for resistors in series, or the plain sum for resistors in parallel.",
    ),  # noqa: E501
    "PARALLEL_RESISTANCES_ADDED": (
        "Adds resistances that are in parallel",
        "The student adds the resistances instead of adding their reciprocals.",
    ),  # noqa: E501
    "FORGOT_FINAL_RECIPROCAL": (
        "Stops before the final reciprocal",
        "The student adds the reciprocals correctly but gives the sum itself as the answer.",
    ),  # noqa: E501
    "PARALLEL_AVERAGED": (
        "Averages the parallel resistances",
        "The student takes the mean of the resistances for a parallel pair.",
    ),  # noqa: E501
    "TWO_RESISTOR_SHORTCUT_ON_THREE": (
        "Uses the two-resistor shortcut on three resistors",
        "The student applies product over sum to two resistors and ignores the third.",
    ),  # noqa: E501
    "CURRENT_NOT_SQUARED": (
        "Forgets to square the current",
        "The student writes power or heat with I once instead of I squared.",
    ),  # noqa: E501
    "VOLTAGE_NOT_SQUARED": (
        "Forgets to square the voltage",
        "The student writes V over R, or V t over R, instead of using V squared.",
    ),  # noqa: E501
    "POWER_AS_V_OVER_I": (
        "Writes power as V divided by I",
        "The student divides the voltage by the current where power needs the product.",
    ),  # noqa: E501
    "ROOT_FORGOTTEN": (
        "Forgets the square root",
        "The student stops at P over R and gives it as the current.",
    ),  # noqa: E501
    "AREA_DIRECT_NOT_INVERSE": (
        "Treats area as directly proportional to resistance",
        "The student puts the area on top, so a thicker wire is given a larger resistance.",
    ),  # noqa: E501
    "AREA_UNIT_SLIP": (
        "Uses square millimetres as square metres",
        "The student does not convert the area to square metres, so the answer is off by a power of ten.",
    ),  # noqa: E501
    "ONLY_LENGTH_COUNTED": (
        "Counts only the change in length",
        "The student scales the resistance with the length and forgets that the area changes too.",
    ),  # noqa: E501
    "DIAMETER_AS_AREA": (
        "Treats a change in diameter as a change in area",
        "The student uses the diameter factor where the area factor (its square) is needed.",
    ),  # noqa: E501
    "SERIES_VOLTAGE_NOT_SHARED": (
        "Gives each series resistor the full battery voltage",
        "The student forgets that the battery voltage is shared between resistors in series.",
    ),  # noqa: E501
    "EQUAL_SHARE_ASSUMED": (
        "Splits the quantity equally",
        "The student shares voltage or current equally between unequal resistors.",
    ),  # noqa: E501
    "ONE_RESISTOR_ONLY": (
        "Uses one resistor instead of the combination",
        "The student works with a single resistor and ignores the others in the circuit.",
    ),  # noqa: E501
    "RESISTOR_LEFT_OUT": (
        "Leaves a resistor out of the sum",
        "The student adds only some of the resistors.",
    ),  # noqa: E501
    "WRONG_RESISTOR_USED": (
        "Uses the wrong resistor for the share",
        "The student picks the other resistor when sharing the voltage or current.",
    ),  # noqa: E501
    "CURRENT_NOT_SPLIT": (
        "Gives a branch the whole current",
        "The student forgets that the total current divides between the branches.",
    ),  # noqa: E501
    "ELECTRON_CHARGE_MISUSE": (
        "Multiplies by the electron charge instead of dividing",
        "The student multiplies by e where the number of electrons needs division by e.",
    ),  # noqa: E501
    "CHARGE_NOT_DIVIDED_BY_E": (
        "Gives the charge as the number of electrons",
        "The student stops at the total charge and does not divide by the charge of one electron.",
    ),  # noqa: E501
    "POWER_OF_TEN_SLIP": (
        "Slips by a power of ten",
        "The student mishandles an exponent, so the answer is ten times too large or too small.",
    ),  # noqa: E501
    "TIME_LEFT_OUT": (
        "Leaves the time out",
        "The student finds a power instead of an energy or heat, because the time is never used.",
    ),  # noqa: E501
    "DAYS_LEFT_OUT": (
        "Leaves the number of days out",
        "The student finds the energy for one day only.",
    ),  # noqa: E501
    "ONE_APPLIANCE_ONLY": (
        "Counts only one appliance",
        "The student ignores the second appliance in the total.",
    ),  # noqa: E501
    "WRONG_QUANTITY_SQUARED": (
        "Squares the wrong quantity",
        "The student squares a product or a different quantity than the formula needs.",
    ),  # noqa: E501
    "POWER_FORMULA_MISMATCH": (
        "Mixes up the power formulas",
        "The student uses a power relation with the wrong pair of quantities.",
    ),  # noqa: E501
    "PD_FORMULA_MIXED": (
        "Multiplies work and charge for the potential difference",
        "The student multiplies work done by charge instead of dividing.",
    ),  # noqa: E501
    "POWER_SCALES_LINEARLY": (
        "Assumes power scales in direct proportion",
        "The student scales the power by the same factor as the quantity, ignoring the square.",
    ),  # noqa: E501
    "UNIT_PREFIX_SLIP": (
        "Slips by a thousand between a unit and its milli or kilo form",
        "The student forgets to convert a prefix, so the answer is a thousand times off.",
    ),  # noqa: E501
    "U_SIGN_DROPPED": (
        "Uses u as a positive number",
        "The student puts the object distance in as a positive value instead of a negative one.",
    ),  # noqa: E501
    "F_SIGN_WRONG": (
        "Gives the focal length the wrong sign",
        "The student gives a concave mirror or lens a positive focal length, or a convex one a negative focal length.",
    ),  # noqa: E501
    "V_SIGN_DROPPED": (
        "Loses the sign of the image distance",
        "The student gives the image distance the opposite sign to the correct one.",
    ),  # noqa: E501
    "MIRROR_LENS_FORMULA_MIXED": (
        "Uses the mirror formula for a lens, or the lens formula for a mirror",
        "The student swaps the sign in front of 1/u.",
    ),  # noqa: E501
    "RADIUS_FOCAL_CONFUSED": (
        "Confuses the radius of curvature with the focal length",
        "The student uses R in place of f, or doubles or halves in the wrong direction.",
    ),  # noqa: E501
    "MAG_SIGN_DROPPED": (
        "Drops the minus sign in the mirror magnification",
        "The student writes m = v / u for a mirror.",
    ),  # noqa: E501
    "MAG_INVERTED": (
        "Writes the magnification upside down",
        "The student uses object distance over image distance.",
    ),  # noqa: E501
    "MAG_INVERTED_SIGN_DROPPED": (
        "Inverts the magnification and loses its sign",
        "The student uses u over v with no minus sign.",
    ),  # noqa: E501
    "POWER_IN_CM": (
        "Uses the focal length in centimetres for the power",
        "The student does not change centimetres to metres, so the power is a hundred times off.",
    ),  # noqa: E501
    "POWER_SIGN_IGNORED": (
        "Ignores the sign of the power",
        "The student gives a concave lens a positive power.",
    ),  # noqa: E501
    "POWER_NOT_RECIPROCAL": (
        "Gives the focal length as the power",
        "The student does not take the reciprocal.",
    ),  # noqa: E501
    "FOCAL_LENGTHS_ADDED": (
        "Adds focal lengths for lenses in contact",
        "The student adds the focal lengths instead of the powers.",
    ),  # noqa: E501
    "POWERS_MULTIPLIED": (
        "Multiplies the powers",
        "The student multiplies the powers of two lenses in contact.",
    ),  # noqa: E501
    "INDEX_INVERTED": (
        "Writes the refractive index upside down",
        "The student divides the speed in the medium by the speed in vacuum.",
    ),  # noqa: E501
    "SPEED_INCREASES_IN_DENSER_MEDIUM": (
        "Thinks light speeds up in a denser medium",
        "The student multiplies the speed of light in vacuum by the index.",
    ),  # noqa: E501
    "SNELL_INVERTED": (
        "Inverts the ratio of sines",
        "The student divides the sine of the refraction angle by the sine of the incidence angle.",
    ),  # noqa: E501
    "SINES_SUBTRACTED": (
        "Subtracts or adds the sines",
        "The student combines the two sines by subtraction or addition.",
    ),  # noqa: E501
    "SNELL_MULTIPLIED_WRONG_WAY": (
        "Multiplies where the ratio is needed",
        "The student multiplies the quantities in the sine relation instead of dividing.",
    ),  # noqa: E501
    "RELATIVE_INDEX_INVERTED": (
        "Inverts the relative refractive index",
        "The student writes n1 over n2 (or v2 over v1) for the second medium relative to the first.",
    ),  # noqa: E501
    "INDEX_DIFFERENCE_USED": (
        "Subtracts the indices",
        "The student uses a difference where a ratio is needed.",
    ),  # noqa: E501
    "INDEX_PRODUCT_USED": (
        "Multiplies the indices",
        "The student uses a product where a ratio is needed.",
    ),  # noqa: E501
    "V_SIGN_MEANING_REVERSED": (
        "Reads the sign of the image distance the wrong way round",
        "The student swaps real and virtual when reading the sign of v, or gives an image distance the wrong sign.",
    ),  # noqa: E501
    "MAG_SIGN_MEANING_REVERSED": (
        "Reads the sign of the magnification the wrong way round",
        "The student swaps erect and inverted when reading the sign of m.",
    ),  # noqa: E501
    "SIZE_MEANING_REVERSED": (
        "Reads the size of the magnification the wrong way round",
        "The student swaps magnified and diminished when reading the size of m.",
    ),  # noqa: E501
    "HEIGHT_NOT_USED": (
        "Gives the magnification where the image height is asked",
        "The student forgets to multiply by the object height.",
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
