# ruff: noqa: E501
"""Vectors, three dimensional geometry, linear programming, probability."""

from __future__ import annotations

import itertools
import math
from collections.abc import Mapping
from fractions import Fraction
from typing import Any

import sympy
from sympy.solvers.simplex import lpmax

from app.factory.lanes.maths_c12 import kit
from app.factory.lanes.maths_c12.core import (
    Built,
    F,
    IllPosed,
    case,
    fr,
    hints3,
    isqrt_exact,
    model,
    pick,
    vec_text,
)  # fmt: skip
from app.factory.lanes.maths_c12.m_matrices import lin_text
from app.factory.lanes.maths_c12.m_rf_itf import slug

CH = "cbse.12.maths."
VEC, GEO, LP, PROB = (
    CH + "vectors",
    CH + "three_d_geometry",
    CH + "linear_programming",
    CH + "probability",
)
PRE_VEC = "MATH.C12.PRE.COORDINATES_3D"
PRE_FRAC = "MATH.C12.PRE.FRACTIONS_PROBABILITY"

BASES = [(1, 2, 2), (2, 3, 6), (2, 6, 9), (1, 4, 8), (4, 4, 7), (0, 3, 4), (0, 5, 12), (2, 10, 11)]


def _vec(seed: int, salt: int) -> tuple[int, int, int]:
    r = kit.lcg(seed * 13 + salt, 5, 0, 99)
    base = BASES[r[0] % len(BASES)]
    perm = list(itertools.permutations(range(3)))[r[1] % 6]
    sg = [1 if r[2 + i] % 2 else -1 for i in range(3)]
    return (sg[0] * base[perm[0]], sg[1] * base[perm[1]], sg[2] * base[perm[2]])


def _dot(a: Any, b: Any) -> int:
    return int(sum(x * y for x, y in zip(a, b, strict=True)))


def _norm(a: Any) -> int:
    return math.isqrt(_dot(a, a))


# ================================================================ VEC.ANGLE_COS


def _va_hand(md: Mapping[str, Any]) -> Fraction:
    a, b = md["a"], md["b"]
    na, nb = isqrt_exact(F(_dot(a, a))), isqrt_exact(F(_dot(b, b)))
    if na is None or nb is None:
        raise ValueError("irrational norm")
    return F(_dot(a, b)) / (na * nb) if md["ask"] == "cos" else F(_dot(a, b)) / nb


def _va_sympy(md: Mapping[str, Any]) -> Fraction:
    a, b = sympy.Matrix(md["a"]), sympy.Matrix(md["b"])
    val = a.dot(b) / (a.norm() * b.norm()) if md["ask"] == "cos" else a.dot(b) / b.norm()
    return kit.unsp(sympy.simplify(val))


def _va_other(md: Mapping[str, Any]) -> Fraction:
    a, b = [F(x) for x in md["a"]], [F(x) for x in md["b"]]
    nb = isqrt_exact(sum((x * x for x in b), F(0)))
    na = isqrt_exact(sum((x * x for x in a), F(0)))
    assert nb is not None and na is not None
    if md["ask"] == "proj":  # scalar projection through the unit vector in the direction of b
        return sum((x * y / nb for x, y in zip(a, b, strict=True)), F(0))
    diff2 = sum((x - y) ** 2 for x, y in zip(a, b, strict=True))  # law of cosines
    return (na * na + nb * nb - diff2) / (2 * na * nb)


