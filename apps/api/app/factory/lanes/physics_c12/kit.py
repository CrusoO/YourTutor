"""Small helpers shared by the Class 12 physics model files.

A model is data (see physics/model.py: Model and Variant are reused as they are). These helpers
only cut the typing: `var` builds a Variant, `bases` builds the base-value function, `reg` puts a
model in the registry and records its skill title.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from fractions import Fraction
from typing import Any

from app.factory.lanes.physics.model import FORMS, Model, Variant
from app.factory.lanes.physics_c12.quantities import to_si

GRADE = 12
MC_PREFIX = "PHY.MC.C12"

CHAPTERS: dict[str, str] = {
    "EF": "electric_charges_fields",
    "CAP": "electrostatic_potential_capacitance",
    "CUR": "current_electricity",
    "MAG": "moving_charges_magnetism",
    "MAT": "magnetism_matter",
    "EMI": "electromagnetic_induction",
    "AC": "alternating_current",
    "EMW": "electromagnetic_waves",
    "RAY": "ray_optics",
    "WAVE": "wave_optics",
    "DUAL": "dual_nature",
    "ATOM": "atoms",
    "NUC": "nuclei",
    "SEMI": "semiconductor_electronics",
}
CHAPTER_TITLES: dict[str, str] = {
    "EF": "Electric Charges and Fields",
    "CAP": "Electrostatic Potential and Capacitance",
    "CUR": "Current Electricity",
    "MAG": "Moving Charges and Magnetism",
    "MAT": "Magnetism and Matter",
    "EMI": "Electromagnetic Induction",
    "AC": "Alternating Current",
    "EMW": "Electromagnetic Waves",
    "RAY": "Ray Optics and Optical Instruments",
    "WAVE": "Wave Optics",
    "DUAL": "Dual Nature of Radiation and Matter",
    "ATOM": "Atoms",
    "NUC": "Nuclei",
    "SEMI": "Semiconductor Electronics",
}


def chapter_id(area: str) -> str:
    return f"cbse.{GRADE}.physics.{CHAPTERS[area]}"


def mc(name: str) -> str:
    return f"{MC_PREFIX}.{name}"


def var(
    find: str,
    needs: str,
    expr: str,
    formula: str,
    ask: str,
    wrongs: list[tuple[str, str]],
    *,
    rearr: str | None = None,
    laws: tuple[str, ...] | None = None,
    forms: tuple[str, ...] = FORMS,
    keq: tuple[str, str] | None = None,
) -> Variant:
    """One question variant. The id is `<find>_from_<needs>`; keq defaults to 1 * find = expr."""
    names = tuple(needs.split())
    return Variant(
        id=f"{find}_from_{'_'.join(names)}",
        find=find,
        needs=names,
        expr=expr,
        keq=keq or ("1", expr),
        formula=formula,
        ask=ask,
        wrongs=tuple((mc(a), b) for a, b in wrongs),
        rearr=rearr,
        laws=laws,
        forms=forms,
    )


def bases(spec: Mapping[str, tuple[str, str]]) -> Callable[[Mapping[str, Any]], Any]:
    """spec: symbol -> (value param, unit or '$unit param'); returns the model's base function."""

    def build(p: Mapping[str, Any]) -> tuple[dict[str, Fraction], dict[str, str]]:
        si: dict[str, Fraction] = {}
        un: dict[str, str] = {}
        for sym, (vp, u) in spec.items():
            unit = str(p[u[1:]]) if u.startswith("$") else u
            si[sym] = to_si(p[vp], unit)
            un[sym] = unit
        return si, un

    return build


def pairs(
    names: tuple[str, str], param: str, unit_a: str, unit_b: str
) -> Callable[[Mapping[str, Any]], Any]:
    """Base function for a model whose two values come as one 'a,b' text parameter."""

    def build(p: Mapping[str, Any]) -> tuple[dict[str, Fraction], dict[str, str]]:
        a, b = str(p[param]).split(",")
        return (
            {names[0]: to_si(a, unit_a), names[1]: to_si(b, unit_b)},
            {names[0]: unit_a, names[1]: unit_b},
        )

    return build


def c(*values: str) -> dict[str, Any]:
    return {"choices": list(values)}


REGISTRY: dict[str, Model] = {}
TITLES: dict[str, tuple[str, tuple[str, ...]]] = {}


def reg(model: Model, title: str, prereqs: tuple[str, ...]) -> Model:
    """Register a model with its skill title and prerequisite skill ids."""
    if model.id in REGISTRY:
        raise ValueError(f"duplicate model {model.id}")
    REGISTRY[model.id] = model
    TITLES[model.id] = (title, prereqs)
    return model


def model(
    mid: str,
    area: str,
    technique: str,
    topic: str,
    **kw: Any,
) -> Model:
    """Model with the lane defaults (skill id from the model id, chapter from the area)."""
    return Model(
        id=mid,
        skill=f"PHY.C12.{mid}",
        chapter=chapter_id(area),
        technique=technique,
        topic=topic,
        mc_prefix=MC_PREFIX,
        **kw,
    )


P = "PHY.C12.PREREQ."
__all__ = ["FORMS", "Model", "Variant"]
