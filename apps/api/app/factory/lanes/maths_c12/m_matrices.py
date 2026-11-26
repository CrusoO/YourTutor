# ruff: noqa: E501
"""Matrices and determinants."""

from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction
from typing import Any

import sympy

from app.factory.lanes.maths_c12 import kit
from app.factory.lanes.maths_c12.core import (
    Built,
    F,
    IllPosed,
    case,
    fr,
    hints3,
    mat_text,
    model,
    pick,
    poly_text,
)  # fmt: skip
from app.factory.lanes.maths_c12.m_rf_itf import slug

CH = "cbse.12.maths."
MAT, DET = CH + "matrices", CH + "determinants"
PRE_ARITH = "MATH.C12.PRE.INTEGER_ARITHMETIC"


def _seeded(seed: int, rows: int, cols: int, lo: int = -3, hi: int = 3, salt: int = 0) -> kit.Mat:
    flat = kit.lcg(seed * 7 + salt, rows * cols, lo, hi)
    return [[F(flat[r * cols + c]) for c in range(cols)] for r in range(rows)]


def _M(md: Mapping[str, Any], key: str) -> kit.Mat:
    return kit.mat(md[key])


def _txt(m: kit.Mat) -> list[list[str]]:
    return [[fr(x) for x in r] for r in m]


def _flat(m: kit.Mat) -> tuple[Fraction, ...]:
    return tuple(x for r in m for x in r)


def _m2(v: tuple[Fraction, ...]) -> str:
    return mat_text([v[0:2], v[2:4]])


# ================================================================ MAT.PRODUCT


def _operands(md: Mapping[str, Any]) -> tuple[kit.Mat, kit.Mat]:
    a, b = _M(md, "A"), _M(md, "B")
    return {"AB": (a, b), "BA": (b, a), "A2": (a, a)}[md["op"]]


def _mp_hand(md: Mapping[str, Any]) -> tuple[Fraction, ...]:
    left, right = _operands(md)
    return _flat(
        [
            [sum((left[i][k] * right[k][j] for k in range(2)), F(0)) for j in range(2)]
            for i in range(2)
        ]
    )


def _mp_sympy(md: Mapping[str, Any]) -> tuple[Fraction, ...]:
    left, right = _operands(md)
    prod = kit.smat(left) * kit.smat(right)
    return tuple(kit.unsp(prod[i, j]) for i in range(2) for j in range(2))


def _mp_columns(md: Mapping[str, Any]) -> tuple[Fraction, ...]:
    """Each column of the product is a combination of the columns of the left matrix."""
    left, right = _operands(md)
    cols = [
        [sum((right[k][j] * left[i][k] for k in range(2)), F(0)) for i in range(2)]
        for j in range(2)
    ]
    return tuple(cols[j][i] for i in range(2) for j in range(2))


