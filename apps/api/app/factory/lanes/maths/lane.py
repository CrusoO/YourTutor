# ruff: noqa: E501
"""The Class 10 maths lane: dispatches a template to its family and builds the ItemContext.

Template = a small YAML file (factory-template/1): id, lane, family, family_version, skill_id,
parameter box, syllabus (allowed methods, forbidden content), form (marks). The family holds the
generator; `family_version` in the template must match the code (a test enforces it), so a change
of generator logic changes the template hash and invalidates old certificates.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from fractions import Fraction
from typing import Any

from app.factory.kernel.exact import chash
from app.factory.lanes.maths.ap import AP_FAMILIES
from app.factory.lanes.maths.core import Built, Family, IllPosed, distinct_wrong, hint_problems
from app.factory.lanes.maths.lin2 import LIN2_FAMILIES
from app.factory.lanes.maths.quad import QUAD_FAMILIES
from app.factory.lanes.maths.trig import TRIG_FAMILIES
from app.factory.registry import ItemContext, register_lane

FAMILIES: dict[str, Family] = {**QUAD_FAMILIES, **AP_FAMILIES, **TRIG_FAMILIES, **LIN2_FAMILIES}
LANE_NAME = "maths_c10"


def _item_id(template: Mapping[str, Any], slug: str) -> str:
    base = f"{template['short']}.{slug}"
    if len(base) > 78 or not re.fullmatch(r"[A-Za-z0-9_.:-]+", base):
        base = f"{template['short']}.{chash(slug)[:12]}"
    return base


class MathsC10Lane:
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
        """Typed answers: a value, or a list of roots. Spacing, case and 'x =' are ignored."""
        text = response.strip().lower().replace("−", "-").replace("sqrt", "√")
        value = str(item.answer.get("value", ""))

        def squash(s: str) -> str:
            return re.sub(r"\s+", "", s.lower().replace("sqrt", "√"))

        if "roots" in item.answer and value.startswith("x ="):
            try:
                parts = re.split(r"\s*(?:,|;|\bor\b|\band\b)\s*", text)
                given = {
                    Fraction(part.strip().removeprefix("x").strip().removeprefix("=").strip())
                    for part in parts
                    if part.strip()
                }
            except (ValueError, ZeroDivisionError):
                return False
            return given == {Fraction(r) for r in item.answer["roots"]}
        return squash(text) == squash(value) or squash(text).removeprefix("x=") == squash(
            value
        ).removeprefix("x=")


LANE = register_lane(MathsC10Lane())
