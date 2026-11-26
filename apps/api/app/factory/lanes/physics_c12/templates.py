"""Item models (factory-template/1): one per skill, with its declared parameter box.

Values in a box are strings so decimals stay exact. `form` is the question form: mcq1 (1 mark),
num2 (2 marks), num3 (3 marks), case4 (4 marks, a short case). Every stamped item is a
multiple-choice presentation of a numerical answer.
"""

from __future__ import annotations

from typing import Any

from app.factory.lanes.physics_c12.boxes import BOXES
from app.factory.lanes.physics_c12.kit import GRADE, c
from app.factory.lanes.physics_c12.models import ALL_MODELS

FORMS = ["mcq1", "num2", "num3", "case4"]
FORBIDDEN = ["calculus", "graph_reading", "ray_diagram", "derivation", "free_text", "diagram"]


def make_template(model_id: str) -> dict[str, Any]:
    model = ALL_MODELS[model_id]
    return {
        "id": f"TPL2.{model.skill}",
        "schema": "factory-template/1",
        "lane": "physics_c12",
        "model": model.id,
        "skill_id": model.skill,
        "box": {"variant": c(*model.variants), "form": c(*FORMS), **BOXES[model_id]},
        "syllabus": {
            "grade": GRADE,
            "chapter_ref": model.chapter,
            "skill_id": model.skill,
            "allowed_methods": [model.technique],
            "forbidden_content": FORBIDDEN,
        },
    }


TEMPLATES: dict[str, dict[str, Any]] = {mid: make_template(mid) for mid in ALL_MODELS}