@model(
    "MAT.PRODUCT", chapter=MAT, title="Multiply two 2 by 2 matrices", prereq=[PRE_ARITH], marks=2,
    technique="row_by_column",
    box={"sa": {"min": 0, "max": 11}, "sb": {"min": 0, "max": 9}, "op": {"choices": ["AB", "BA", "A2"]}},
)  # fmt: skip
def mat_product(p: Mapping[str, Any]) -> Built:
    sa, sb, op = int(p["sa"]), int(p["sb"]), str(p["op"])
    if op == "A2" and sb != 0:
        raise IllPosed("second_matrix_unused")
    a, b = _seeded(sa, 2, 2), _seeded(sb, 2, 2, salt=101)
    if op != "A2" and a == b:
        raise IllPosed("matrices_identical")
    md = {"A": _txt(a), "B": _txt(b), "op": op}
    key = _mp_hand(md)
    left, right = _operands(md)
    ent = [[left[i][j] * right[i][j] for j in range(2)] for i in range(2)]
    rowrow = [
        [sum((left[i][k] * right[j][k] for k in range(2)), F(0)) for j in range(2)]
        for i in range(2)
    ]
    wrong = [
        ("MC.C12.MAT.ENTRYWISE_PRODUCT", _flat(ent)),
        ("MC.C12.MAT.PRODUCT_ORDER_REVERSED", _flat(kit.matmul(right, left))),
        ("MC.C12.MAT.ROW_TIMES_ROW", _flat(rowrow)),
        ("MC.C12.MAT.RESULT_TRANSPOSED", _flat(kit.transpose(kit.matmul(left, right)))),
    ]
    title = {"AB": "A B", "BA": "B A", "A2": "A²"}[op]
    stem = (
        f"Let A = {mat_text(a)}"
        + (f" and B = {mat_text(b)}" if op != "A2" else "")
        + f". Find {title}."
    )
    return case(
        fam="MAT.PRODUCT", md=md, names=["m11", "m12", "m21", "m22"], value=key, fmt=_m2, stem=stem,
        steps=["Each entry of the product is one row of the left matrix times one column of the right matrix: multiply matching entries and add.", f"Fill the four entries this way: the result is {_m2(key)}."],
        hints=hints3(p, ["Which matrix is on the left, and does the order matter here?", "Each entry uses one whole row and one whole column.", "Look at the order first, then decide which row meets which column."],
                     "For the entry in row i and column j, take row i of the left matrix and column j of the right matrix, multiply matching entries and add.",
                     "Full method: compute the four entries one at the time, each as the sum of two products, and keep the left-right order exactly as written."),
        wrong=wrong, base=0.3, role="apply", prediction="Will the product be the same if you swap the order?",
        slug=slug(sa, sb, op), nsteps=4,
        methods=[("c12.mat.product.row_col", "closed_form", "row_by_column", _mp_hand),
                 ("c12.mat.product.sympy", "sympy.matrix", "", _mp_sympy),
                 ("c12.mat.product.columns", "column_combination", "", _mp_columns)],
    )  # fmt: skip


# ================================================================ MAT.SYMMETRIC_UNKNOWN


def _cells(md: Mapping[str, Any]) -> list[list[tuple[int, int]]]:
    return [[(int(a), int(b)) for a, b in row] for row in md["cells"]]


def _sym_solve(cells: list[list[tuple[int, int]]], sign: int) -> Fraction:
    (p1, q1), (p2, q2) = cells[0][1], cells[1][0]
    if p1 - sign * p2 == 0:
        raise ZeroDivisionError("unknown cancels")
    return F(sign * q2 - q1, p1 - sign * p2)


def _sym_hand(md: Mapping[str, Any]) -> Fraction:
    return _sym_solve(_cells(md), 1 if md["kind"] == "symmetric" else -1)


def _sym_sympy(md: Mapping[str, Any]) -> Fraction:
    x = sympy.Symbol("x")
    m = sympy.Matrix([[a * x + b for a, b in row] for row in _cells(md)])
    diff = (m - m.T) if md["kind"] == "symmetric" else (m + m.T)
    sol = sympy.solve([e for e in diff if e != 0], x, dict=True)
    if len(sol) != 1:
        raise ValueError("no unique solution")
    return kit.unsp(sol[0][x])


def _sym_scan(md: Mapping[str, Any]) -> Fraction:
    cells = _cells(md)
    found = []
    for twice in range(-40, 41):
        x = F(twice, 2)
        m = [[a * x + b for a, b in row] for row in cells]
        mt = kit.transpose(m)
        s = 1 if md["kind"] == "symmetric" else -1
        if all(m[i][j] == s * mt[i][j] for i in range(3) for j in range(3)):
            found.append(x)
    if len(found) != 1:
        raise ValueError("not exactly one solution on the scan")
    return found[0]


