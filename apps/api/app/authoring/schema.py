"""The compact draft file (frozen format). Strict: unknown keys are errors."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Subject = Literal["maths", "physics", "chemistry", "biology"]
SUBJECTS: tuple[str, ...] = ("maths", "physics", "chemistry", "biology")
Difficulty = Literal["easy", "medium", "hard"]
Role = Literal["recall", "explain", "procedure", "apply", "transfer"]
Confidence = Literal["high", "medium", "low"]


class DraftWrong(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    mistake: str = Field(min_length=1)


class DraftItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str = Field(min_length=1)
    type: Literal["mcq", "numeric"]
    difficulty: Difficulty
    role: Role
    stem: str = Field(min_length=1)
    correct: str = Field(min_length=1)
    unit: str = ""
    wrong: list[DraftWrong] = []
    explanation: str = Field(min_length=1)
    hints: list[str]
    diagram: str | None = None
    confidence: Confidence

    @model_validator(mode="after")
    def shape(self) -> DraftItem:
        if self.type == "mcq" and len(self.wrong) != 3:
            raise ValueError("an mcq needs exactly 3 wrong options")
        if self.type == "numeric" and self.wrong:
            raise ValueError("a numeric item has no wrong options")
        if self.type == "mcq" and self.unit:
            raise ValueError("unit is for numeric items only")
        if len(self.hints) != 3 or any(not h.strip() for h in self.hints):
            raise ValueError("exactly 3 non-empty hints are needed")
        if self.diagram is not None and not self.diagram.strip():
            raise ValueError("diagram must be null or a description")
        return self


class DraftFile(BaseModel):
    class_: int = Field(alias="class", ge=9, le=12)
    subject: Subject
    chapter: str = Field(min_length=1)
    drafted_by: str = Field(min_length=1)
    items: list[DraftItem] = Field(min_length=1)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
