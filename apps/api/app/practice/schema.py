"""`step-check/1`: an equation and up to twelve written lines. Maths characters only.

There is no free-text field: a line is maths symbols plus a few words ("or", "and", "no real
roots"). Anything with another word is refused by the schema, and a refusal never echoes it.
"""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

SCHEMA_ID = "step-check/1"
MAX_BODY_BYTES = 4096
MAX_LINES = 12
MAX_LINE_CHARS = 160
MAX_QUESTION_CHARS = 64

_CHARS = re.compile(
    r"[0-9A-Za-z+\-*/^()=., \u2212\u2013\u2014\u00b1\u00b2\u00b3\u00d7\u00f7\u00b7]*"
)
_WORDS = re.compile(r"\b(or|and|no|real|roots?|solutions?|there|is|are)\b", re.IGNORECASE)

Line = Annotated[str, StringConstraints(strict=True, max_length=MAX_LINE_CHARS)]


def maths_only(text: str) -> bool:
    if not _CHARS.fullmatch(text):
        return False
    return not re.search(r"[A-Za-z]{2,}", _WORDS.sub(" ", text))


class StepCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_id: Literal["step-check/1"] = Field(alias="schema")
    question: Annotated[str, StringConstraints(strict=True, min_length=3, max_length=64)]
    lines: Annotated[list[Line], Field(min_length=1, max_length=MAX_LINES)]

    @field_validator("question")
    @classmethod
    def _question(cls, value: str) -> str:
        if value.count("=") != 1 or not maths_only(value):
            raise ValueError("question")
        return value

    @field_validator("lines")
    @classmethod
    def _lines(cls, values: list[str]) -> list[str]:
        if not all(maths_only(v) for v in values):
            raise ValueError("line")
        return values

    def canonical(self) -> str:
        return "\n".join([self.question, *self.lines])