@model(
    "MAT.SYMMETRIC_UNKNOWN", chapter=MAT, title="Find the unknown that makes a matrix symmetric or skew-symmetric",
    prereq=["MATH.C12.PRE.LINEAR_EQUATIONS"], marks=3, technique="compare_entries",
    box={"x0": {"choices": [-3, -2, -1, 1, 2, 3]}, "p1": {"choices": [1, 2, 3]}, "p2": {"choices": [0, 1, -1]},
         "q1": {"choices": [-2, 3]}, "kind": {"choices": ["symmetric", "skew"]}},
)  # fmt: skip
def sym_unknown(p: Mapping[str, Any]) -> Built:
    x0, p1, p2, q1, kind = int(p["x0"]), int(p["p1"]), int(p["p2"]), int(p["q1"]), str(p["kind"])
    sign = 1 if kind == "symmetric" else -1
    if p1 - sign * p2 == 0:
        raise IllPosed("unknown_cancels")
    q2 = sign * (p1 * x0 + q1) - p2 * x0
    c13, c23 = (2, -1) if kind == "symmetric" else (4, 3)
    diag = (1, 5, -2) if kind == "symmetric" else (0, 0, 0)
    cells = [
        [(0, diag[0]), (p1, q1), (0, c13)],
        [(p2, q2), (0, diag[1]), (0, c23)],
        [(0, sign * c13), (0, sign * c23), (0, diag[2])],
    ]
    md = {"cells": [[[a, b] for a, b in row] for row in cells], "kind": kind}
    key = _sym_hand(md)
    if key != x0:
        raise IllPosed("construction_mismatch")
    rows = [[poly_text([b, a]) if a else str(b) for a, b in row] for row in cells]
    mtxt = "[" + ", ".join("[" + ", ".join(r) + "]" for r in rows) + "]"
    try:
        other = _sym_solve(_cells(md), -sign)
    except ZeroDivisionError:
        other = key + 2
    wrong = [
        ("MC.C12.MAT.SIGN_SLIP_WHEN_SOLVING", -key),
        ("MC.C12.MAT.UNKNOWN_COEFFICIENT_NOT_DIVIDED", F(sign * q2 - q1)),
        ("MC.C12.MAT.SYMMETRIC_SKEW_CONFUSED", other),
        ("MC.C12.MAT.ONLY_CONSTANT_TERMS_EQUATED", F(q2 - q1)),
        ("MC.C12.MAT.OFF_BY_ONE_SLIP", key + 1),
        ("MC.C12.MAT.HALVED_BY_MISTAKE", key * 2),
    ]
    cond = "symmetric" if kind == "symmetric" else "skew-symmetric"
    why = (
        "A symmetric matrix equals its transpose, so entries in mirror positions are equal."
        if kind == "symmetric"
        else "A skew-symmetric matrix equals minus its transpose, so entries in mirror positions are negatives of each other."
    )
    return case(
        fam="MAT.SYMMETRIC_UNKNOWN", md=md, names=["x"], value=key,
        stem=f"The matrix {mtxt} is {cond}. Find the value of x.",
        steps=[why, "Write the equation for the pair of mirror entries that contain x, and solve it with inverse operations.", f"x = {fr(key)}."],
        hints=hints3(p, ["Which pairs of entries must match for this kind of matrix?", "Only the entries that contain the unknown matter.", "Compare each entry with the entry in the mirror position."],
                     "Write the condition for the pair of entries holding x as one statement about x, then solve it with inverse operations.",
                     "Full method: state the condition for this type of matrix, apply it to the mirror pair holding x, solve for x, and check the other mirror pairs."),
        wrong=wrong, base=0.35, role="apply", prediction="Which entries are forced to be equal or opposite?",
        slug=slug(kind, x0, p1, p2, q1), nsteps=3, mags=[x0],
        methods=[("c12.mat.sym.compare", "closed_form", "compare_entries", _sym_hand),
                 ("c12.mat.sym.sympy", "sympy.solve", "", _sym_sympy),
                 ("c12.mat.sym.scan", "enumeration", "", _sym_scan)],
    )  # fmt: skip


# ================================================================ DET.VALUE


def _dv_cof(md: Mapping[str, Any]) -> Fraction:
    return kit.det_cofactor(_M(md, "A"))


def _dv_leibniz(md: Mapping[str, Any]) -> Fraction:
    return kit.det_leibniz(_M(md, "A"))


