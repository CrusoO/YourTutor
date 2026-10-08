from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class ContentStatus(StrEnum):
    draft = "draft"
    approved = "approved"
    retired = "retired"


class ItemType(StrEnum):
    expression = "expression"
    numeric = "numeric"
    mcq = "mcq"
    short_text = "short_text"


class ItemRole(StrEnum):
    """What evidence an item can give the mastery ladder (ARCHITECTURE §9.5)."""

    recall = "recall"
    explain = "explain"
    procedure = "procedure"
    apply = "apply"
    transfer = "transfer"


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


class McqOption(BaseModel):
    id: str
    en: str
    ne: str | None = None
    as_: str | None = Field(default=None, alias="as")

    model_config = {"populate_by_name": True}


class VerifySpec(BaseModel):
    kind: str = "equation"
    expr: str | None = None
    equation: str | None = None
    value: str | None = None
    unknown: str | None = None


class MisconceptionRule(BaseModel):
    id: str
    when_answer_equals: list[str]


class SlipPattern(BaseModel):
    """An authored set of answers that look like a slip, not a misunderstanding (G2)."""

    model_config = {"extra": "forbid"}

    kind: Literal["values", "sign_flip", "off_by"]
    values: list[str] = []
    max_distance: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def values_need_values(self) -> SlipPattern:
        if self.kind == "values" and not self.values:
            raise ValueError("a `values` slip pattern needs values")
        return self


class PrereqSignature(BaseModel):
    """Answers that point at a gap in a prerequisite skill (G2)."""

    model_config = {"extra": "forbid"}

    skill_id: str
    values: list[str] = Field(min_length=1)


class Item(BaseModel):
    id: str
    skill_ids: list[str] = Field(min_length=1)
    difficulty: float = Field(ge=0, le=1)
    type: ItemType
    pool: ItemPool
    role: ItemRole
    stem: LocalizedText
    verify: str | VerifySpec | None = None
    options: list[McqOption] = []
    answer: Answer
    solution_steps: list[LocalizedText]
    hints: list[Hint]
    prediction_prompt: LocalizedText
    misconception_rules: list[MisconceptionRule] = []
    # G2 diagnosis and stuck-point fields (all optional)
    slip_patterns: list[SlipPattern] = []
    prereq_signatures: list[PrereqSignature] = []
    intermediate_values: list[str] = []
    min_plausible_ms: int | None = Field(default=None, ge=500)
    step_hints: list[LocalizedText] = []
    hint_restate: LocalizedText | None = None
    reviewed_by: str | None = None
    content_hash: str | None = None
    status: ContentStatus = ContentStatus.draft
    template_id: str | None = None
    generator_version: str | None = None
    template_hash: str | None = None

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
        if self.step_hints and len(self.step_hints) != len(self.solution_steps):
            raise ValueError(f"{self.id} step_hints must match solution_steps one to one")
        if self.type == ItemType.mcq:
            ids = [o.id for o in self.options]
            if len(ids) < 2:
                raise ValueError(f"{self.id} mcq must have at least two options")
            if self.answer.sympy not in ids:
                raise ValueError(f"{self.id} answer is not an option id")
        return self


class Misconception(BaseModel):
    id: str
    title: LocalizedText
    explanation: LocalizedText
    remedial_skill: str
    status: ContentStatus = ContentStatus.draft


class Overlay(BaseModel):
    model_config = {"extra": "forbid"}  # a leftover `board:` must fail loudly

    id: str
    curriculum_id: str
    grade: int
    chapter: str
    skill_ids: list[str]
    live: bool = False
    section_map: dict[str, list[str]] = Field(default_factory=dict)


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


class ItemTemplate(BaseModel):
    id: str
    skill_id: str
    role: ItemRole
    structure: str
    parameters: dict[str, Any]
    derived: dict[str, str] = {}
    constraints: dict[str, Any] = {}
    answer_expr: str
    stem: str
    verify: str | dict[str, Any] | None = None
    type: ItemType = ItemType.expression
    options: list[McqOption] = []
    prediction: str
    steps: list[str]
    hints: dict[int, str] | dict[str, str]
    misconceptions: list[dict[str, str]] = []
    tier_rules: list[dict[str, Any]]
    status: ContentStatus = ContentStatus.draft
    reviewed_by: str | None = None
    content_hash: str | None = None


class ContentBundle(BaseModel):
    skills: list[Skill]
    items: list[Item]
    misconceptions: list[Misconception]
    overlays: list[Overlay]
    glossaries: list[GlossaryFile]
    checkpoint_forms: list[CheckpointForms]
    templates: list[ItemTemplate] = []
