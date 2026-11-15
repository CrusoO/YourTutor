"""The ONE reviewed constants table (owner decision D7, 14 Nov 2026).

House values are school-style (g = 9.8 m/s^2, R = 8.314 J/(mol K), CBSE-style rounded atomic
masses). Change a value only by editing this file in a reviewed PR: the table is versioned and
hashed, the hash is pinned in tests/factory/test_constants.py, and every certificate records it,
so any edit invalidates all earlier certificates (fail closed).

NIST and IUPAC data are cross-checks only until counsel has answered; no values are copied from
a textbook. `reviewed` is false until the owner signs the table off.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.factory.kernel.exact import Reject, chash

CONSTANTS_VERSION = "2026-11-14.1"
CONSTANTS_REVIEWED = False  # owner review of the house values is pending


@dataclass(frozen=True)
class Constant:
    id: str
    value: str  # exact decimal string
    unit: str
    source: str


_HOUSE = "house value, school style (owner decision D7)"

PHYSICAL: tuple[Constant, ...] = (
    Constant("g_earth", "9.8", "m/s^2", _HOUSE),
    Constant("R_gas", "8.314", "J/mol/K", _HOUSE),
    Constant("c_light", "3e8", "m/s", _HOUSE),
    Constant("N_A", "6.022e23", "1/mol", _HOUSE),
    Constant("e_charge", "1.6e-19", "C", _HOUSE),
    Constant("h_planck", "6.63e-34", "J*s", _HOUSE),
    Constant("G_grav", "6.67e-11", "N*m^2/kg^2", _HOUSE),
    Constant("F_faraday", "96500", "C/mol", _HOUSE),
    Constant("V_molar_stp", "22.4", "L/mol", _HOUSE),
    Constant("K_celsius_offset", "273", "K", _HOUSE),
)

# Atomic masses in g/mol, rounded the way school papers use them.
ATOMIC_MASSES: tuple[tuple[str, str], ...] = (
    ("H", "1"), ("He", "4"), ("Li", "7"), ("Be", "9"), ("B", "11"), ("C", "12"), ("N", "14"),
    ("O", "16"), ("F", "19"), ("Ne", "20"), ("Na", "23"), ("Mg", "24"), ("Al", "27"),
    ("Si", "28"), ("P", "31"), ("S", "32"), ("Cl", "35.5"), ("Ar", "40"), ("K", "39"),
    ("Ca", "40"), ("Mn", "55"), ("Fe", "56"), ("Ni", "59"), ("Cu", "63.5"), ("Zn", "65"),
    ("Br", "80"), ("Ag", "108"), ("I", "127"), ("Ba", "137"), ("Au", "197"), ("Hg", "201"),
    ("Pb", "207"),
)  # fmt: skip

_BY_ID = {c.id: c for c in PHYSICAL}
_MASS = dict(ATOMIC_MASSES)


def constants_hash() -> str:
    return chash(
        {
            "version": CONSTANTS_VERSION,
            "physical": [[c.id, c.value, c.unit, c.source] for c in PHYSICAL],
            "atomic_masses": [list(pair) for pair in ATOMIC_MASSES],
        }
    )


def constant(const_id: str) -> Constant:
    try:
        return _BY_ID[const_id]
    except KeyError:
        raise Reject("unknown_constant", const_id) from None


def atomic_mass(symbol: str) -> str:
    try:
        return _MASS[symbol]
    except KeyError:
        raise Reject("unknown_element", symbol) from None
