# ruff: noqa: E501
"""Templates (item models), skills and overlays of the chemistry lane.

A template is a factory-template/1 record: one family plus its declared parameter box. Everything
here is data written to content/cbse/10/chemistry by `emit`; stamped items are written only by the
factory's stamp command. All wording is original; nothing is copied from a book.
"""

from __future__ import annotations

from typing import Any

from app.factory.lanes.chemistry import metals as M
from app.factory.lanes.chemistry import tables as T
from app.factory.lanes.chemistry.balance import ATOM_FORMULAS
from app.factory.lanes.chemistry.lane import FAMILIES

GRADE = 10
BASE = "cbse.10.chemistry"
CH_RXN, CH_ACID, CH_METAL, CH_CARBON = (
    f"{BASE}.{k}"
    for k in ("reactions", "acids_bases_salts", "metals_nonmetals", "carbon_compounds")
)
CHAPTERS = {
    CH_RXN: ("reactions", "Chemical Reactions and Equations"),
    CH_ACID: ("acids_bases_salts", "Acids, Bases and Salts"),
    CH_METAL: ("metals_nonmetals", "Metals and Non-metals"),
    CH_CARBON: ("carbon_compounds", "Carbon and its Compounds"),
}
FORBIDDEN = [
    "calculus",
    "diagram",
    "free_text",
    "experiment_design",
    "graph_reading",
    "assertion_reason",
]
RIDS = [r[0] for r in T.REACTIONS]


def _c(*values: Any) -> dict[str, Any]:
    return {"choices": list(values)}


def _r(lo: int, hi: int) -> dict[str, Any]:
    return {"min": lo, "max": hi}


