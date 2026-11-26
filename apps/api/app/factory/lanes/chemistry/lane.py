# ruff: noqa: E501
"""The chemistry lane: dispatches a template to its family and builds the ItemContext.

Template = a small YAML file (factory-template/1): id, short, lane, family, family_version,
skill_id, parameter box and syllabus (chapter, allowed methods, forbidden content). The family
holds the generator; `family_version` in the template must match the code, so a change of
generator logic changes the template hash and invalidates old certificates.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from app.factory.kernel.exact import chash
from app.factory.lanes.chemistry.acids import ACID_FAMILIES
from app.factory.lanes.chemistry.balance import BALANCE_FAMILIES
from app.factory.lanes.chemistry.carbon import CARBON_FAMILIES
from app.factory.lanes.chemistry.core import Built, Family, IllPosed, distinct_wrong, hint_problems
from app.factory.lanes.chemistry.metals import METAL_FAMILIES
from app.factory.registry import ItemContext, register_lane

FAMILIES: dict[str, Family] = {
    **BALANCE_FAMILIES,
    **ACID_FAMILIES,
    **METAL_FAMILIES,
    **CARBON_FAMILIES,
}
LANE_NAME = "chemistry"
_CACHE: dict[str, Any] = {"key": None, "value": None}


def _item_id(template: Mapping[str, Any], slug: str) -> str:
    base = f"ITM.{template['short']}.{slug}".replace(":", "_")
    if len(base) > 78 or not re.fullmatch(r"[A-Za-z0-9_.:-]+", base):
        base = f"ITM.{template['short']}.{chash(slug)[:12]}"
    return base


class ChemistryLane:
    name = LANE_NAME
    domain = "stoichiometry"  # balance and mass items; the rest are exact linear relations

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

    def _build(self, template: Mapping[str, Any], params: Mapping[str, Any]) -> Built | str:
        key = chash({"t": str(template["id"]), "p": dict(params)})
        if _CACHE["key"] != key:
            try:
                value: Built | str = self.family(template).build(template, params)
            except IllPosed as why:
                value = str(why)
            _CACHE.update(key=key, value=value)
        return _CACHE["value"]  # type: ignore[no-any-return]

    def well_posed(self, template: Mapping[str, Any], params: Mapping[str, Any]) -> str | None:
        built = self._build(template, params)
        if isinstance(built, str):
            return built
        if len(distinct_wrong(built.answer, built.key_text, built.wrong, chash)) < 3:
            return "fewer_than_three_distinct_wrong_options"
        return hint_problems(built.stem, built.hints, built.tokens)

    def render(self, template: Mapping[str, Any], params: Mapping[str, Any]) -> ItemContext:
        built = self._build(template, params)
        if isinstance(built, str):
            raise ValueError(f"ill-posed tuple rendered: {built}")
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
        """Multiple choice only: the typed text equals the key option's text (spacing ignored)."""
        key = next((o for o in item.options if o["id"] == item.key_option), None)
        if key is None:
            return False

        def squash(s: str) -> str:
            return re.sub(r"\s+", "", s.lower())

        return squash(response) == squash(str(key["text"]))


LANE = ChemistryLane()
register_lane(LANE)
