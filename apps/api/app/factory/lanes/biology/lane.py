"""The biology lane: registers with the factory and renders items for the CLI and the pipeline."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from fractions import Fraction
from typing import Any

from app.factory.lanes.biology.common import AREA_OF_CHAPTER, Built, finish
from app.factory.lanes.biology.methods import methods_for
from app.factory.lanes.biology.models import ALL_MODELS, MISC
from app.factory.registry import ItemContext, register_lane

_LAST: dict[str, Any] = {"key": None, "value": None}


def resolver(chapter: str) -> Callable[[str], str]:
    area = AREA_OF_CHAPTER[chapter]

    def resolve(name: str) -> str:
        if name not in MISC[area]:
            raise KeyError(f"misconception {name} is not declared for {area}")
        return f"BIO.MC.{area}.{name}"

    return resolve


def build(template: Mapping[str, Any], params: Mapping[str, Any]) -> Built | str:
    model = ALL_MODELS[str(template["model"])]
    draft = model.build(params)
    if isinstance(draft, str):
        return draft
    return finish(model, params, draft, resolver(model.chapter))


def _built(template: Mapping[str, Any], params: Mapping[str, Any]) -> Built | str:
    key = json.dumps(template.get("model")) + json.dumps(dict(params), sort_keys=True)
    if _LAST["key"] != key:
        try:
            value: Built | str = build(template, params)
        except Exception as exc:  # noqa: BLE001 - a construction bug must be a visible failure
            raise RuntimeError(f"construction crashed: {type(exc).__name__}: {exc}") from exc
        _LAST.update(key=key, value=value)
    return _LAST["value"]  # type: ignore[no-any-return]


_SPACE = re.compile(r"\s+")


def _norm(text: str) -> str:
    return _SPACE.sub("", text.lower())


def _as_number(text: str) -> Fraction | None:
    cleaned = _norm(text).replace(",", "").rstrip("%")
    cleaned = re.sub(r"[a-z]+$", "", cleaned)
    try:
        return Fraction(cleaned)
    except (ValueError, ZeroDivisionError):
        return None


class BiologyLane:
    name = "biology"
    domain = "mixed"  # genetics crosses go to the kernel's genetics checker, the rest to algebra

    def box(self, template: Mapping[str, Any]) -> Mapping[str, Mapping[str, Any]]:
        return template["box"]  # type: ignore[no-any-return]

    def well_posed(self, template: Mapping[str, Any], params: Mapping[str, Any]) -> str | None:
        built = _built(template, params)
        return built if isinstance(built, str) else None

    def render(self, template: Mapping[str, Any], params: Mapping[str, Any]) -> ItemContext:
        built = _built(template, params)
        if isinstance(built, str):
            raise ValueError(f"ill-posed tuple rendered: {built}")
        d, model = built.draft, built.model
        return ItemContext(
            item_id=built.item_id,
            lane="biology",
            spec=d.spec,
            answer=d.answer,
            witness=d.witness,
            stem=d.stem,
            skill_ids=[model.skill],
            difficulty=d.difficulty,
            role=d.role,
            steps=d.steps,
            prediction=d.prediction,
            hints=d.hints,
            options=built.options,
            key_option="key",
            answer_tokens=d.tokens,
            provenance={"original": True, "features": d.features, "variant": d.variant},
            syllabus=dict(template["syllabus"]),
            methods=list(methods_for(model.id)),  # type: ignore[arg-type]
        )

    def check_student_answer(self, item: ItemContext, response: str) -> bool:
        key = next(str(o["text"]) for o in item.options if o["id"] == item.key_option)
        if _norm(response) == _norm(key):
            return True
        a, b = _as_number(response), _as_number(key)
        return a is not None and b is not None and a == b


LANE = register_lane(BiologyLane())