def _dv_sympy(md: Mapping[str, Any]) -> Fraction:
    return kit.unsp(kit.smat(_M(md, "A")).det())


@model(
    "DET.VALUE", chapter=DET, title="Evaluate the determinant of a 2 by 2 or 3 by 3 matrix", prereq=[PRE_ARITH],
    marks=2, technique="cofactor_expansion", version="2",
    box={"n": {"choices": [2, 3]}, "seed": {"min": 0, "max": 39}},
)  # fmt: skip
def det_value(p: Mapping[str, Any]) -> Built:
    n, seed = int(p["n"]), int(p["seed"])
    a = _seeded(seed, n, n, -4, 4, salt=n)
    md = {"A": _txt(a)}
    key = _dv_cof(md)
    if key == 0:
        raise IllPosed("zero_determinant")
    if n == 2:
        (x, y), (z, w) = a
        wrong = [
            ("MC.C12.DET.ADD_INSTEAD_OF_SUBTRACT", x * w + y * z),
            ("MC.C12.DET.SIGN_REVERSED", y * z - x * w),
            ("MC.C12.DET.WRONG_PAIRS_MULTIPLIED", x * z - y * w),
            ("MC.C12.DET.DIAGONAL_PRODUCT_ONLY", x * w),
        ]
    else:
        nosign = sum((a[0][j] * kit.det_cofactor(kit.minor(a, 0, j)) for j in range(3)), F(0))
        wrong = [
            ("MC.C12.DET.COFACTOR_SIGNS_IGNORED", nosign),
            ("MC.C12.DET.SIGN_REVERSED", -key),
            ("MC.C12.DET.DIAGONAL_PRODUCT_ONLY", a[0][0] * a[1][1] * a[2][2]),
            ("MC.C12.DET.FIRST_TERM_ONLY", a[0][0] * kit.det_cofactor(kit.minor(a, 0, 0))),
        ]
    return case(
        fam="DET.VALUE", md=md, names=["det"], value=key, stem=pick([f"Find the determinant of the matrix {mat_text(a)}.", f"What is the value of the determinant of A = {mat_text(a)}?", f"Evaluate det A for A = {mat_text(a)}."], p),
        steps=["Expand along the first row, using alternating signs plus, minus, plus." if n == 3 else "For a 2 by 2 matrix, multiply the main diagonal and subtract the product of the other diagonal.", f"The determinant is {fr(key)}."],
        hints=hints3(p, ["Which expansion rule fits this size of matrix?", "Watch the signs of the terms.", "Pick one row to expand along and write each term before adding."],
                     "Use the diagonal rule for two rows, or expand along the first row with alternating signs for three rows.",
                     "Full method: for each entry of the first row, multiply by its minor with the correct sign, then add the terms; recheck each sign."),
        wrong=wrong, base=0.25 if n == 2 else 0.4, role="apply", prediction="Will the determinant be positive or negative?",
        slug=slug(n, seed), nsteps=2 + n, mags=[abs(int(key))],
        methods=[("c12.det.cofactor", "closed_form", "cofactor_expansion", _dv_cof),
                 ("c12.det.leibniz", "permutation_sum", "", _dv_leibniz),
                 ("c12.det.sympy", "sympy.matrix", "", _dv_sympy)],
    )  # fmt: skip


# ================================================================ DET.ADJOINT_ENTRY


def _adj_hand(md: Mapping[str, Any]) -> Fraction:
    return kit.cofactor(_M(md, "A"), md["j"], md["i"])  # adj[i][j] = C_ji


def _adj_sympy(md: Mapping[str, Any]) -> Fraction:
    return kit.unsp(kit.smat(_M(md, "A")).adjugate()[md["i"], md["j"]])


def _adj_inverse(md: Mapping[str, Any]) -> Fraction:
    a = _M(md, "A")
    return kit.gauss_inverse(a)[md["i"]][md["j"]] * kit.det_leibniz(a)


