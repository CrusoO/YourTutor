"""The Class 12 physics lane: registers with the factory and renders items for the CLI."""

from __future__ import annotations

import json
from collections.abc import Mapping
from fractions import Fraction
from typing import Any

from app.factory.lanes.physics_c12.build import Built, build, parse_value
from app.factory.lanes.physics_c12.methods import ClosedForm, SympyLaws
from app.factory.lanes.physics_c12.quantities import to_si, unit_si
from app.factory.registry import ItemContext, register_lane

_LAST: dict[str, Any] = {"key": None, "value": None}


def _built(template: Mapping[str, Any], params: Mapping[str, Any]) -> Built | str:
    key = json.dumps(template, sort_keys=True, default=str) + json.dumps(
        dict(params), sort_keys=True, default=str
    )
    if _LAST["key"] != key:
        try:
            value: Built | str = build(template, params)
        except Exception as exc:  # noqa: BLE001 - a construction bug must be a visible failure
            raise RuntimeError(f"construction crashed: {type(exc).__name__}: {exc}") from exc
        _LAST.update(key=key, value=value)
    return _LAST["value"]  # type: ignore[no-any-return]


class PhysicsC12Lane:
    name = "physics_c12"
    domain = "algebra"  # every item is checked by the kernel as an exact linear relation

    def box(self, template: Mapping[str, Any]) -> Mapping[str, Mapping[str, Any]]:
        return template["box"]  # type: ignore[no-any-return]

    def well_posed(self, template: Mapping[str, Any], params: Mapping[str, Any]) -> str | None:
        built = _built(template, params)
        return built if isinstance(built, str) else None

    def render(self, template: Mapping[str, Any], params: Mapping[str, Any]) -> ItemContext:
        built = _built(template, params)
        if isinstance(built, str):
            raise ValueError(f"ill-posed tuple rendered: {built}")
        technique = str(template["syllabus"]["allowed_methods"][0])
        return ItemContext(
            item_id=built.item_id,
            lane="physics_c12",
            spec=built.spec,
            answer=built.answer,
            witness=built.witness,
            stem=built.stem,
            skill_ids=[built.model.skill],
            difficulty=built.difficulty,
            role=built.role,
            steps=built.steps,
            prediction=built.prediction,
            hints=built.hints,
            options=built.options,
            key_option="key",
            answer_tokens=built.answer_tokens,
            provenance={
                "original": True,
                "form": built.form,
                "features": built.features,
                "kind": built.variant.kind,
            },
            syllabus=dict(template["syllabus"]),
            methods=[SympyLaws(technique), ClosedForm(technique)],
        )

    def check_student_answer(self, item: ItemContext, response: str) -> bool:
        parsed = parse_value(response)
        if parsed is None:
            return False
        value, unit = parsed
        phys = item.spec["physics"]
        key_unit = phys["answer_unit"]
        key = Fraction(str(item.answer["values"][phys["find"]]))
        try:
            if unit and unit != key_unit:
                return to_si(value, unit) == key * unit_si(key_unit)[0]
        except Exception:  # noqa: BLE001 - an unknown unit is simply not a match
            return False
        return value == key


LANE = register_lane(PhysicsC12Lane())