@model(
    "VEC.ANGLE_COS", chapter=VEC, title="Find the cosine of the angle between two vectors, or a scalar projection",
    prereq=[PRE_VEC], marks=2, technique="dot_product_formula",
    box={"seed": {"min": 0, "max": 39}, "ask": {"choices": ["cos", "proj"]}},
)  # fmt: skip
def vec_angle(p: Mapping[str, Any]) -> Built:
    seed, ask = int(p["seed"]), str(p["ask"])
    a, b = _vec(seed, 1), _vec(seed, 2)
    if a == b or tuple(-x for x in a) == b or _dot(a, b) == 0:
        raise IllPosed("parallel_or_perpendicular_pair")
    md = {"a": list(a), "b": list(b), "ask": ask}
    key = _va_hand(md)
    d, na, nb = _dot(a, b), _norm(a), _norm(b)
    if ask == "cos":
        wrong = [
            ("MC.C12.VEC.COSINE_WITHOUT_DIVIDING", F(d)),
            ("MC.C12.VEC.ONE_NORM_ONLY", F(d, na)),
            ("MC.C12.VEC.NORMS_ADDED", F(d, na + nb)),
            ("MC.C12.VEC.NORMS_NOT_SQUARE_ROOTED", F(d, na * na * nb * nb)),
        ]
        stem = f"Find the cosine of the angle between the vectors {vec_text(a)} and {vec_text(b)}."
    else:
        wrong = [
            ("MC.C12.VEC.PROJECTION_WITHOUT_DIVIDING", F(d)),
            ("MC.C12.VEC.PROJECTED_ON_WRONG_VECTOR", F(d, na)),
            ("MC.C12.VEC.NORM_NOT_SQUARE_ROOTED", F(d, nb * nb)),
            ("MC.C12.VEC.PROJECTION_AS_COSINE", F(d, na * nb)),
        ]
        stem = (
            f"Find the scalar projection of the vector {vec_text(a)} on the vector {vec_text(b)}."
        )
    return case(
        fam="VEC.ANGLE_COS", md=md, names=["value"], value=key, stem=stem,
        steps=[f"The dot product is {d}.", f"The lengths are {na} and {nb}.", f"{'cos θ = dot product divided by the product of the lengths' if ask == 'cos' else 'The scalar projection is the dot product divided by the length of the vector projected on'}: {fr(key)}."],
        hints=hints3(p, ["Which product of two vectors gives one number?", "You need the lengths of the vectors as well as the dot product.", "List the three numbers you need before you divide."],
                     "Compute the dot product and the length of each vector, then divide as the formula says.",
                     "Full method: dot product from matching components, each length from the square root of the sum of squares, then the quotient asked for; check that the cosine lies between minus one and one."),
        wrong=wrong, base=0.4, role="apply", prediction="Is the angle acute or obtuse?", slug=slug(seed, ask), nsteps=4,
        methods=[("c12.vec.angle.formula", "closed_form", "dot_product_formula", _va_hand),
                 ("c12.vec.angle.sympy", "sympy.matrix", "", _va_sympy),
                 ("c12.vec.angle.other", "law_of_cosines_or_unit_vector", "", _va_other)],
    )  # fmt: skip


# ================================================================ VEC.CROSS_TRIPLE


def _cross(a: Any, b: Any) -> tuple[Fraction, Fraction, Fraction]:
    return (
        F(a[1] * b[2] - a[2] * b[1]),
        F(a[2] * b[0] - a[0] * b[2]),
        F(a[0] * b[1] - a[1] * b[0]),
    )


def _ct_hand(md: Mapping[str, Any]) -> Any:
    a, b, c = md["a"], md["b"], md["c"]
    x = _cross(a, b)
    return x if md["ask"] == "cross" else sum(F(c[i]) * x[i] for i in range(3))


def _ct_sympy(md: Mapping[str, Any]) -> Any:
    a, b, c = (sympy.Matrix(md[k]) for k in "abc")
    if md["ask"] == "cross":
        v = a.cross(b)
        return tuple(kit.unsp(v[i]) for i in range(3))
    return kit.unsp(sympy.Matrix.hstack(a, b, c).det())


def _ct_levi(md: Mapping[str, Any]) -> Any:
    a, b, c = md["a"], md["b"], md["c"]
    eps = {perm: kit._parity(perm) for perm in itertools.permutations(range(3))}
    if md["ask"] == "cross":
        return tuple(
            F(
                sum(
                    eps[(i, j, k)] * a[j] * b[k]
                    for j in range(3)
                    for k in range(3)
                    if (i, j, k) in eps
                )
            )
            for i in range(3)
        )
    return kit.det_leibniz(kit.mat([a, b, c]))


