"""Item models as factory-template/1 documents. The box lists every parameter choice as text."""

from __future__ import annotations

from typing import Any

from app.factory.lanes.biology.models import ALL_MODELS

FORBIDDEN = [
    "free_text",
    "assertion_reason",
    "fact_recall",
    "diagram",
    "calculus",
    "experiment_design",
]


def make_template(model_id: str) -> dict[str, Any]:
    model = ALL_MODELS[model_id]
    return {
        "id": f"TPL2.{model.skill}",
        "schema": "factory-template/1",
        "lane": "biology",
        "model": model.id,
        "skill_id": model.skill,
        "box": {name: {"choices": list(values)} for name, values in model.box.items()},
        "syllabus": {
            "grade": 10,
            "chapter_ref": model.chapter,
            "skill_id": model.skill,
            "allowed_methods": [model.technique, model.technique_b],
            "forbidden_content": FORBIDDEN,
        },
    }


def all_templates() -> dict[str, dict[str, Any]]:
    return {mid: make_template(mid) for mid in ALL_MODELS}
