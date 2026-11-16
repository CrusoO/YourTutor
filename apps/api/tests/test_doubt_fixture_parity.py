"""TypeScript-produced doubt answers, re-verified by a Python reference and the factory kernel.

`packages/shared/fixtures/doubt/*.json` are written by `apps/web/tests/doubt/fixtures.test.ts`
(TypeScript solver). Here every answer is reproduced by `app.doubt.reference` (Fractions and
Python's own `ast`, no shared code) and, where the kernel has a kind for it, accepted by
`kernel.verify` using a witness the reference built. The kernel is the authority; the
TypeScript solver is untrusted.
"""

import json
import re
from fractions import Fraction
from pathlib import Path

import pytest

from app.ask.guard import _equations, _numbers  # noqa: PLC2701 - mirrored on the device, so parity-tested here
from app.doubt import reference as ref
from app.factory.kernel import verify

DIR = Path(__file__).resolve().parents[3] / "packages" / "shared" / "fixtures" / "doubt"


def load(name: str):
    return json.loads((DIR / name).read_text(encoding="utf-8"))


CASES = load("cases.json")


def test_fixtures_exist_and_are_large_enough():
    assert len(CASES) >= 100
    kinds = {c["kind"] for c in CASES}
    assert kinds == {"arith", "poly_eq", "poly_simplify", "linear_system"}
    statuses = {c["status"] for c in CASES}
    assert {"solved", "no_solution", "identity", "unsupported"} <= statuses


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["status"] != "unsupported"], ids=lambda c: c["id"]
)
def test_reference_reproduces_the_typescript_answer(case):
    mine = ref.solve_case(case)
    assert mine["status"] == case["status"], case["input"]
    ts = case["answer"]
    if ts["kind"] == "expr":  # the display string is TypeScript's; the coefficients are the answer
        assert mine["answer"]["coeffs"] == ts["coeffs"]
    else:
        assert mine["answer"] == ts, case["input"]
    if case["kind"] == "arith" and case["claimed"] is not None:
        assert mine["claimTrue"] == case["claimTrue"]


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["kind"] == "poly_eq"], ids=lambda c: c["id"]
)
def test_reference_reads_the_same_polynomials_as_typescript(case):
    left, right = ref.parse_poly(case["lhsText"]), ref.parse_poly(case["rhsText"])
    assert [str(c) for c in left] == case["lhs"]
    assert [str(c) for c in right] == case["rhs"]


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["status"] == "solved"], ids=lambda c: c["id"]
)
def test_kernel_accepts_the_typescript_answer(case):
    inputs = ref.kernel_inputs(case)
    if inputs is None:
        pytest.skip("the kernel has no kind for this case")
    spec, _, witness = inputs
    ts = case["answer"]
    if case["kind"] == "linear_system":
        answer = {"values": {"x": ts["x"], "y": ts["y"]}}
    else:
        answer = {"roots": ts["values"], "count": len(ts["values"])}
    verdict = verify(spec, answer, witness)
    assert verdict.accepted, (case["input"], verdict.code, verdict.detail)


@pytest.mark.parametrize(
    "case",
    [c for c in CASES if c["status"] == "no_solution" and c["kind"] == "poly_eq"],
    ids=lambda c: c["id"],
)
def test_kernel_certifies_no_real_roots(case):
    inputs = ref.kernel_inputs(case)
    if inputs is None:
        pytest.skip("not a rootless quadratic")
    spec, answer, witness = inputs
    assert verify(spec, answer, witness).accepted


def test_kernel_covers_a_meaningful_share_of_the_cases():
    covered = sum(
        1
        for c in CASES
        if c["status"] in {"solved", "no_solution"} and ref.kernel_inputs(c) is not None
    )
    assert covered >= 60


def test_kernel_rejects_a_tampered_answer():
    case = next(c for c in CASES if c["input"] == "x^2 - 5x + 6 = 0")
    spec, _, witness = ref.kernel_inputs(case)
    assert not verify(spec, {"roots": ["2"], "count": 1}, witness).accepted  # lost root
    assert not verify(spec, {"roots": ["2", "3", "4"], "count": 3}, witness).accepted  # extra root
    assert not verify(spec, {"roots": ["2", "4"], "count": 2}, witness).accepted  # wrong root


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["answer"]["kind"] == "surd"], ids=lambda c: c["id"]
)
def test_surd_roots_satisfy_the_equation_exactly(case):
    assert ref.check_surd_roots(case, case["answer"]["surds"]), case["input"]


def test_surd_text_is_canonical():
    assert ref.surd_text(Fraction(-1, 2), Fraction(1, 2), 5) == "-1/2+1/2√5"
    assert ref.surd_text(Fraction(0), Fraction(-1), 2) == "-√2"
    assert ref.surd_text(Fraction(0), Fraction(2), 2) == "2√2"


# ---- ladder, leak, detect, guard ----


def test_ladder_levels_one_to_three_hold_no_root():
    rows = load("ladder.json")
    assert rows
    checked = 0
    for row in rows:
        if row["status"] != "solved":
            continue
        roots = {abs(Fraction(v)) for v in row["answerValues"]}
        given = {Fraction(g) for g in row["given"]}
        for level in row["levels"]:
            if level["level"] == 4:
                continue
            for n in ref.numbers_in(level["text"]):
                assert n not in roots or n in given, (row["input"], level["level"], level["text"])
            checked += 1
        assert [lv["level"] for lv in row["levels"]][-1] == 4
    assert checked >= 60


def test_leak_fixture_has_the_seeded_faults_and_they_are_all_killed():
    rows = load("leak.json")
    faults = [r for r in rows if r["expect"] == "leak"]
    controls = [r for r in rows if r["expect"] == "clean"]
    assert len(faults) >= 14
    assert len({r["note"] for r in faults}) >= 14
    assert all(r["leaks"] for r in faults)
    assert controls and not any(r["leaks"] for r in controls)
    # Independent spot check: the plain-digit faults really do contain the root.
    digit_faults = [r for r in faults if r["id"] in {"f01", "f02"}]
    for r in digit_faults:
        assert re.search(r"\b2\b", r["text"])


def test_detect_fixture_phone_numbers_never_become_numbers():
    rows = load("detect.json")
    for row in rows:
        if re.search(r"\d{10}", row["input"].replace(" ", "").replace("-", "").replace("+", "")):
            assert row["lhs"] is None or all(len(c) < 7 for c in row["lhs"]), row
    assert any(r["result"] == "none" and "98765" in r["input"] for r in rows)
    assert not any(
        r["result"].startswith("candidate")
        for r in rows
        if r["input"].startswith(("my name", "I have", "what is the capital"))
    )


def test_guard_fixture_matches_the_server_ask_guard():
    data = load("guard.json")
    assert data["limits"]["maxDigits"] == 9
    for row in data["item"]:
        stem, question = row["stem"].lower(), row["question"].lower()
        compact = re.sub(r"\s+", "", question)
        expected = None
        if any(eq in compact for eq in _equations(stem)):
            expected = "stem_expression"
        elif len(_numbers(stem) & _numbers(question)) >= 2:
            expected = "stem_numbers"
        assert row["expect"] == expected, row
    for row in data["text"]:
        if row["ok"]:
            assert len(row["text"]) <= data["limits"]["maxChars"]
        else:
            assert row["why"] in {"too_long", "too_big_number", "huge_exponent"}