@model(
    "VEC.CROSS_TRIPLE", chapter=VEC, title="Find a cross product or a scalar triple product", prereq=[PRE_VEC],
    marks=2, technique="determinant_form", box={"seed": {"min": 0, "max": 39}, "ask": {"choices": ["cross", "triple"]}},
)  # fmt: skip
def vec_cross_triple(p: Mapping[str, Any]) -> Built:
    seed, ask = int(p["seed"]), str(p["ask"])
    a, b, c = (tuple(kit.lcg(seed * 3 + s, 3, -3, 3)) for s in (1, 2, 3))
    cr = _cross(a, b)
    if all(x == 0 for x in cr) or (ask == "triple" and sum(F(c[i]) * cr[i] for i in range(3)) == 0):
        raise IllPosed("degenerate_vectors")
    md = {"a": list(a), "b": list(b), "c": list(c), "ask": ask}
    key = _ct_hand(md)
    if ask == "cross":
        wrong: list[tuple[str, Any]] = [
            ("MC.C12.VEC.CROSS_ORDER_REVERSED", tuple(-x for x in cr)),
            ("MC.C12.VEC.MIDDLE_SIGN_FORGOTTEN", (cr[0], -cr[1], cr[2])),
            ("MC.C12.VEC.COMPONENTWISE_PRODUCT", tuple(F(a[i] * b[i]) for i in range(3))),
            ("MC.C12.VEC.COMPONENTS_ADDED", tuple(F(a[i] + b[i]) for i in range(3))),
        ]
        return case(
            fam="VEC.CROSS_TRIPLE", md=md, names=["i", "j", "k"], value=key, fmt=lambda v: vec_text(v),
            stem=f"Find the cross product of the vectors {vec_text(a)} and {vec_text(b)}, in that order.",
            steps=["Write the 3 by 3 determinant with the unit vectors on the first row, the first vector on the second row and the second vector on the third row.", "Expand along the first row; the middle term carries a minus sign.", f"The cross product is {vec_text(key)}."],
            hints=hints3(p, ["The answer of this product is one vector, not one number.", "The order of the two vectors matters.", "Set up the determinant with the unit vectors on top."],
                         "Expand the determinant along the unit-vector row, taking care with the sign of the middle term.",
                         "Full method: determinant with i, j, k on the first row, expand, simplify each component, and check that your result is perpendicular to both vectors by taking dot products."),
            wrong=wrong, base=0.4, role="apply", prediction="Is the result perpendicular to both vectors?", slug=slug(seed, ask), nsteps=4,
            methods=[("c12.vec.cross.det", "closed_form", "determinant_form", _ct_hand), ("c12.vec.cross.sympy", "sympy.matrix", "", _ct_sympy), ("c12.vec.cross.levi", "permutation_symbol", "", _ct_levi)],
        )  # fmt: skip
    t = key
    wrong = [
        ("MC.C12.VEC.TRIPLE_SIGN_REVERSED", -t),
        ("MC.C12.VEC.DOT_PRODUCTS_ADDED", F(_dot(a, b) + _dot(b, c))),
        ("MC.C12.VEC.MIDDLE_SIGN_FORGOTTEN", F(c[0] * cr[0] - c[1] * cr[1] + c[2] * cr[2])),
        ("MC.C12.VEC.CROSS_THEN_NO_DOT", F(sum(abs(x) for x in cr))),
    ]
    return case(
        fam="VEC.CROSS_TRIPLE", md=md, names=["value"], value=key,
        stem=f"Find the scalar triple product of the vectors {vec_text(a)}, {vec_text(b)} and {vec_text(c)}, in that order.",
        steps=["The scalar triple product is the determinant whose rows are the three vectors.", f"Expand it: the value is {fr(t)}."],
        hints=hints3(p, ["The answer is one number: the volume with its sign.", "Rows of the determinant follow the order the vectors are given.", "Decide the layout of the determinant first."],
                     "Write the three vectors as the rows of one three by three determinant and expand it with alternating signs.",
                     "Full method: rows in the given order, expand along the first row with signs plus, minus, plus, and keep the sign of your final number."),
        wrong=wrong, base=0.4, role="apply", prediction="Would swapping two vectors change the sign?", slug=slug(seed, ask), nsteps=4,
        methods=[("c12.vec.triple.det", "closed_form", "determinant_form", _ct_hand), ("c12.vec.triple.sympy", "sympy.matrix", "", _ct_sympy), ("c12.vec.triple.leibniz", "permutation_sum", "", _ct_levi)],
    )  # fmt: skip


# ================================================================ GEO3D.POINT_PLANE


def _pp_formula(md: Mapping[str, Any]) -> Fraction:
    n, pt, d = md["n"], md["pt"], md["d"]
    norm = isqrt_exact(F(_dot(n, n)))
    assert norm is not None
    return abs(F(_dot(n, pt) - d)) / norm


def _pp_foot(md: Mapping[str, Any]) -> Fraction:
    n, pt, d = [F(x) for x in md["n"]], [F(x) for x in md["pt"]], F(md["d"])
    s = (sum(x * y for x, y in zip(n, pt, strict=True)) - d) / sum(x * x for x in n)
    foot = [pt[i] - s * n[i] for i in range(3)]
    if sum(n[i] * foot[i] for i in range(3)) != d:
        raise ValueError("foot not on the plane")
    dist2 = sum(((pt[i] - foot[i]) ** 2 for i in range(3)), F(0))
    r = isqrt_exact(dist2)
    if r is None:
        raise ValueError("irrational distance")
    return r


def _pp_sympy(md: Mapping[str, Any]) -> Fraction:
    n = md["n"]
    n_sq = sum(x * x for x in n)
    base = sympy.Point3D(*[sympy.Rational(md["d"] * x, n_sq) for x in n])  # a point on the plane
    plane = sympy.Plane(base, normal_vector=tuple(n))
    return kit.unsp(sympy.simplify(plane.distance(sympy.Point3D(*md["pt"]))))


