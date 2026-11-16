"""Build a small factory-stamped content root for tests (never the lane PR files).

The root has the layout the lanes use: `<root>/cbse/10/maths/{skills,misconceptions,overlays,items}`
with the lane's own `factory/` folder (ledger, certificates, factory-template/1 file) beside them.
Items are produced by the maths quadratic lane through the real certify and stamp commands.
"""

from __future__ import annotations

import copy
from pathlib import Path

import yaml

from app.factory.cli import main
from app.factory.lanes.maths_quadratic import TEMPLATE

SKILL = "MATH.ALG.QUAD.FACTORISE"
OVERLAY = "cbse.10.maths.quadratic"
MISCONCEPTIONS = ("sign_error", "one_root_only", "sum_product_confusion")

SMALL = copy.deepcopy(TEMPLATE)
SMALL["box"] = {"a": {"choices": [1, 2]}, "r1": {"min": -3, "max": 3}, "r2": {"min": -3, "max": 3}}


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8", newline="\n")


def build_factory_root(tmp_path: Path, count: int = 4) -> tuple[Path, Path]:
    """(content root, subject folder) with `count` stamped tier A items and a not-live overlay."""
    root = tmp_path / "content"
    subject = root / "cbse" / "10" / "maths"
    template = subject / "factory" / "templates" / "TPL2.MATHS.QUAD.INT_ROOTS.yaml"
    _write(template, SMALL)
    base = ["--root", str(subject)]
    assert main([*base, "certify", str(template), "--no-reference-index"]) == 0
    assert main([*base, "stamp", str(template), "--count", str(count), "--no-reference-index"]) == 0
    _write(
        subject / "skills" / f"{SKILL}.yaml",
        {
            "id": SKILL,
            "title": {"en": "Factorise a quadratic"},
            "grade_band": [10],
            "subject": "maths",
            "misconceptions": list(MISCONCEPTIONS),
            "bkt": {"p_init": 0.3, "p_learn": 0.15, "p_slip": 0.1, "p_guess": 0.25},
        },
    )
    for mid in MISCONCEPTIONS:
        _write(
            subject / "misconceptions" / f"{mid}.yaml",
            {
                "id": mid,
                "title": {"en": mid.replace("_", " ")},
                "explanation": {"en": "A common slip on this skill."},
                "remedial_skill": SKILL,
            },
        )
    _write(
        subject / "overlays" / f"{OVERLAY}.yaml",
        {
            "id": OVERLAY,
            "curriculum_id": "cbse",
            "grade": 10,
            "chapter": "quadratic",
            "skill_ids": [SKILL],
            "live": False,
            "section_map": {},
        },
    )
    return root, subject


def item_files(subject: Path) -> list[Path]:
    return sorted((subject / "items" / "factory" / "maths").glob("*.yaml"))
