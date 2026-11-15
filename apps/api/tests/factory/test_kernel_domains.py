import copy

import pytest

from app.factory.kernel import verify
from app.factory.kernel.exact import Reject
from app.factory.kernel.stoichiometry import molar_mass, parse_formula
from app.factory.kernel.units import parse_unit, to_si

ALG = {"domain": "algebra", "kind": "polynomial", "lhs": [-6, -1, 1]}  # x^2 - x - 6 = 0
ALG_A = {"roots": [-2, 3], "count": 2}
ALG_W = {"split": {"lead": 1, "roots": [[3, 1], [-2, 1]]}}


def code(spec, answer, witness):
    return verify(spec, answer, witness).code


def test_algebra_accepts_and_rejects():
    assert code(ALG, ALG_A, ALG_W) == "ok"
    assert code(ALG, {"roots": [3], "count": 2}, ALG_W) == "root_set_mismatch"
    assert code(ALG, {"roots": [-3, 3]}, ALG_W) == "root_fails_substitution"
    assert code(ALG, {"roots": [3, 3]}, ALG_W) == "duplicate_root_in_answer"
    assert code(ALG, {"count": 1}, ALG_W) == "count_mismatch"
    assert code(ALG, {}, ALG_W) == "empty_answer"
    assert code(ALG, ALG_A, {}) == "missing_witness"
    bad_w = {"split": {"lead": 2, "roots": [[3, 1], [-2, 1]]}}
    assert code(ALG, ALG_A, bad_w) == "factorisation_mismatch"
    assert code({**ALG, "lhs": [1]}, {"count": 0}, ALG_W) == "degenerate_equation"


def test_algebra_double_root_and_multiplicity():
    spec = {"domain": "algebra", "kind": "polynomial", "lhs": [1, -2, 1]}
    ans = {"roots": [1], "count": 1, "multiplicity": {"1": 2}}
    wit = {"split": {"lead": 1, "roots": [[1, 2]]}}
    assert code(spec, ans, wit) == "ok"
    ans["multiplicity"] = {"1": 1}
    assert code(spec, ans, wit) == "multiplicity_mismatch"


def test_algebra_no_real_roots_by_discriminant():
    spec = {"domain": "algebra", "kind": "polynomial", "lhs": [1, 0, 1]}
    assert code(spec, {"roots": [], "count": 0}, {"discriminant": -4}) == "ok"
    assert code(spec, {"roots": [], "count": 2}, {"discriminant": -4}) == "count_mismatch"
    assert code(spec, {"roots": [], "count": 0}, {"discriminant": 4}) == "discriminant_mismatch"
    square = {"domain": "algebra", "kind": "polynomial", "lhs": [-1, 0, 1]}
    assert code(square, {"roots": [], "count": 2}, {"discriminant": 4}) == "roots_are_rational"


def test_linear_system():
    spec = {
        "domain": "algebra",
        "kind": "linear_system",
        "variables": ["x", "y"],
        "equations": [{"coeffs": [1, 1], "const": 5}, {"coeffs": [1, -1], "const": 1}],
    }
    ans = {"values": {"x": 3, "y": 2}}
    assert code(spec, ans, ans) == "ok"
    wrong = {"values": {"x": 2, "y": 3}}
    assert code(spec, wrong, wrong) == "equation_fails_substitution"
    singular = copy.deepcopy(spec)
    singular["equations"][1]["coeffs"] = [2, 2]
    assert code(singular, ans, ans) == "not_unique"


def test_formula_parser_and_molar_mass():
    assert parse_formula("Ca(OH)2") == {"Ca": 1, "O": 2, "H": 2}
    assert parse_formula("Fe2(SO4)3") == {"Fe": 2, "S": 3, "O": 12}
    assert molar_mass("H2O") == 18 and molar_mass("NaCl") == 58.5
    for bad in ("", "h2o", "Xx", "H0", "(H2", "H2)", "H-2"):
        with pytest.raises(Reject):
            parse_formula(bad)


BAL = {
    "domain": "stoichiometry",
    "kind": "balance",
    "species": [
        {"formula": "H2", "side": "L"},
        {"formula": "O2", "side": "L"},
        {"formula": "H2O", "side": "R"},
    ],
}
BAL_W = {"atom_counts": [{"H": 2}, {"O": 2}, {"H": 2, "O": 1}]}


def test_balance_checks():
    assert code(BAL, {"coefficients": [2, 1, 2]}, BAL_W) == "ok"
    assert code(BAL, {"coefficients": [1, 1, 1]}, BAL_W) == "not_balanced"
    assert code(BAL, {"coefficients": [4, 2, 4]}, BAL_W) == "not_smallest"
    assert code(BAL, {"coefficients": [2, 1, 0]}, BAL_W) == "bad_coefficients"
    wrong_w = {"atom_counts": [{"H": 2}, {"O": 2}, {"H": 3}]}
    assert code(BAL, {"coefficients": [2, 1, 2]}, wrong_w) == "witness_mismatch"