@model(
    "DET.ADJOINT_ENTRY", chapter=DET, title="Find one entry of the adjoint of a 3 by 3 matrix", prereq=[PRE_ARITH],
    marks=3, technique="cofactor_transpose", version="2",
    box={"seed": {"min": 0, "max": 19}, "i": {"min": 0, "max": 2}, "j": {"min": 0, "max": 2}},
)  # fmt: skip
def adjoint_entry(p: Mapping[str, Any]) -> Built:
    seed, i, j = int(p["seed"]), int(p["i"]), int(p["j"])
    a = _seeded(seed, 3, 3, -3, 3, salt=77)
    if kit.det_cofactor(a) == 0:
        raise IllPosed("singular_matrix")
    md = {"A": _txt(a), "i": i, "j": j}
    key = _adj_hand(md)
    minor_nosign = kit.det_cofactor(kit.minor(a, j, i))
    wrong = [
        ("MC.C12.DET.ADJOINT_NOT_TRANSPOSED", kit.cofactor(a, i, j)),
        ("MC.C12.DET.COFACTOR_SIGN_FORGOTTEN", minor_nosign),
        ("MC.C12.DET.ADJOINT_DIVIDED_BY_DETERMINANT", key / kit.det_cofactor(a)),
        ("MC.C12.DET.MINOR_OF_WRONG_POSITION", kit.det_cofactor(kit.minor(a, i, j))),
        ("MC.C12.DET.SIGN_REVERSED", -key),
        ("MC.C12.DET.DETERMINANT_USED_FOR_ENTRY", kit.det_cofactor(a)),
    ]
    return case(
        fam="DET.ADJOINT_ENTRY", md=md, names=["entry"], value=key,
        stem=pick([f"Let A = {mat_text(a)}. Find the entry in row {i + 1} and column {j + 1} of the adjoint of A.", f"For the matrix A = {mat_text(a)}, what is the element in row {i + 1}, column {j + 1} of adj A?", f"The adjoint of A = {mat_text(a)} is needed. Give its entry in row {i + 1} and column {j + 1}."], p),
        steps=["The adjoint is the transpose of the matrix of cofactors, so its entry in row i and column j is the cofactor of the entry in row j and column i of A.", f"Delete row {j + 1} and column {i + 1}, take the 2 by 2 determinant, and attach the sign {'+' if (i + j) % 2 == 0 else '-'}.", f"The entry is {fr(key)}."],
        hints=hints3(p, ["Which entry of the matrix does this position of the adjoint come from?", "Remember that the adjoint is built from cofactors and then turned over.", "Decide the minor to delete before computing anything."],
                     "Find the cofactor of the entry in the mirrored position, since the adjoint is the transpose of the cofactor matrix.",
                     "Full method: locate the mirrored position, delete its row and column, find the 2 by 2 determinant, and multiply by the sign of that position."),
        wrong=wrong, base=0.45, role="apply", prediction="Does the position of the entry matter once the matrix is turned over?",
        slug=slug(seed, i, j), nsteps=4,
        methods=[("c12.adj.cofactor", "closed_form", "cofactor_transpose", _adj_hand),
                 ("c12.adj.sympy", "sympy.matrix", "", _adj_sympy),
                 ("c12.adj.inverse", "gauss_jordan", "", _adj_inverse)],
    )  # fmt: skip


# ================================================================ DET.INVERSE_2X2


def _inv_formula(md: Mapping[str, Any]) -> tuple[Fraction, ...]:
    (a, b), (c, d) = _M(md, "A")
    det = a * d - b * c
    return (d / det, -b / det, -c / det, a / det)


def _inv_sympy(md: Mapping[str, Any]) -> tuple[Fraction, ...]:
    inv = kit.smat(_M(md, "A")).inv()
    return tuple(kit.unsp(inv[i, j]) for i in range(2) for j in range(2))


def _inv_gauss(md: Mapping[str, Any]) -> tuple[Fraction, ...]:
    return _flat(kit.gauss_inverse(_M(md, "A")))


