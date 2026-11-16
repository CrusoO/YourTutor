"""Item models (factory-template/1): one per skill, with its declared parameter box.

Values in a box are strings so decimals stay exact. `form` is the question form: mcq1 (1 mark),
num2 (2 marks), num3 (3 marks), case4 (4 marks, a short case). Every stamped item is a
multiple-choice presentation of a numerical answer (the stamp step writes only that type today).
"""

from __future__ import annotations

from typing import Any

from app.factory.lanes.physics.models import ALL_MODELS

FORMS = ["mcq1", "num2", "num3", "case4"]
FORBIDDEN = ["calculus", "graph_reading", "ray_diagram", "experiment_design", "assertion_reason"]


def _c(*values: str) -> dict[str, Any]:
    return {"choices": list(values)}


def _variants(model_id: str) -> dict[str, Any]:
    return _c(*ALL_MODELS[model_id].variants)


R2 = ["2,3", "4,6", "5,10", "10,15", "2,4", "6,6", "10,20", "6,3", "20,5", "9,18", "12,4", "30,20"]
R3 = ["2,3,5", "4,6,10", "5,5,10", "10,20,30", "12,6,4", "30,20,12", "60,30,20", "9,18,6"]
PAR2 = ["6,3", "10,15", "20,5", "9,18", "4,4", "12,4", "30,20", "60,20"]
PAR3 = ["12,6,4", "30,20,12", "60,30,20", "6,6,6", "9,18,6"]
_DEVICES_ALL = ["concave_mirror", "convex_mirror", "convex_lens", "concave_lens"]
_UM = ["10", "12", "15", "20", "24", "30", "40", "60"]


