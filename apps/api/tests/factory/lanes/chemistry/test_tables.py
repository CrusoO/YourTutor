"""Golden vectors: the reviewed tables against code written independently of them."""

from __future__ import annotations

import pytest

from app.factory.kernel.constants import atomic_mass
from app.factory.lanes.chemistry import structure as S
from app.factory.lanes.chemistry import tables as T
from app.factory.lanes.chemistry.balance import (
    classify_by_rule,
    is_balanced,
    solve_own,
    solve_sympy,
)
from app.factory.lanes.chemistry.formula import atoms, atoms_expanded
from app.factory.lanes.chemistry.ions import crisscross, search_smallest
from app.factory.lanes.chemistry.metals import ORDER_COMBOS, orders_agree


@pytest.mark.parametrize("rid", [r[0] for r in T.REACTIONS])
def test_hand_balanced_coefficients_match_both_solvers(rid):
    _, kind, left, right, coef = T.REACTION_BY_ID[rid]
    assert is_balanced(list(left), list(right), list(coef))
    assert solve_own(list(left), list(right)) == list(coef)
    assert solve_sympy(list(left), list(right)) == list(coef)
    assert classify_by_rule(list(left), list(right)) == kind


def test_reaction_table_covers_all_four_types_and_ids_are_unique():
    assert {r[1] for r in T.REACTIONS} == set(T.TYPES)
    assert len({r[0] for r in T.REACTIONS}) == len(T.REACTIONS)
    assert len(T.REACTIONS) >= 70


def test_every_table_element_has_a_house_atomic_mass():
    for r in T.REACTIONS:
        for f in (*r[2], *r[3]):
            for el in atoms(f):
                assert atomic_mass(el)


def test_two_formula_readers_agree_on_every_formula():
    from app.factory.lanes.chemistry.balance import ATOM_FORMULAS

    for r in T.REACTIONS:
        for f in (*r[2], *r[3]):
            assert atoms(f) == atoms_expanded(f)
    for f in ATOM_FORMULAS:
        assert atoms(f) == atoms_expanded(f)


@pytest.mark.parametrize(("qc", "qa"), [(c, a) for c in (1, 2, 3) for a in (1, 2, 3)])
def test_crisscross_and_search_agree_and_cancel_charge(qc, qa):
    m, n = crisscross(qc, qa)
    assert (m, n) == search_smallest(qc, qa)
    assert m * qc == n * qa


def test_series_and_potentials_disagree_exactly_where_recorded():
    metals = list(T.SCHOOL_SERIES)
    bad = {frozenset((a, b)) for a in metals for b in metals if a != b and not orders_agree(a, b)}
    assert bad == {frozenset(("Na", "Ca")), frozenset(("Hg", "Ag"))}
    assert all("Hg" not in c and not {"Na", "Ca"} <= set(c) for c in ORDER_COMBOS)


def test_isomer_counts_by_two_methods_match_the_published_sequence():
    for n in range(1, 11):
        assert S.otter_count(n) == T.ALKANE_ISOMERS_OEIS[n]
    for n in range(1, 9):
        assert len(S.enumerate_alkanes(n)) == T.ALKANE_ISOMERS_OEIS[n]


@pytest.mark.parametrize("formula", sorted(T.ALKANE_NAMES))
def test_alkane_namer_matches_the_hand_written_table(formula):
    tree = S.parse_condensed(formula)
    assert S.name_alkane(tree) == T.ALKANE_NAMES[formula]


@pytest.mark.parametrize("formula", sorted({**T.ALKENE_NAMES, **T.ALKYNE_NAMES}))
def test_unsaturated_namer_matches_the_hand_written_table(formula):
    table = {**T.ALKENE_NAMES, **T.ALKYNE_NAMES}
    assert S.name_unsaturated(S.parse_condensed(formula)) == table[formula]


def test_functional_namer_matches_the_hand_written_table():
    for group, names in T.FUNCTIONAL.items():
        for n, name in names.items():
            assert S.name_functional(S.functional_formula(group, n)) == (name, n)


def test_isomers_written_two_ways_get_one_name():
    names = {}
    for formula, name in T.ALKANE_NAMES.items():
        names.setdefault(name, set()).add(S.carbon_count(S.parse_condensed(formula)))
    assert all(len(v) == 1 for v in names.values())


@pytest.mark.parametrize("bad", ["CH3-CH(CH3)", "CH3-CH4", "CH2-CH2", "CH3-X", "CH3-CH3-CH3"])
def test_a_malformed_condensed_formula_is_refused(bad):
    with pytest.raises(S.StructureError):
        S.parse_condensed(bad)