@model(
    "DET.INVERSE_2X2", chapter=DET, title="Find the inverse of a 2 by 2 matrix", prereq=[PRE_ARITH], marks=2,
    technique="adjoint_over_determinant", version="2", box={"seed": {"min": 0, "max": 399}},
)  # fmt: skip
def inverse_2x2(p: Mapping[str, Any]) -> Built:
    seed = int(p["seed"])
    a = _seeded(seed, 2, 2, -4, 4, salt=5)
    det = a[0][0] * a[1][1] - a[0][1] * a[1][0]
    if det == 0 or abs(det) > 3 or any(x == 0 for r in a for x in r):
        raise IllPosed("not_a_nice_invertible_matrix")
    md = {"A": _txt(a)}
    key = _inv_formula(md)
    (x, y), (z, w) = a
    wrong = [
        ("MC.C12.DET.INVERSE_WITHOUT_DIVIDING", (w, -y, -z, x)),
        ("MC.C12.DET.OFF_DIAGONAL_SIGNS_KEPT", (w / det, y / det, z / det, x / det)),
        ("MC.C12.DET.INVERSE_AS_ENTRYWISE_RECIPROCAL", (1 / x, 1 / y, 1 / z, 1 / w)),
        ("MC.C12.DET.ADJOINT_NOT_ARRANGED", (x / det, -y / det, -z / det, w / det)),
    ]
    return case(
        fam="DET.INVERSE_2X2", md=md, names=["m11", "m12", "m21", "m22"], value=tuple(key), fmt=_m2,
        stem=pick([f"Find the inverse of the matrix {mat_text(a)}.", f"What is the inverse of A = {mat_text(a)}?", f"Given A = {mat_text(a)}, write down A⁻¹."], p),
        steps=["The inverse is the adjoint divided by the determinant.", f"The determinant is {fr(det)}. For a 2 by 2 matrix, swap the diagonal entries and change the sign of the other two to get the adjoint.", f"Divide every entry by {fr(det)}: {_m2(tuple(key))}."],
        hints=hints3(p, ["What must be true about the determinant before an inverse exists?", "Two things happen to the entries of the adjoint: positions and signs.", "Find the determinant first."],
                     "Compute the determinant, build the adjoint by exchanging the main diagonal entries and negating the other two, then divide by the determinant.",
                     "Full method: determinant, adjoint, divide every entry; finally multiply your answer by the original matrix to see the identity."),
        wrong=wrong, base=0.35, role="apply", prediction="What should the product of the matrix and its inverse be?",
        slug=slug(seed), nsteps=4, mags=[abs(int(det))],
        methods=[("c12.inv.adjoint", "closed_form", "adjoint_over_determinant", _inv_formula),
                 ("c12.inv.sympy", "sympy.matrix", "", _inv_sympy),
                 ("c12.inv.gauss", "gauss_jordan", "", _inv_gauss)],
    )  # fmt: skip


# ================================================================ DET.SOLVE_SYSTEM


def _sys(md: Mapping[str, Any]) -> tuple[kit.Mat, list[Fraction]]:
    return _M(md, "A"), [F(x) for x in md["b"]]


def _ss_cramer(md: Mapping[str, Any]) -> tuple[Fraction, ...]:
    a, b = _sys(md)
    d = kit.det_cofactor(a)
    out = []
    for j in range(len(a)):
        aj = [row[:j] + [b[i]] + row[j + 1 :] for i, row in enumerate(a)]
        out.append(kit.det_cofactor(aj) / d)
    return tuple(out)


def _ss_sympy(md: Mapping[str, Any]) -> tuple[Fraction, ...]:
    a, b = _sys(md)
    sol = kit.smat(a).LUsolve(sympy.Matrix([kit.sp(x) for x in b]))
    return tuple(kit.unsp(v) for v in sol)


def _ss_gauss(md: Mapping[str, Any]) -> tuple[Fraction, ...]:
    a, b = _sys(md)
    inv = kit.gauss_inverse(a)
    return tuple(sum((inv[i][k] * b[k] for k in range(len(b))), F(0)) for i in range(len(a)))