@model(
    "GEO3D.POINT_PLANE", chapter=GEO, title="Find the distance of a point from a plane", prereq=[PRE_VEC], marks=2,
    technique="distance_formula",
    box={"seed": {"min": 0, "max": 23}, "t": {"choices": [1, 2, 3, -1, -2]}, "f": {"choices": [0, 1]}},
)  # fmt: skip
def point_plane(p: Mapping[str, Any]) -> Built:
    seed, t, f = int(p["seed"]), int(p["t"]), int(p["f"])
    n = _vec(seed, 5)
    foot = tuple(kit.lcg(seed + 40 * f, 3, -3, 3))
    pt = tuple(foot[i] + t * n[i] for i in range(3))
    d = _dot(n, foot)
    if d == 0 or any(abs(x) > 40 for x in pt):
        raise IllPosed("unsuitable_plane")
    md = {"n": list(n), "pt": list(pt), "d": d}
    key = _pp_formula(md)
    N, top = _norm(n), abs(_dot(n, pt) - d)
    wrong = [
        ("MC.C12.GEO.NORM_NOT_DIVIDED", F(top)),
        ("MC.C12.GEO.NORM_NOT_SQUARE_ROOTED", F(top, N * N)),
        ("MC.C12.GEO.COEFFICIENTS_ADDED_FOR_NORM", F(top, abs(sum(n)) or 1)),
        ("MC.C12.GEO.PLANE_CONSTANT_IGNORED", F(abs(_dot(n, pt)), N)),
    ]
    return case(
        fam="GEO3D.POINT_PLANE", md=md, names=["distance"], value=key,
        stem=f"Find the distance of the point ({pt[0]}, {pt[1]}, {pt[2]}) from the plane {lin_text([F(x) for x in n], 'xyz')} = {d}.",
        steps=["Put the point into the left side of the plane equation and subtract the right side.", f"The size of that number is {top}, and the length of the normal vector is {N}.", f"Distance = {top} / {N} = {fr(key)}."],
        hints=hints3(p, ["Which vector is perpendicular to the plane?", "Substitute the point into the plane equation and see how far it misses.", "You will need the length of the normal vector."],
                     "Take the absolute value of the plane expression at the point and divide by the length of the normal vector.",
                     "Full method: substitute the point, subtract the constant, take the absolute value, find the length of the normal from its coefficients, and divide."),
        wrong=wrong, base=0.4, role="apply", prediction="Can a distance be negative?", slug=slug(seed, t, f), nsteps=3,
        methods=[("c12.geo.pp.formula", "closed_form", "distance_formula", _pp_formula), ("c12.geo.pp.foot", "foot_of_perpendicular", "", _pp_foot), ("c12.geo.pp.sympy", "sympy.geometry", "", _pp_sympy)],
    )  # fmt: skip


# ================================================================ LP.OPTIMUM


def _lp_cons(md: Mapping[str, Any]) -> list[tuple[Fraction, Fraction, Fraction]]:
    return [(F(a), F(b), F(c)) for a, b, c in md["cons"]]


def _lp_vertices(md: Mapping[str, Any]) -> list[tuple[Fraction, Fraction]]:
    lines = [*_lp_cons(md), (F(1), F(0), F(0)), (F(0), F(1), F(0))]
    out = set()
    for (a1, b1, c1), (a2, b2, c2) in itertools.combinations(lines, 2):
        det = a1 * b2 - a2 * b1
        if det == 0:
            continue
        x, y = (c1 * b2 - c2 * b1) / det, (a1 * c2 - a2 * c1) / det
        if x >= 0 and y >= 0 and all(a * x + b * y <= c for a, b, c in _lp_cons(md)):
            out.add((x, y))
    return sorted(out)


def _lp_corner(md: Mapping[str, Any]) -> Fraction:
    pq = F(md["pq"][0]), F(md["pq"][1])
    return max(pq[0] * x + pq[1] * y for x, y in _lp_vertices(md))


def _lp_lattice(md: Mapping[str, Any]) -> Fraction:
    cons, (p_, q_) = _lp_cons(md), md["pq"]
    best = None
    for x in range(0, 31):
        for y in range(0, 31):
            if all(a * x + b * y <= c for a, b, c in cons):
                z = F(p_ * x + q_ * y)
                best = z if best is None or z > best else best
    assert best is not None
    return best


