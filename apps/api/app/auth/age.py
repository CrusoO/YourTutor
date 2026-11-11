"""The age question, asked as little as possible.

An adult learner answers with a birth year or with a plain "I am 18 or over" declaration. What is
kept is `StudentRow.is_adult` and, only when a birth year was the answer, `birth_year`. Nothing
else about age is stored (no day, no month). `learner_is_adult` in app/classes/service.py is the
one place that reads the answer; no other code decides who is an adult.

A birth year alone cannot tell whether someone aged 18 by year-difference has had their birthday,
so exactly that case needs the declaration as well. The year-difference is a floor, not proof:
age is self-declared (see the counsel questions in the pull request).
"""

from __future__ import annotations

from datetime import date

from fastapi import HTTPException

from app.auth.security import now_utc
from app.db.models import StudentRow

ADULT_AGE = 18
OLDEST_BIRTH_YEAR_GAP = 110


def resolve_is_adult(
    birth_year: int | None, declared_adult: bool | None, today: date | None = None
) -> bool:
    """Whether the answer means "18 or over". Raises ValueError for an answer that is not usable."""
    year = (today or now_utc().date()).year
    if birth_year is not None:
        gap = year - birth_year
        if gap < 0 or gap > OLDEST_BIRTH_YEAR_GAP:
            raise ValueError("birth_year out of range")
        if gap > ADULT_AGE:
            return True
        if gap < ADULT_AGE:
            return False
        # exactly 18 by year: adult only if the person says the birthday has passed
        return bool(declared_adult)
    if declared_adult is None:
        raise ValueError("age answer missing")
    return declared_adult


def record_age(student: StudentRow, birth_year: int | None, declared_adult: bool | None) -> bool:
    """Store the answer on the learner and return is_adult (HTTP 400 if it is not usable)."""
    try:
        adult = resolve_is_adult(birth_year, declared_adult)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
    student.is_adult = adult
    student.birth_year = birth_year
    return adult
