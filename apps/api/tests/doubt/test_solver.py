"""Server doubt solver: differential against the web fixtures, properties, kernel honesty."""

from __future__ import annotations

import json
import random
from fractions import Fraction
from pathlib import Path

import pytest

from app.doubt.schema import DoubtExpr
from app.doubt.solver import LABEL_CHECKED, solve_doubt

FIX = Path(__file__).resolve().parents[4] / "packages" / "shared" / "fixtures" / "doubt"
CASES = json.loads((FIX / "cases.json").read_text(encoding="utf-8"))
TIDY = {"expand_bracket", "collect_like_terms"}  # depend on how the student wrote it; not sent


def request_of(case: dict) -> DoubtExpr | None:
    if case["kind"] == "poly_eq" and case["lhs"] is not None:
        body = {"schema": "doubt-expr/1", "kind": "poly_eq", "lhs": case["lhs"], "rhs": case["rhs"]}
    elif case["kind"] == "linear_system":
        body = {
            "schema": "doubt-expr/1",
            "kind": "linear_system",
            "system": {"coeffs": case["system"]["coeffs"], "consts": case["system"]["consts"]},
        }
    else:
        return None
    try:
        return DoubtExpr.model_validate(body)
    except ValueError:
        return None  # a number the schema refuses (more than nine digits)


SHARED = [c for c in CASES if c["kind"] in {"poly_eq", "linear_system"} and request_of(c)]


def test_there_are_shared_fixtures() -> None:
    assert len(SHARED) >= 45


@pytest.mark.parametrize("case", SHARED, ids=lambda c: c["id"])
def test_server_agrees_with_the_web_solver(case: dict) -> None:
    out = solve_doubt(request_of(case))  # type: ignore[arg-type]
    ts = case["answer"]
    if case["status"] == "solved" and ts["kind"] == "values":
        if out["verified"]:
            assert out["answer"]["values"] == ts["values"], case["input"]
    if case["status"] == "solved" and ts["kind"] == "pair":
        assert out["verified"], case["input"]
        assert (out["answer"]["x"], out["answer"]["y"]) == (ts["x"], ts["y"])
    if out["verified"]:
        want = [r for r in case["rules"] if r not in TIDY]
        assert [s["rule"] for s in out["steps"]] == want, case["input"]
    if case["status"] == "solved" and ts["kind"] == "surd":
        assert not out["verified"] and out["reason"] == "irrational_roots"


def test_most_shared_cases_are_verified() -> None:
    outs = [solve_doubt(r) for r in map(request_of, SHARED) if r is not None]
    verified = len([o for o in outs if o["verified"]])
    assert verified >= 35


def make(kind: str, **kw: object) -> DoubtExpr:
    return DoubtExpr.model_validate({"schema": "doubt-expr/1", "kind": kind, **kw})


def test_never_true_is_an_honest_could_not_check() -> None:
    out = solve_doubt(make("poly_eq", lhs=["3", "2"], rhs=["5", "2"]))
    assert out["verified"] is False and out["label"] == "not_verified"
    assert out["answer"] is None and out["steps"] == []


def test_irrational_roots_are_not_labelled_checked() -> None:
    out = solve_doubt(make("poly_eq", lhs=["-2", "0", "1"], rhs=["0"]))
    assert out == {**out, "verified": False, "reason": "irrational_roots", "answer": None}


def test_only_kernel_accepted_results_carry_the_label(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.doubt.solver as s

    req = make("poly_eq", lhs=["-6", "1", "1"], rhs=["0"])
    assert solve_doubt(req)["label"] == LABEL_CHECKED
    real = s.verify

    def reject(*a: object, **k: object):  # type: ignore[no-untyped-def]
        v = real(*a, **k)  # type: ignore[arg-type]
        return type(v)(False, "forced", "", v.domain, v.checker_version, {})

    monkeypatch.setattr(s, "verify", reject)
    out = solve_doubt(req)
    assert out["label"] == "not_verified" and out["answer"] is None and out["steps"] == []


def test_property_random_linear_equations_verified_by_substitution() -> None:
    rng = random.Random(20261118)
    for _ in range(300):
        a = rng.choice([n for n in range(-9, 10) if n])
        b, c, d = (rng.randint(-20, 20) for _ in range(3))
        if a == c:
            continue
        out = solve_doubt(make("poly_eq", lhs=[str(b), str(a)], rhs=[str(d), str(c)]))
        assert out["verified"], (a, b, c, d)
        x = Fraction(out["answer"]["values"][0])
        assert a * x + b == c * x + d


def test_property_random_quadratics_roots_verified_by_substitution() -> None:
    rng = random.Random(7)
    for _ in range(300):
        r1, r2 = Fraction(rng.randint(-9, 9), rng.randint(1, 4)), Fraction(rng.randint(-9, 9))
        lead = rng.choice([1, 2, -1, 3])
        # lead*(x - r1)(x - r2), cleared of denominators
        p = [lead * r1 * r2, -lead * (r1 + r2), Fraction(lead)]
        den = 1
        for c in p:
            den = den * c.denominator // __import__("math").gcd(den, c.denominator)
        coeffs = [str(int(c * den)) for c in p]
        out = solve_doubt(make("poly_eq", lhs=coeffs, rhs=["0"]))
        assert out["verified"], coeffs
        got = {Fraction(v) for v in out["answer"]["values"]}
        assert got == {r1, r2}
        for x in got:
            assert sum(Fraction(c) * x**i for i, c in enumerate(coeffs)) == 0


def test_property_random_systems() -> None:
    rng = random.Random(11)
    for _ in range(200):
        a1, b1, a2, b2 = (rng.randint(-6, 6) for _ in range(4))
        if a1 * b2 - a2 * b1 == 0:
            continue
        x, y = rng.randint(-9, 9), rng.randint(-9, 9)
        c1, c2 = a1 * x + b1 * y, a2 * x + b2 * y
        out = solve_doubt(
            make(
                "linear_system",
                system={
                    "coeffs": [[str(a1), str(b1)], [str(a2), str(b2)]],
                    "consts": [str(c1), str(c2)],
                },
            )
        )
        assert out["verified"]
        assert (out["answer"]["x"], out["answer"]["y"]) == (str(x), str(y))