def _lp_sympy(md: Mapping[str, Any]) -> Fraction:
    x, y = sympy.symbols("x y")
    cons = [kit.sp(a) * x + kit.sp(b) * y <= kit.sp(c) for a, b, c in _lp_cons(md)] + [
        x >= 0,
        y >= 0,
    ]
    val, _ = lpmax(md["pq"][0] * x + md["pq"][1] * y, cons)
    return kit.unsp(val)


@model(
    "LP.OPTIMUM", chapter=LP, title="Maximise a linear objective over a feasible region (corner point method)",
    prereq=["MATH.C12.PRE.LINEAR_EQUATIONS"], marks=3, technique="corner_point_method",
    box={"seed": {"min": 0, "max": 599}},
)  # fmt: skip
def lp_optimum(p: Mapping[str, Any]) -> Built:
    seed = int(p["seed"])
    r = kit.lcg(seed, 8, 1, 4)
    u, v = r[0], r[1]
    a1, b1, a2, b2 = r[2], r[3], r[4], r[5]
    p_, q_ = r[6], r[7] + 1
    if a1 * b2 == a2 * b1:
        raise IllPosed("parallel_lines")
    cons = [(a1, b1, a1 * u + b1 * v), (a2, b2, a2 * u + b2 * v)]
    md = {"cons": [list(c) for c in cons], "pq": [p_, q_]}
    verts = _lp_vertices(md)
    if any(x.denominator != 1 or y.denominator != 1 for x, y in verts) or len(verts) < 4:
        raise IllPosed("corner_points_not_whole_numbers")
    key = _lp_corner(md)
    zs = sorted({p_ * x + q_ * y for x, y in verts}, reverse=True)
    inter = p_ * u + q_ * v
    wrong = [
        ("MC.C12.LP.INTERSECTION_POINT_ONLY", F(inter)),
        ("MC.C12.LP.WRONG_CORNER_CHOSEN", zs[1] if len(zs) > 1 else key + 1),
        ("MC.C12.LP.MINIMUM_REPORTED", zs[-1]),
        (
            "MC.C12.LP.VALUE_OF_X_PLUS_Y_AT_BEST_CORNER",
            sum(next(c for c in verts if p_ * c[0] + q_ * c[1] == key)),
        ),
    ]
    cons_txt = "; ".join(f"{lin_text([F(a), F(b)], 'xy')} ≤ {c}" for a, b, c in cons)
    return case(
        fam="LP.OPTIMUM", md=md, names=["z"], value=key,
        stem=f"Maximise Z = {lin_text([F(p_), F(q_)], 'xy')} subject to {cons_txt}; x ≥ 0 and y ≥ 0.",
        steps=["Draw or list the corner points of the feasible region: where the boundary lines meet each other and the axes, keeping only points that satisfy every inequality.", "Evaluate Z at each corner point.", f"The largest value is {fr(key)}."],
        hints=hints3(p, ["Where can the best value of any linear objective occur?", "Find every corner point of the feasible region.", "Check each candidate point against all the inequalities."],
                     "Solve pairs of boundary lines to find the corner points, keep the feasible ones, and evaluate the objective at each.",
                     "Full method: all pairwise intersections of boundary lines, discard the infeasible ones, compute Z at every remaining corner, and take the largest."),
        wrong=wrong, base=0.5, role="apply", prediction="Will the best point be a corner of the region?", slug=slug(seed), nsteps=5,
        methods=[("c12.lp.corner", "closed_form", "corner_point_method", _lp_corner), ("c12.lp.lattice", "enumeration", "", _lp_lattice), ("c12.lp.sympy", "sympy.lpmax", "", _lp_sympy)],
    )  # fmt: skip


# ================================================================ PROB.BAYES

PRIORS = [(50, 50), (60, 40), (30, 70), (50, 30, 20), (25, 35, 40), (20, 30, 50)]
ORD = ["first", "second", "third"]


def _bayes_hand(md: Mapping[str, Any]) -> Fraction:
    pr, rt, k = md["pri"], md["rate"], md["k"]
    return F(pr[k] * rt[k], sum(a * b for a, b in zip(pr, rt, strict=True)))


