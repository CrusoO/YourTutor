# ruff: noqa: E501
"""The Class 12 maths lane (calculation-checked, draft). Registers lane `maths_c12`.

Same pattern as the Class 10 maths lane: a template (factory-template/1) names a model and its
parameter box; the model builds an item backward from a tuple; independent methods recompute the
answer from the structured model in the spec; the kernel checks the encoded relation.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from fractions import Fraction
from typing import Any

from app.factory.kernel.exact import chash
from app.factory.lanes.maths.core import Built, Family, IllPosed, distinct_wrong, hint_problems
from app.factory.lanes.maths_c12 import models  # noqa: F401  (registers every model)
from app.factory.lanes.maths_c12.core import FAMILIES
from app.factory.registry import ItemContext, register_lane

LANE_NAME = "maths_c12"


def _item_id(template: Mapping[str, Any], slug: str) -> str:
    base = f"{template['short']}.{slug}"
    if len(base) > 78 or not re.fullmatch(r"[A-Za-z0-9_.:-]+", base):
        base = f"{template['short']}.{chash(slug)[:12]}"
    return base


def _squash(text: str) -> str:
    return re.sub(r"\s+", "", text.lower().replace("−", "-").replace("sqrt", "√"))


class MathsC12Lane:
    name = LANE_NAME
    domain = "algebra"

    def box(self, template: Mapping[str, Any]) -> Mapping[str, Mapping[str, Any]]:
        return template["box"]  # type: ignore[no-any-return]

    def family(self, template: Mapping[str, Any]) -> Family:
        fam = FAMILIES[template["family"]]
        if str(template.get("family_version")) != fam.version:
            raise ValueError(
                f"{template['id']}: family_version {template.get('family_version')!r} != "
                f"code {fam.version!r}"
            )
        return fam

    def _build(self, template: Mapping[str, Any], params: Mapping[str, Any]) -> Built:
        return self.family(template).build(template, params)

    def well_posed(self, template: Mapping[str, Any], params: Mapping[str, Any]) -> str | None:
        try:
            built = self._build(template, params)
        except IllPosed as why:
            return str(why)
        if len(distinct_wrong(built.answer, built.key_text, built.wrong, chash)) < 3:
            return "fewer_than_three_distinct_wrong_options"
        return hint_problems(built.stem, built.hints)

    def render(self, template: Mapping[str, Any], params: Mapping[str, Any]) -> ItemContext:
        built = self._build(template, params)
        wrong = distinct_wrong(built.answer, built.key_text, built.wrong, chash)
        options = [
            {"id": "key", "value": built.answer, "text": built.key_text, "procedure": "correct"}
        ]
        options += [
            {"id": f"d{i}", "value": rec, "text": text, "procedure": mc}
            for i, (mc, rec, text) in enumerate(wrong, start=1)
        ]
        return ItemContext(
            item_id=_item_id(template, built.slug),
            lane=LANE_NAME,
            spec=built.spec,
            answer=built.answer,
            witness=built.witness,
            stem=built.stem,
            skill_ids=[template["skill_id"]],
            difficulty=built.difficulty,
            role=built.role,
            steps=built.steps,
            prediction=built.prediction,
            hints=built.hints,
            options=options,
            key_option="key",
            answer_tokens=built.tokens,
            provenance={"original": True},
            syllabus=dict(template["syllabus"]),
            content_tags=built.tags,
            methods=built.methods,
        )

    def check_student_answer(self, item: ItemContext, response: str) -> bool:
        """Typed answers: the key as shown, or the same number written as a fraction or decimal."""
        key = next((o["text"] for o in item.options if o["id"] == item.key_option), "")
        if _squash(response) == _squash(str(key)):
            return True
        try:
            return Fraction(response.strip().replace("−", "-")) == Fraction(str(key))
        except (ValueError, ZeroDivisionError):
            return False


LANE = register_lane(MathsC12Lane())
__all__ = ["LANE", "IllPosed"]
