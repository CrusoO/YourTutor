# ruff: noqa: E501
"""Template records (factory-template/1) for the registered models."""

from __future__ import annotations

from typing import Any

from app.factory.lanes.maths_c12.core import MODELS, Spec

KIND = {1: "mcq_direct", 2: "mcq_short", 3: "mcq_multi_step", 4: "mcq_case"}


def make_template(spec: Spec) -> dict[str, Any]:
    return {
        "id": spec.template_id,
        "short": "C12." + spec.short,
        "schema": "factory-template/1",
        "lane": "maths_c12",
        "family": spec.short,
        "family_version": spec.version,
        "skill_id": spec.skill_id,
        "box": spec.box,
        "form": {"marks": spec.marks, "kind": KIND[spec.marks]},
        "syllabus": {
            "grade": 12,
            "chapter_ref": spec.chapter,
            "skill_id": spec.skill_id,
            "allowed_methods": [spec.technique],
            "forbidden_content": spec.forbidden,
        },
    }


def all_templates() -> list[dict[str, Any]]:
    import app.factory.lanes.maths_c12.lane  # noqa: F401

    return [make_template(s) for s in MODELS.values()]
