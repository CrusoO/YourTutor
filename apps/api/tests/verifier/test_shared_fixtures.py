"""The shared verifier fixtures: Python is the authority, the TypeScript verifier must agree."""

from __future__ import annotations

import json

import pytest

from app.registries.paths import repo_root
from app.verifier.check import verify_response

PATH = repo_root() / "packages" / "shared" / "fixtures" / "verifier" / "cases.json"
CASES = json.loads(PATH.read_text(encoding="utf-8"))["cases"]


def test_the_fixture_is_not_empty_and_has_both_outcomes() -> None:
    assert len(CASES) >= 40
    assert {c["expected"] for c in CASES} == {True, False}


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
def test_python_gives_the_recorded_answer(case: dict) -> None:
    item = case["item"]
    got = verify_response(
        case["response"],
        answer_sympy=item["answer_sympy"],
        accept=item["accept"],
        item_type=item["type"],
        options=item["options"],
        notation_profile=case["profile"],
    )
    assert got is case["expected"]