# id suffix, family, skill, chapter, technique(s), box
_SPECS: list[tuple[str, str, str, str, list[str], dict[str, Any]]] = [
    ("ATOM_COUNT", "atom_count", "CHEM.RXN.ATOM_COUNT", CH_RXN, ["atom_counting"],
     {"f": _r(0, len(ATOM_FORMULAS) - 1), "coef": _c(1, 2, 3, 4), "el": _r(0, 3)}),
    ("BALANCE", "bal_eq", "CHEM.RXN.BALANCE", CH_RXN, ["atom_counting"],
     {"rid": _c(*RIDS), "wording": _c("student", "smallest")}),
    ("COEFFICIENT", "bal_coef", "CHEM.RXN.COEFFICIENT", CH_RXN, ["atom_counting"],
     {"rid": _c(*RIDS), "ask": _c("total", "coef:0", "coef:1", "coef:2", "coef:3")}),
    ("COMBUSTION", "combustion", "CHEM.RXN.COMBUSTION", CH_RXN, ["atom_counting"],
     {"family": _c("alkane", "alkene", "alkyne"), "n": _r(1, 8), "ask": _c("O2", "CO2", "H2O", "total")}),
    ("REACTION_TYPE", "rxn_type", "CHEM.RXN.TYPE", CH_RXN, ["reaction_types"],
     {"rid": _c(*RIDS)}),
    ("PH_CONVERSION", "ph_conv", "CHEM.ACID.PH_CONVERSION", CH_ACID, ["ph_scale"],
     {"kind": _c("pH_from_H", "H_from_pH", "pOH_from_pH", "pH_from_OH", "OH_from_pH"), "k": _r(1, 13)}),
    ("PH_STRONG", "ph_strong", "CHEM.ACID.PH_STRONG", CH_ACID, ["ph_scale"],
     {"sub": _r(0, 6), "c": _c("1", "0.1", "0.01", "0.001", "0.0001", "0.5", "0.05", "0.005", "0.0005", "0.00005")}),
    ("PH_DILUTION", "ph_dilution", "CHEM.ACID.PH_DILUTION", CH_ACID, ["ph_scale"],
     {"role": _c("acid", "base"), "p0": _r(1, 13), "m": _r(1, 3)}),
    ("PH_RATIO", "ph_ratio", "CHEM.ACID.PH_RATIO", CH_ACID, ["ph_scale"],
     {"a": _r(1, 12), "b": _r(2, 13)}),
    ("PH_CLASSIFY", "ph_classify", "CHEM.ACID.PH_CLASSIFY", CH_ACID, ["ph_scale"],
     {"pH": _r(0, 14), "given": _c("pH", "H", "OH")}),
    ("NEUTRAL_VOLUME", "neutral_volume", "CHEM.ACID.NEUTRAL_VOLUME", CH_ACID, ["neutralisation"],
     {"a": _r(0, 2), "b": _r(0, 4), "ca": _c("0.1", "0.2", "0.5", "1"), "va": _c(10, 20, 25, 50),
      "cb": _c("0.1", "0.2", "0.25", "0.5")}),
    ("NEUTRAL_MASS", "neutral_mass", "CHEM.ACID.NEUTRAL_MASS", CH_ACID, ["stoichiometry"],
     {"a": _r(0, 2), "b": _r(0, 5), "given": _c("acid", "base"), "target": _c("salt", "water", "other"),
      "mode": _c("mass_to_mass", "moles_to_mass", "mass_to_moles"), "n": _c("0.1", "0.25", "0.5", "1", "2")}),
    ("SALT_FORMULA", "salt_formula", "CHEM.ACID.SALT_FORMULA", CH_ACID, ["salt_formulas"],
     {"a": _r(0, 2), "b": _r(0, 5)}),
    ("DISPLACEMENT", "displace_pairs", "CHEM.METAL.DISPLACEMENT", CH_METAL, ["reactivity_series"],
     {"anion": _c("nitrate", "sulphate", "chloride"),
      "metal": _c(*sorted(T.SOLUTION_METALS)), "other": _c(*sorted(T.SOLUTION_METALS))}),
    ("ACID_REACTION", "acid_reaction", "CHEM.METAL.ACID_REACTION", CH_METAL, ["reactivity_series"],
     {"acid": _c("HCl", "H2SO4"), "metal": _c("Mg", "Al", "Zn", "Fe", "Cu", "Ag", "Au")}),
    ("REACTIVITY_ORDER", "reactivity_order", "CHEM.METAL.REACTIVITY_ORDER", CH_METAL, ["reactivity_series"],
     {"combo": _r(0, len(M.ORDER_COMBOS) - 1), "ask": _c("most", "least")}),
    ("IONIC_FORMULA", "ionic_formula", "CHEM.METAL.IONIC_FORMULA", CH_METAL, ["ionic_formulas"],
     {"c": _r(0, len(M.ION_CATIONS) - 1), "a": _r(0, len(T.ANIONS) - 1)}),
    ("SERIES_FORMULA", "series_formula", "CHEM.CARBON.SERIES_FORMULA", CH_CARBON, ["homologous_series"],
     {"family": _c("alkane", "alkene", "alkyne"), "n": _r(1, 10), "ask": _c("H", "bonds", "mass", "n_from_H")}),
    ("SERIES_IDENTIFY", "series_identify", "CHEM.CARBON.SERIES_IDENTIFY", CH_CARBON, ["homologous_series"],
     {"x": _r(1, 10), "y": {"min": 2, "max": 22, "step": 2}}),
    ("ISOMER_COUNT", "isomer_count", "CHEM.CARBON.ISOMER_COUNT", CH_CARBON, ["isomerism"],
     {"n": _r(4, 8)}),
    ("NAME_ALKANE", "name_alkane", "CHEM.CARBON.NAME_ALKANE", CH_CARBON, ["iupac_naming"],
     {"i": _r(0, len(T.ALKANE_NAMES) - 1)}),
    ("NAME_UNSATURATED", "name_unsaturated", "CHEM.CARBON.NAME_UNSATURATED", CH_CARBON, ["iupac_naming"],
     {"i": _r(0, len(T.ALKENE_NAMES) + len(T.ALKYNE_NAMES) - 1)}),
    ("NAME_FUNCTIONAL", "name_functional", "CHEM.CARBON.NAME_FUNCTIONAL", CH_CARBON, ["iupac_naming"],
     {"group": _c(*T.FUNCTIONAL), "n": _r(1, 5)}),
]  # fmt: skip