def _box(model_id: str) -> dict[str, Any]:  # noqa: PLR0911
    v = {"variant": _variants(model_id), "form": _c(*FORMS)}
    boxes: dict[str, dict[str, Any]] = {
        "ELEC.CHARGE_CURRENT": {
            "I": _c("0.5", "2", "5", "20", "50"),
            "iu": _c("A", "mA"),
            "t": _c("2", "5", "10", "30"),
            "tu": _c("s", "min"),
        },
        "ELEC.CHARGE_COUNT": {
            "I": _c("0.8", "1.6", "3.2", "2.4", "4", "0.4"),
            "t": _c("1", "2", "5", "10"),
        },
        "ELEC.POT_DIFF": {
            "V": _c("1.5", "3", "6", "12", "24", "220"),
            "Q": _c("0.5", "2", "5", "10", "20"),
        },
        "ELEC.OHM": {
            "I": _c("0.25", "0.5", "2", "5", "20", "50"),
            "iu": _c("A", "mA"),
            "R": _c("2", "4", "5", "10", "25", "100"),
            "ru": _c("ohm", "kohm"),
        },
        "ELEC.RESISTIVITY": {
            "rho": _c("1e-6", "5e-7", "2e-6", "1e-7"),
            "L": _c("1", "2", "5", "10", "20"),
            "lu": _c("m", "cm"),
            "A": _c("0.25", "0.5", "1", "2"),
            "au": _c("mm^2"),
        },
        "ELEC.RESIST_SCALE": {"case": _c("stretch", "diameter"), "k": _c("2", "3", "4", "1/2")},
        "ELEC.SERIES": {"rset": _c(*R2, *R3)},
        "ELEC.PARALLEL": {"rset": _c(*PAR2, *PAR3)},
        "ELEC.SERIES_CIRCUIT": {
            "rset": _c(
                "2,3",
                "4,6",
                "5,10",
                "10,15",
                "2,4",
                "6,6",
                "10,20",
                "2,3,5",
                "4,6,10",
                "5,5,10",
                "10,20,30",
            ),
            "I": _c("0.2", "0.5", "1", "2"),
        },
        "ELEC.PARALLEL_CIRCUIT": {
            "rset": _c(
                "6,3",
                "10,15",
                "20,5",
                "12,4",
                "30,20",
                "4,4",
                "12,6,4",
                "30,20,12",
                "60,30,20",
                "9,18,6",
            ),
            "V": _c("6", "12", "24", "30", "60"),
        },
        "ELEC.MIXED_NETWORK": {
            "R1": _c("2", "4", "6", "10"),
            "pair": _c("6,3", "10,15", "20,5", "12,4", "30,20", "9,18"),
            "I": _c("0.5", "1", "1.5", "2", "3"),
        },
        "ELEC.POWER": {
            "I": _c("0.25", "0.5", "1", "2", "5"),
            "R": _c("10", "12", "20", "40", "50", "100", "200", "400"),
        },
        "ELEC.POWER_SCALE": {"k": _c("2", "3", "4", "1/2"), "k2": _c("2", "3", "4", "5", "1/2")},
        "ELEC.ENERGY": {
            "P1": _c("40", "60", "100", "1000", "1500"),
            "t1": _c("2", "4", "5", "8"),
            "P2": _c("40", "100"),
            "t2": _c("2", "3"),
            "d": _c("10", "30"),
        },
        "ELEC.HEATING": {
            "I": _c("0.5", "1", "2", "4", "5"),
            "R": _c("10", "20", "40", "50", "100"),
            "t": _c("2", "5", "10"),
            "tu": _c("s", "min"),
        },
        "LIGHT.SIGN": {
            "case": _c(
                "concave_mirror:focal",
                "convex_mirror:focal",
                "convex_lens:focal",
                "concave_lens:focal",
            ),
            "d": _c("5", "10", "12", "15", "20", "25", "30", "40", "50"),
        },
        "LIGHT.MIRROR_FOCAL": {
            "device": _c("concave_mirror", "convex_mirror"),
            "fm": _c("5", "10", "12", "15", "20", "25", "30"),
        },
        "LIGHT.MIRROR_FORMULA": {
            "device": _c("concave_mirror", "convex_mirror"),
            "fm": _c("10", "12", "15", "20", "25", "30"),
            "um": _c(*_UM),
        },
        "LIGHT.MIRROR_MAG": {
            "device": _c("concave_mirror", "convex_mirror"),
            "fm": _c("10", "15", "20", "30"),
            "um": _c("15", "20", "30", "40", "60"),
            "h": _c("2", "4"),
        },
        "LIGHT.MIRROR_NATURE": {
            "device": _c(*_DEVICES_ALL),
            "fm": _c("10", "15", "20", "30"),
            "um": _c("15", "20", "30", "40", "60"),
        },
        "LIGHT.LENS_FORMULA": {
            "device": _c("convex_lens", "concave_lens"),
            "fm": _c("10", "15", "20", "30"),
            "um": _c("15", "20", "30", "40", "60"),
        },
        "LIGHT.LENS_MAG": {
            "device": _c("convex_lens", "concave_lens"),
            "fm": _c("10", "15", "20", "30"),
            "um": _c("15", "20", "30", "40", "60"),
            "h": _c("2", "4"),
        },
        "LIGHT.LENS_POWER": {
            "device": _c("convex_lens", "concave_lens"),
            "fm": _c("10", "12.5", "20", "25", "40", "50", "100", "200"),
        },
        "LIGHT.LENS_COMB": {
            "d1": _c("convex_lens", "concave_lens"),
            "d2": _c("convex_lens", "concave_lens"),
            "f1": _c("20", "25", "50", "100"),
            "f2": _c("20", "25", "50", "100"),
        },
        "LIGHT.REFRACTIVE_INDEX": {"n": _c("1.2", "1.25", "1.5", "1.6", "2", "2.4", "2.5")},
        "LIGHT.SNELL": {
            "n": _c("1.2", "1.25", "1.5", "1.6", "2"),
            "si": _c("0.4", "0.5", "0.6", "0.75", "0.8", "0.9"),
        },
        "LIGHT.RELATIVE_INDEX": {
            "n1": _c("1", "1.25", "1.5", "2", "2.4"),
            "n2": _c("1.2", "1.25", "1.5", "2", "2.4", "3"),
        },
    }
    return {**v, **boxes[model_id]}


def make_template(model_id: str) -> dict[str, Any]:
    model = ALL_MODELS[model_id]
    return {
        "id": f"TPL2.{model.skill}",
        "schema": "factory-template/1",
        "lane": "physics",
        "model": model.id,
        "skill_id": model.skill,
        "box": _box(model_id),
        "syllabus": {
            "grade": 10,
            "chapter_ref": model.chapter,
            "skill_id": model.skill,
            "allowed_methods": [model.technique],
            "forbidden_content": FORBIDDEN,
        },
    }


TEMPLATES: dict[str, dict[str, Any]] = {mid: make_template(mid) for mid in ALL_MODELS}