def test_ionic_charge_balance():
    spec = {
        "domain": "stoichiometry",
        "kind": "balance",
        "species": [
            {"formula": "Fe", "charge": 3, "side": "L"},
            {"formula": "Cu", "side": "L"},
            {"formula": "Fe", "charge": 2, "side": "R"},
            {"formula": "Cu", "charge": 2, "side": "R"},
        ],
    }
    wit = {"atom_counts": [{"Fe": 1}, {"Cu": 1}, {"Fe": 1}, {"Cu": 1}]}
    assert code(spec, {"coefficients": [2, 1, 2, 1]}, wit) == "ok"  # charge 6 = 4 + 2
    assert code(spec, {"coefficients": [1, 1, 1, 1]}, wit) == "not_balanced"


def test_unit_parser():
    assert to_si("36", "km/h")[0] == 10
    assert parse_unit("kg*m/s^2") == parse_unit("N")
    assert parse_unit("J/mol/K")[1] == parse_unit("kg*m^2/s^2/mol/K")[1]
    for bad in ("furlong", "", "m//s", "m^x"):
        with pytest.raises(Reject):
            parse_unit(bad)


def kin(given, find, unit, value, wit):
    spec = {"domain": "kinematics", "kind": "suvat", "given": given, "find": find}
    return code(spec, {"value": value, "unit": unit}, wit)


def test_kinematics_exact_and_unique():
    g = {
        "u": {"value": "0", "unit": "m/s"},
        "a": {"const": "g_earth"},
        "t": {"value": "3", "unit": "s"},
    }
    wit = {"s": "441/10", "u": 0, "v": "147/5", "a": "49/5", "t": 3}
    assert kin(g, "s", "m", "44.1", wit) == "ok"
    assert kin(g, "s", "m", "45", wit) == "value_mismatch"  # g = 10 slip
    assert kin(g, "s", "km", "44.1", wit) == "value_mismatch"
    assert kin(g, "s", "m/s", "44.1", wit) == "unit_dimension_mismatch"
    assert kin(g, "s", "m", "44.1", {**wit, "v": 0}) == "witness_mismatch"
    bad_dim = {**g, "t": {"value": "3", "unit": "m"}}
    assert kin(bad_dim, "s", "m", "44.1", wit) == "dimension_mismatch"
    assert kin({**g, "extra": 1}, "s", "m", "44.1", wit) in ("bad_given", "needs_three_given")


def test_kinematics_ambiguous_time_is_refused():
    # s = 6, u = 5, a = -2: t = 2 or t = 3, both physical, so the question has two answers
    given = {
        "s": {"value": "6", "unit": "m"},
        "u": {"value": "5", "unit": "m/s"},
        "a": {"value": "-2", "unit": "m/s^2"},
    }
    wit = {"s": 6, "u": 5, "v": 1, "a": -2, "t": 2}
    assert kin(given, "t", "s", "2", wit) == "ambiguous"


GEN = {"domain": "genetics", "kind": "cross", "parents": ["Aa", "Aa"], "ask": "phenotype"}
GEN_W = {"gametes": [["A", "a"], ["A", "a"]]}


def test_genetics():
    assert code(GEN, {"ratio": [3, 1]}, GEN_W) == "ok"
    assert code(GEN, {"probabilities": {"A": "3/4", "a": "1/4"}}, GEN_W) == "ok"
    assert code(GEN, {"probabilities": {"A": "1/2", "a": "1/2"}}, GEN_W) == "distribution_mismatch"
    assert code(GEN, {"ratio": [1, 1]}, GEN_W) == "ratio_mismatch"
    assert code({**GEN, "target": "a"}, {"probability": "1/4"}, GEN_W) == "ok"
    dihybrid = {**GEN, "parents": ["AaBb", "AaBb"]}
    wit = {"gametes": [["AB", "Ab", "aB", "ab"]] * 2}
    assert code(dihybrid, {"ratio": [9, 3, 3, 1]}, wit) == "ok"
    incomplete = {**GEN, "dominance": {"A": "incomplete"}}
    assert code(incomplete, {"ratio": [2, 1, 1]}, GEN_W) == "ok"  # 1 : 2 : 1
    mixed = {**GEN, "parents": ["Aa", "Bb"]}
    assert code(mixed, {"ratio": [1]}, GEN_W) == "loci_mismatch"


@pytest.mark.parametrize(
    "args",
    [
        (None, None, None),
        ({}, {}, {}),
        ({"domain": "nope"}, {}, {}),
        (
            {"domain": "algebra", "kind": "polynomial", "lhs": [0.5, 1]},
            {"roots": [1]},
            {"split": {}},
        ),
        ({"domain": "kinematics", "kind": "suvat", "given": "x", "find": "s"}, {}, {}),
        ({"domain": "genetics", "kind": "cross", "parents": ["A", "A"], "ask": "x"}, {}, {}),
        ({"domain": "stoichiometry", "kind": "balance", "species": [{"formula": "H2"}]}, {}, {}),
    ],
)
def test_fail_closed_on_garbage(args):
    verdict = verify(*args)
    assert not verdict.accepted and verdict.code


def test_timeout_fails_closed():
    gen = {**GEN, "parents": ["AaBbCcDd", "AaBbCcDd"]}
    assert verify(gen, {"ratio": [1]}, {"gametes": []}, timeout_s=-1).code == "timeout"