def _bayes_population(md: Mapping[str, Any]) -> Fraction:
    pr, rt, k = md["pri"], md["rate"], md["k"]
    counts = [
        (pr[i] * 100 // 1) * rt[i] for i in range(len(pr))
    ]  # items out of 10 000 per source and outcome
    return F(counts[k], sum(counts))


def _bayes_sympy(md: Mapping[str, Any]) -> Fraction:
    pr = [sympy.Rational(x, 100) for x in md["pri"]]
    rt = [sympy.Rational(x, 100) for x in md["rate"]]
    k = md["k"]
    return kit.unsp(sympy.simplify(pr[k] * rt[k] / sum(a * b for a, b in zip(pr, rt, strict=True))))


@model(
    "PROB.BAYES", chapter=PROB, title="Find a posterior probability by Bayes' theorem", prereq=[PRE_FRAC], marks=3,
    technique="bayes_theorem",
    box={"pri": {"min": 0, "max": 5}, "rseed": {"min": 0, "max": 5}, "k": {"min": 0, "max": 2}},
)  # fmt: skip
def prob_bayes(p: Mapping[str, Any]) -> Built:
    pri = PRIORS[int(p["pri"])]
    k = int(p["k"])
    if k >= len(pri):
        raise IllPosed("source_does_not_exist")
    rate = kit.lcg(int(p["rseed"]) * 5 + len(pri), len(pri), 1, 9)
    if len(set(rate)) < len(rate):
        raise IllPosed("rates_not_distinct")
    md = {"pri": list(pri), "rate": rate, "k": k}
    key = _bayes_hand(md)
    tot = sum(a * b for a, b in zip(pri, rate, strict=True))
    wrong = [
        ("MC.C12.PROB.LIKELIHOOD_USED_AS_POSTERIOR", F(rate[k], 100)),
        ("MC.C12.PROB.PRIOR_USED_AS_POSTERIOR", F(pri[k], 100)),
        ("MC.C12.PROB.JOINT_NOT_DIVIDED_BY_TOTAL", F(pri[k] * rate[k], 10000)),
        ("MC.C12.PROB.PRIORS_IGNORED", F(rate[k], sum(rate))),
    ]
    srcs = ", ".join(f"{ORD[i]} source {pri[i]}%" for i in range(len(pri)))
    fails = ", ".join(f"{rate[i]}%" for i in range(len(pri)))
    return case(
        fam="PROB.BAYES", md=md, names=["probability"], value=key,
        stem=f"A factory has {len(pri)} machines. They make {srcs} of the bolts. The chance that a bolt is faulty is {fails} for the machines in that order. A bolt is picked at random and found faulty. What is the probability that it came from the {ORD[k]} machine?",
        steps=["Find the probability of each machine and a faulty bolt together: prior times fault rate.", f"Add them to get the total chance of a faulty bolt: {tot} out of 10000.", f"Posterior = {pri[k] * rate[k]} / {tot} = {fr(key)}."],
        hints=hints3(p, ["Are you asked for the chance of one fault, or the chance of one machine given one fault?", "Several machines can give faulty bolts, so you need the total.", "Find each machine's share of the faulty bolts."],
                     "Multiply each machine's share by its fault rate, add them all for the total, then divide the share of the asked machine by that total.",
                     "Full method: joint probability for each machine, their sum as the total probability of a fault, then the asked joint divided by the total; simplify the fraction."),
        wrong=wrong, base=0.55, role="apply", prediction="Should the answer be larger or smaller than the machine's share?", slug=slug(int(p["pri"]), int(p["rseed"]), k), nsteps=4,
        methods=[("c12.bayes.formula", "closed_form", "bayes_theorem", _bayes_hand), ("c12.bayes.population", "counting_population", "", _bayes_population), ("c12.bayes.sympy", "sympy.rational", "", _bayes_sympy)],
    )  # fmt: skip


# ================================================================ PROB.BINOMIAL


def _bin_event(kind: str, k: int, n: int, i: int) -> bool:
    return {"exactly": i == k, "at_least_one": i >= 1, "at_most_one": i <= 1}[kind]


def _bin_formula(md: Mapping[str, Any]) -> Fraction:
    n, pr, k, kind = md["n"], F(md["p"]), md["k"], md["kind"]
    q = 1 - pr
    return sum(
        math.comb(n, i) * pr**i * q ** (n - i) for i in range(n + 1) if _bin_event(kind, k, n, i)
    )


def _bin_enum(md: Mapping[str, Any]) -> Fraction:
    n, pr, k, kind = md["n"], F(md["p"]), md["k"], md["kind"]
    total = F(0)
    for seq in itertools.product((0, 1), repeat=n):
        if _bin_event(kind, k, n, sum(seq)):
            w = F(1)
            for s in seq:
                w *= pr if s else 1 - pr
            total += w
    return total


def _bin_dp(md: Mapping[str, Any]) -> Fraction:
    n, pr, k, kind = md["n"], F(md["p"]), md["k"], md["kind"]
    dist = [F(1)]
    for _ in range(n):
        new = [F(0)] * (len(dist) + 1)
        for i, w in enumerate(dist):
            new[i] += w * (1 - pr)
            new[i + 1] += w * pr
        dist = new
    return sum((dist[i] for i in range(n + 1) if _bin_event(kind, k, n, i)), F(0))


@model(
    "PROB.BINOMIAL", chapter=PROB, title="Find a binomial probability for repeated independent trials", prereq=[PRE_FRAC],
    marks=3, technique="binomial_formula",
    box={"n": {"choices": [3, 4, 5, 6]}, "p": {"choices": ["1/2", "1/3", "1/4", "2/3"]},
         "kind": {"choices": ["exactly", "at_least_one", "at_most_one"]}, "k": {"choices": [1, 2, 3]}},
)  # fmt: skip
def prob_binomial(p: Mapping[str, Any]) -> Built:
    n, ps, kind, k = int(p["n"]), str(p["p"]), str(p["kind"]), int(p["k"])
    if kind != "exactly" and k != 1:
        raise IllPosed("unused_parameter")
    if kind == "exactly" and k >= n:
        raise IllPosed("count_out_of_range")
    pr = F(ps)
    q = 1 - pr
    md = {"n": n, "p": ps, "kind": kind, "k": k}
    key = _bin_formula(md)
    if kind == "exactly":
        ask = f"exactly {k} heads"
        wrong = [
            ("MC.C12.PROB.BINOMIAL_COEFFICIENT_FORGOTTEN", pr**k * q ** (n - k)),
            ("MC.C12.PROB.FAILURE_FACTOR_FORGOTTEN", math.comb(n, k) * pr**k),
            ("MC.C12.PROB.SUCCESS_FAILURE_SWAPPED", math.comb(n, k) * q**k * pr ** (n - k)),
            ("MC.C12.PROB.SUCCESS_ONLY_POWER", pr**k),
        ]
    elif kind == "at_least_one":
        ask = "at least one head"
        wrong = [
            ("MC.C12.PROB.AT_LEAST_ONE_AS_ALL", pr**n),
            ("MC.C12.PROB.COMPLEMENT_WITH_WRONG_PROBABILITY", 1 - pr**n),
            ("MC.C12.PROB.EXACTLY_ONE_ONLY", n * pr * q ** (n - 1)),
            ("MC.C12.PROB.FAILURE_PROBABILITY_REPORTED", q**n),
        ]
    else:
        ask = "at most one head"
        wrong = [
            ("MC.C12.PROB.EXACTLY_ONE_ONLY", n * pr * q ** (n - 1)),
            ("MC.C12.PROB.ZERO_CASE_ONLY", q**n),
            ("MC.C12.PROB.AT_MOST_AS_AT_LEAST", 1 - q**n),
            ("MC.C12.PROB.SUCCESS_FAILURE_SWAPPED", pr**n + n * q * pr ** (n - 1)),
        ]
    return case(
        fam="PROB.BINOMIAL", md=md, names=["probability"], value=key,
        stem=f"A biased coin shows heads with probability {ps}. It is tossed {n} times, each toss independent of the others. Find the probability of {ask}.",
        steps=["The number of heads follows a binomial pattern: each outcome with i heads has probability p to the i times q to the n minus i, and there are n choose i ways to place the heads.", "Add the cases that belong to the event asked.", f"The probability is {fr(key)}."],
        hints=hints3(p, ["How many different orders can the heads appear in?", "Name success, failure and their probabilities first.", "Decide which counts of heads belong to the event."],
                     "For each allowed number of heads, multiply the number of arrangements by the probability of one arrangement, then add the cases.",
                     "Full method: list the allowed head counts, compute n choose i times p to the i times q to the n minus i for each, add, and simplify. A complement can save work for at least one."),
        wrong=wrong, base=0.5, role="apply", prediction="Is the event likely or unlikely?", slug=slug(n, ps, kind, k), nsteps=4,
        methods=[("c12.bin.formula", "closed_form", "binomial_formula", _bin_formula), ("c12.bin.enumeration", "enumeration", "", _bin_enum), ("c12.bin.dp", "dynamic_programming", "", _bin_dp)],
    )  # fmt: skip


# ================================================================ PROB.RV_MEAN_VAR


def _rv_stats(md: Mapping[str, Any]) -> tuple[Fraction, Fraction]:
    xs, ws = md["x"], md["w"]
    tot = sum(ws)
    mean = F(sum(x * w for x, w in zip(xs, ws, strict=True)), tot)
    var = F(sum(x * x * w for x, w in zip(xs, ws, strict=True)), tot) - mean * mean
    return mean, var


def _rv_a(md: Mapping[str, Any]) -> Fraction:
    mean, var = _rv_stats(md)
    return mean if md["ask"] == "mean" else var


def _rv_population(md: Mapping[str, Any]) -> Fraction:
    pop = [x for x, w in zip(md["x"], md["w"], strict=True) for _ in range(w)]
    mean = F(sum(pop), len(pop))
    return mean if md["ask"] == "mean" else sum((v - mean) ** 2 for v in pop) / len(pop)


def _rv_definition(md: Mapping[str, Any]) -> Fraction:
    tot = sympy.Integer(sum(md["w"]))
    probs = [sympy.Integer(w) / tot for w in md["w"]]
    mean = sum(sympy.Integer(x) * pr for x, pr in zip(md["x"], probs, strict=True))
    if md["ask"] == "mean":
        return kit.unsp(mean)
    return kit.unsp(
        sum((sympy.Integer(x) - mean) ** 2 * pr for x, pr in zip(md["x"], probs, strict=True))
    )


@model(
    "PROB.RV_MEAN_VAR", chapter=PROB, title="Find the mean or variance of a random variable from its distribution",
    prereq=[PRE_FRAC], marks=3, technique="expectation_sum", version="2",
    box={"x0": {"choices": [0, 1]}, "wseed": {"min": 0, "max": 14}, "ask": {"choices": ["mean", "variance"]}},
)  # fmt: skip
def prob_rv(p: Mapping[str, Any]) -> Built:
    x0, ws, ask = int(p["x0"]), int(p["wseed"]), str(p["ask"])
    xs = [x0 + i for i in range(4)]
    w = kit.lcg(ws + 3, 4, 1, 5)
    if math.gcd(*w) != 1 or len(set(w)) < 3:
        raise IllPosed("weights_not_varied")
    md = {"x": xs, "w": w, "ask": ask}
    key = _rv_a(md)
    mean, var = _rv_stats(md)
    tot = sum(w)
    second = F(sum(x * x * ww for x, ww in zip(xs, w, strict=True)), tot)
    if ask == "mean":
        wrong = [
            (
                "MC.C12.PROB.WEIGHTS_NOT_DIVIDED_BY_TOTAL",
                F(sum(x * ww for x, ww in zip(xs, w, strict=True))),
            ),
            ("MC.C12.PROB.VALUES_AVERAGED_WITHOUT_PROBABILITIES", F(sum(xs), 4)),
            (
                "MC.C12.PROB.PROBABILITY_WEIGHTED_WRONG_VALUE",
                F(sum(xs[3 - i] * w[i] for i in range(4)), tot),
            ),
            ("MC.C12.PROB.MOST_LIKELY_VALUE_REPORTED", F(xs[w.index(max(w))])),
        ]
    else:
        wrong = [
            ("MC.C12.PROB.MEAN_NOT_SQUARED", second - mean),
            ("MC.C12.PROB.SECOND_MOMENT_AS_VARIANCE", second),
            ("MC.C12.PROB.STANDARD_DEVIATION_STYLE_SLIP", var * var),
            ("MC.C12.PROB.MEAN_REPORTED", mean),
        ]
    return case(
        fam="PROB.RV_MEAN_VAR", md=md, names=["value"], value=key,
        stem=pick([f"A random variable X takes the values {', '.join(map(str, xs))} with probabilities in the ratio {' : '.join(map(str, w))}. Find the {ask} of X.", f"The probabilities of X taking the values {', '.join(map(str, xs))} are in the ratio {' : '.join(map(str, w))}. What is the {ask} of X?", f"Let X be a random variable with values {', '.join(map(str, xs))}, whose probabilities stand in the ratio {' : '.join(map(str, w))}. Calculate the {ask}."], p),
        steps=[f"The ratios add to {tot}, so the probabilities are each ratio divided by {tot}.", f"The mean is the sum of value times probability: {fr(mean)}.", f"The variance is the mean of the squares minus the square of the mean: {fr(var)}." if ask == "variance" else "That is the asked mean.", f"The answer is {fr(key)}."],
        hints=hints3(p, ["Probabilities must add to one: what must you do to the ratio numbers?", "Turn the ratio into probabilities before any other step.", "Write the distribution as one table."],
                     "Divide each ratio number by their total, then use the sum of value times probability for the mean.",
                     "Full method: probabilities from the ratio, mean as the sum of value times probability, and for the variance the mean of squares minus the square of the mean."),
        wrong=wrong, base=0.5, role="apply", prediction="Should the mean lie between the smallest and largest value?", slug=slug(x0, ws, ask), nsteps=4,
        methods=[("c12.rv.formula", "closed_form", "expectation_sum", _rv_a), ("c12.rv.population", "counting_population", "", _rv_population), ("c12.rv.definition", "sympy.rational_definition", "", _rv_definition)],
    )  # fmt: skip
