"""`doubt-expr/1`: the only thing the doubt route accepts (ADR 0005, points 2 and 4).

A structured maths problem as exact numbers. There is no free-text field: every string is a number
in a fixed ASCII pattern of at most nine digits (so a phone or Aadhaar number cannot fit) or one of
a few enumerated words. Unknown keys are refused, and a refusal never echoes what was sent.
"""

from __future__ import annotations

import re
from fractions import Fraction
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

SCHEMA_ID = "doubt-expr/1"
MAX_BODY_BYTES = 2048
MAX_DEGREE = 4  # the device solver's cap too
_NUMBER = re.compile(r"-?[0-9]{1,9}(?:/[0-9]{1,9})?")

Num = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=20)]
Row = Annotated[list[Num], Field(min_length=2, max_length=2)]


def check_number(text: str) -> str:
    # fullmatch and [0-9], not \d: Unicode digits, a trailing newline or a plus sign never pass.
    if not _NUMBER.fullmatch(text):
        raise ValueError("number")
    if "/" in text and int(text.split("/")[1]) == 0:
        raise ValueError("zero denominator")
    return text


class System(BaseModel):
    """Two equations a*x + b*y = c."""

    model_config = ConfigDict(extra="forbid", strict=True)

    coeffs: Annotated[list[Row], Field(min_length=2, max_length=2)]
    consts: Row

    @field_validator("coeffs")
    @classmethod
    def _coeffs(cls, rows: list[list[str]]) -> list[list[str]]:
        return [[check_number(v) for v in row] for row in rows]

    @field_validator("consts")
    @classmethod
    def _consts(cls, values: list[str]) -> list[str]:
        return [check_number(v) for v in values]


Side = Annotated[list[Num], Field(min_length=1, max_length=MAX_DEGREE + 1)]


class DoubtExpr(BaseModel):
    """`poly_eq` carries `lhs` and `rhs` (coefficients, lowest degree first); `linear_system`
    carries `system`. Anything else is refused by the schema."""

    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=False)

    schema_id: Literal["doubt-expr/1"] = Field(alias="schema")
    kind: Literal["poly_eq", "linear_system"]
    lhs: Side | None = None
    rhs: Side | None = None
    system: System | None = None

    @field_validator("lhs", "rhs")
    @classmethod
    def _sides(cls, values: list[str] | None) -> list[str] | None:
        return None if values is None else [check_number(v) for v in values]

    def model_post_init(self, __context: object) -> None:
        if self.kind == "poly_eq":
            if self.lhs is None or self.rhs is None or self.system is not None:
                raise ValueError("shape")
        elif self.system is None or self.lhs is not None or self.rhs is not None:
            raise ValueError("shape")

    def groups(self) -> list[list[str]]:
        """The numbers of the request, grouped as they were sent."""
        if self.kind == "poly_eq":
            return [self.lhs or [], self.rhs or []]
        assert self.system is not None
        return [[v for row in self.system.coeffs for v in row], self.system.consts]

    def numbers(self) -> list[str]:
        return [n for g in self.groups() for n in g]

    def canonical(self) -> str:
        """Stable text of the request, for hashing only (never stored or logged as text)."""
        body = "|".join(",".join(str(Fraction(n)) for n in g) for g in self.groups())
        return f"{self.kind}|{body}"