def template_records() -> list[dict[str, Any]]:
    out = []
    for suffix, family, skill, chapter, techniques, box in _SPECS:
        out.append(
            {
                "id": f"TPL.CHEM.{suffix}",
                "short": f"CHEM.{suffix}",
                "schema": "factory-template/1",
                "lane": "chemistry",
                "family": family,
                "family_version": FAMILIES[family].version,
                "skill_id": skill,
                "box": box,
                "syllabus": {
                    "grade": GRADE,
                    "chapter_ref": chapter,
                    "skill_id": skill,
                    "allowed_methods": techniques,
                    "forbidden_content": FORBIDDEN,
                },
            }
        )
    return out


# ---------------------------------------------------------------- skills

BKT = {"p_init": 0.3, "p_learn": 0.15, "p_slip": 0.1, "p_guess": 0.25}
PREREQS: list[tuple[str, str, str]] = [
    (
        "CHEM.PREREQ.ATOMS_AND_FORMULAE",
        "Read a chemical formula: symbols, subscripts and brackets",
        "Class 8-9 science",
    ),
    (
        "CHEM.PREREQ.CONSERVATION_OF_MASS",
        "Atoms are not created or destroyed in a reaction",
        "Class 9 science",
    ),
    ("CHEM.PREREQ.POWERS_OF_TEN", "Read and write numbers as powers of ten", "Class 8-9 maths"),
    ("CHEM.PREREQ.RATIO_PROPORTION", "Use a ratio to scale a quantity", "Class 8 maths"),
    ("CHEM.PREREQ.MOLES_AND_MOLAR_MASS", "Relate mass, moles and molar mass", "Class 9 science"),
    (
        "CHEM.PREREQ.ACIDS_AND_BASES_BASICS",
        "Say what makes a substance acidic or basic",
        "Class 7-8 science",
    ),
    (
        "CHEM.PREREQ.METALS_BASICS",
        "Tell metals from non-metals by their properties",
        "Class 8 science",
    ),
    ("CHEM.PREREQ.CARBON_BASICS", "Carbon forms four bonds", "Class 8-9 science"),
]
P = "CHEM.PREREQ."
SKILLS: list[tuple[str, str, list[str]]] = [
    (
        "CHEM.RXN.ATOM_COUNT",
        "Count the atoms of an element in a formula with a coefficient and brackets",
        [P + "ATOMS_AND_FORMULAE"],
    ),
    (
        "CHEM.RXN.BALANCE",
        "Balance a chemical equation by counting atoms",
        ["CHEM.RXN.ATOM_COUNT", P + "CONSERVATION_OF_MASS"],
    ),
    (
        "CHEM.RXN.COEFFICIENT",
        "Read a coefficient or a total from a balanced equation",
        ["CHEM.RXN.BALANCE"],
    ),
    ("CHEM.RXN.COMBUSTION", "Balance the complete burning of a hydrocarbon", ["CHEM.RXN.BALANCE"]),
    (
        "CHEM.RXN.TYPE",
        "Classify a reaction as combination, decomposition, displacement or double displacement",
        ["CHEM.RXN.BALANCE"],
    ),
    (
        "CHEM.ACID.PH_CONVERSION",
        "Convert between pH, pOH and ion concentrations written as powers of ten",
        [P + "POWERS_OF_TEN", P + "ACIDS_AND_BASES_BASICS"],
    ),
    (
        "CHEM.ACID.PH_STRONG",
        "Find the pH of a fully ionised acid or base of known concentration",
        ["CHEM.ACID.PH_CONVERSION"],
    ),
    (
        "CHEM.ACID.PH_DILUTION",
        "Predict the pH after a strong acid or base is diluted",
        ["CHEM.ACID.PH_CONVERSION"],
    ),
    (
        "CHEM.ACID.PH_RATIO",
        "Compare ion concentrations from two pH values",
        ["CHEM.ACID.PH_CONVERSION", P + "RATIO_PROPORTION"],
    ),
    (
        "CHEM.ACID.PH_CLASSIFY",
        "Decide whether a solution is acidic, neutral or basic",
        [P + "ACIDS_AND_BASES_BASICS"],
    ),
    (
        "CHEM.ACID.NEUTRAL_VOLUME",
        "Find the volume of base that neutralises an acid",
        ["CHEM.ACID.PH_STRONG", P + "RATIO_PROPORTION"],
    ),
    (
        "CHEM.ACID.NEUTRAL_MASS",
        "Find a mass or an amount from a neutralisation equation",
        ["CHEM.RXN.BALANCE", P + "MOLES_AND_MOLAR_MASS"],
    ),
    (
        "CHEM.ACID.SALT_FORMULA",
        "Write the formula of the salt made from an acid and a base",
        ["CHEM.METAL.IONIC_FORMULA"],
    ),
    (
        "CHEM.METAL.DISPLACEMENT",
        "Predict a displacement reaction from the reactivity series",
        [P + "METALS_BASICS"],
    ),
    (
        "CHEM.METAL.ACID_REACTION",
        "Predict which metals give hydrogen with a dilute acid",
        ["CHEM.METAL.DISPLACEMENT"],
    ),
    (
        "CHEM.METAL.REACTIVITY_ORDER",
        "Order metals by reactivity using the series",
        [P + "METALS_BASICS"],
    ),
    (
        "CHEM.METAL.IONIC_FORMULA",
        "Write the formula of an ionic compound from its ions",
        [P + "ATOMS_AND_FORMULAE"],
    ),
    (
        "CHEM.CARBON.SERIES_FORMULA",
        "Use the general formula of a homologous series",
        [P + "CARBON_BASICS"],
    ),
    (
        "CHEM.CARBON.SERIES_IDENTIFY",
        "Say which general formula a hydrocarbon fits",
        ["CHEM.CARBON.SERIES_FORMULA"],
    ),
    (
        "CHEM.CARBON.ISOMER_COUNT",
        "Count the structural isomers of a small alkane",
        ["CHEM.CARBON.SERIES_FORMULA"],
    ),
    (
        "CHEM.CARBON.NAME_ALKANE",
        "Name a branched or straight alkane from its condensed formula",
        ["CHEM.CARBON.SERIES_FORMULA"],
    ),
    (
        "CHEM.CARBON.NAME_UNSATURATED",
        "Name a straight-chain alkene or alkyne",
        ["CHEM.CARBON.NAME_ALKANE"],
    ),
    (
        "CHEM.CARBON.NAME_FUNCTIONAL",
        "Name a straight-chain compound with one functional group",
        ["CHEM.CARBON.NAME_ALKANE"],
    ),
]


def chapter_of_skill() -> dict[str, str]:
    return {t["skill_id"]: t["syllabus"]["chapter_ref"] for t in template_records()}


def overlay_records() -> list[dict[str, Any]]:
    owner = chapter_of_skill()
    return [
        {
            "id": chapter,
            "curriculum_id": "cbse",
            "grade": GRADE,
            "chapter": key,
            "skill_ids": [s for s, _, _ in SKILLS if owner[s] == chapter],
            "live": False,
            "section_map": {},
        }
        for chapter, (key, _) in CHAPTERS.items()
    ]


def curriculum_block() -> str:
    """The text appended to content/curricula/cbse/curriculum.yaml (a self-contained book)."""
    lines = [
        f"  - id: {BASE}",
        f"    grade: {GRADE}",
        "    subject: chemistry",
        f"    default_chapter_id: {CH_RXN}",
        "    chapters:",
    ]
    for chapter, (key, title) in CHAPTERS.items():
        lines += [
            f"      - id: {chapter}",
            f"        overlay_id: {chapter}",
            f"        chapter_key: {key}",
            f'        titles: {{en: "{title}"}}',
        ]
    return "\n".join(lines) + "\n"
