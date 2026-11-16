# ruff: noqa: E501
"""Golden values for the reference methods: they must agree with hand-computed answers."""

from fractions import Fraction

from app.factory.lanes.maths.reference import quad, trig
from app.factory.lanes.maths.surd import S, fmt, sqrt_of

F = Fraction


def test_surd_pair_text_goldens():
    # roots of x^2 - 2x - 4 = 0 are 1 +- sqrt5; of 2x^2 + 3x - 1 = 0 are (-3 +- sqrt17)/4
    assert quad.surd_pair_text(F(1), F(5)) == "1 ± √5"
    assert quad.surd_pair_text(F(-3, 4), F(17, 16)) == "(-3 ± √17)/4"
    assert quad.surd_pair_text(F(0), F(12)) == "±2√3"
    assert quad.surd_pair_text(F(0), F(3, 4)) == "±√3/2"


def test_squarefree():
    assert (
        quad.squarefree(72) == (6, 2)
        and quad.squarefree(17) == (1, 17)
        and quad.squarefree(48) == (4, 3)
    )


def test_three_engines_agree_on_a_quadratic():
    spec = {"lhs": [-30, -4, 2], "rhs": []}
    infos = [fn(spec) for fn in quad.ENGINES.values()]
    for info in infos:
        assert (info["c"], info["b"], info["a"], info["D"]) == (-30, -4, 2, 256)
        assert info["roots"] == [F(-3), F(5)]


def test_interp_reads_a_disguised_form_without_the_coefficient_lists():
    spec = {"lhs": [8, 1, 2], "rhs": [3, -4]}  # 2x^2 + x + 8 = -4x + 3  ->  2x^2 + 5x + 5
    info = quad.info_interp(spec)
    assert (
        (info["a"], info["b"], info["c"]) == (2, 5, 5)
        and info["D"] == -15
        and info["roots"] is None
    )


def test_special_triangle_ratios_and_conversion():
    model = {"angle": 30, "known": "adjacent", "unknown": "opposite", "value": ["0", "10"]}
    assert fmt(trig.tri_closed(model)) == "10"  # adjacent 10*sqrt3, tan 30 = 1/sqrt3
    for method in (trig.tri_closed, trig.tri_sympy, trig.tri_numeric):
        assert method(
            {"angle": 60, "known": "adjacent", "unknown": "opposite", "value": ["7", "0"]}
        ) == S(0, 0, 7)


def test_three_methods_agree_for_two_positions():
    model = {"angles": [30, 60], "separation": ["20", "0"]}
    results = {trig.two_closed(model), trig.two_sympy(model), trig.two_numeric(model)}
    assert results == {sqrt_of(3) * 10}
    model = {"angles": [45, 60], "separation": ["6", "0"]}
    assert trig.two_closed(model) == trig.two_sympy(model) == trig.two_numeric(model)
    assert fmt(trig.two_closed(model)) == "9 + 3√3"


def test_table_values_match_the_special_triangles():
    for ang in (30, 45, 60):
        opp, adj, hyp = trig.RATIOS[ang]
        assert (
            trig.SIN[ang] == opp / hyp and trig.COS[ang] == adj / hyp and trig.TAN[ang] == opp / adj
        )
    assert trig.TAN[90] is None
