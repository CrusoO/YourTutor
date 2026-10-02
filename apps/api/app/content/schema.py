from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class ContentStatus(StrEnum):
    draft = "draft"
    approved = "approved"


class ItemType(StrEnum):
    expression = "expression"
    numeric = "numeric"
    mcq = "mcq"
    short_text = "short_text"


class ItemPool(StrEnum):
    practice = "practice"
    diagnostic = "diagnostic"
    checkpoint = "checkpoint"


class LocalizedText(BaseModel):
    en: str
    ne: str | None = None
    as_: str | None = Field(default=None, alias="as")

    model_config = {"populate_by_name": True}

    def as_dict(self) -> dict[str, str | None]:
        return {"en": self.en, "ne": self.ne, "as": self.as_}


class BktParams(BaseModel):
    p_init: float = Field(ge=0, le=1)
    p_learn: float = Field(ge=0, le=1)
    p_slip: float = Field(ge=0, le=1)
    p_guess: float = Field(ge=0, le=1)


class Skill(BaseModel):
    id: str
    title: LocalizedText
    grade_band: list[int]
    subject: str
    prerequisites: list[str] = []
    related: list[str] = []
    misconceptions: list[str] = []
    bkt: BktParams
    status: ContentStatus = ContentStatus.draft


class Hint(BaseModel):
    level: int = Field(ge=1, le=3)
    en: str
    ne: str | None = None
    as_: str | None = Field(default=None, alias="as")

    model_config = {"populate_by_name": True}

    def localized(self) -> LocalizedText:
        return LocalizedText.model_validate({"en": self.en, "ne": self.ne, "as": self.as_})


class Answer(BaseModel):
    sympy: str
    accept: list[str] = []


class MisconceptionRule(BaseModel):
    id: str
    when_answer_equals: list[str]


class Item(BaseModel):
    id: str
    skill_ids: list[str] = Field(min_length=1)
    difficulty: float = Field(ge=0, le=1)
    type: ItemType
    pool: ItemPool
    stem: LocalizedText
    answer: Answer
    solution_steps: list[LocalizedText]
    hints: list[Hint]
    prediction_prompt: LocalizedText
    misconception_rules: list[MisconceptionRule] = []
    reviewed_by: str | None = None
    status: ContentStatus = ContentStatus.draft

    @property
    def primary_skill(self) -> str:
        return self.skill_ids[0]

    @model_validator(mode="after")
    def require_three_hints(self) -> Item:
        levels = sorted(h.level for h in self.hints)
        if levels != [1, 2, 3]:
            raise ValueError(f"{self.id} must have hint levels 1, 2, and 3")
        if not self.solution_steps:
            raise ValueError(f"{self.id} must have solution_steps")
        return self


class Misconception(BaseModel):
    id: str
    title: LocalizedText
    explanation: LocalizedText
    remedial_skill: str
    status: ContentStatus = ContentStatus.draft


class Overlay(BaseModel):
    id: str
    board: str
    grade: int
    chapter: str
    skill_ids: list[str]
    live: bool = False


class CheckpointForms(BaseModel):
    id: str
    checkpoint_id: str
    form_a: list[str] = Field(alias="A")
    form_b: list[str] = Field(alias="B")
    match_map: dict[str, str]

    model_config = {"populate_by_name": True}

    @field_validator("match_map")
    @classmethod
    def match_covers_a(cls, value: dict[str, str], info: Any) -> dict[str, str]:
        return value


class GlossaryFile(BaseModel):
    language: str
    terms: dict[str, str]


class ContentBundle(BaseModel):
    skills: list[Skill]
    items: list[Item]
    misconceptions: list[Misconception]
    overlays: list[Overlay]
    glossaries: list[GlossaryFile]
    checkpoint_forms: list[CheckpointForms]