def lin_text(coeffs: list[Fraction], names: str) -> str:
    out = ""
    for c, v in zip(coeffs, names, strict=False):
        if c == 0:
            continue
        mag = abs(c)
        body = ("" if mag == 1 else fr(mag)) + v
        out = (
            (("-" if c < 0 else "") + body) if not out else out + (" - " if c < 0 else " + ") + body
        )
    return out or "0"


@model(
    "DET.SOLVE_SYSTEM", chapter=DET, title="Solve a system of linear equations using determinants or the inverse",
    prereq=["MATH.C12.PRE.LINEAR_EQUATIONS"], marks=3, technique="matrix_method",
    box={"n": {"choices": [2, 3]}, "seed": {"min": 0, "max": 29}},
)  # fmt: skip
def solve_system(p: Mapping[str, Any]) -> Built:
    n, seed = int(p["n"]), int(p["seed"])
    a = _seeded(seed, n, n, -3, 3, salt=9)
    sol = [F(v) for v in kit.lcg(seed + 500, n, -3, 3)]
    det = kit.det_cofactor(a)
    if det == 0 or abs(det) > 12 or len(set(sol)) < n:
        raise IllPosed("unsuitable_system")
    b = [sum((a[i][k] * sol[k] for k in range(n)), F(0)) for i in range(n)]
    md = {"A": _txt(a), "b": [fr(v) for v in b]}
    key = _ss_cramer(md)
    if key != tuple(sol):
        raise IllPosed("construction_mismatch")
    names = "xyz"[:n]
    eqs = [f"{lin_text(a[i], names)} = {fr(b[i])}" for i in range(n)]
    d_vals = []
    for j in range(n):
        aj = [row[:j] + [b[i]] + row[j + 1 :] for i, row in enumerate(a)]
        d_vals.append(kit.det_cofactor(aj))
    wrong = [
        ("MC.C12.DET.CRAMER_NOT_DIVIDED", tuple(d_vals)),
        ("MC.C12.DET.UNKNOWN_ORDER_SWAPPED", tuple(reversed(sol))),
        ("MC.C12.DET.SIGN_ERROR_IN_SOLUTION", tuple(-s for s in sol)),
        ("MC.C12.DET.TRANSPOSED_SYSTEM_SOLVED", tuple(kit.gauss_solve(kit.transpose(a), b))),
    ]
    kernel = {"equations": [{"coeffs": [fr(c) for c in a[i]], "const": fr(b[i])} for i in range(n)]}
    return case(
        fam="DET.SOLVE_SYSTEM", md=md, names=list(names), value=tuple(sol), kernel=kernel,
        fmt=lambda v: ", ".join(f"{nm} = {fr(x)}" for nm, x in zip(names, v, strict=True)),
        stem="Solve the system " + "; ".join(eqs) + ".",
        steps=["Write the system as the matrix equation A X = B.", f"The determinant of A is {fr(det)}, which is not zero, so there is exactly one solution.", "Find each unknown as the determinant with that column replaced by B, divided by the determinant of A."],
        hints=hints3(p, ["Write the system in matrix form first.", "Check that the determinant is not zero before you go on.", "Each unknown needs its own determinant."],
                     "Either replace one column at the time by the right-hand side and divide determinants, or multiply the inverse of the coefficient matrix by the right-hand side.",
                     "Full method: write A X = B, compute the determinant of A, find each unknown by column replacement or with the inverse, and put your answer back into every equation."),
        wrong=wrong, base=0.4 if n == 2 else 0.55, role="apply", prediction="Does the system have one solution, none, or infinitely many?",
        slug=slug(n, seed), nsteps=2 + n,
        methods=[("c12.sys.cramer", "closed_form", "matrix_method", _ss_cramer),
                 ("c12.sys.sympy", "sympy.matrix", "", _ss_sympy),
                 ("c12.sys.inverse", "gauss_jordan", "", _ss_gauss)],
    )  # fmt: skip
