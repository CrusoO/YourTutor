"""Lane constants for Class 12 physics: the ONE table this lane reads, kernel values first.

The kernel table (kernel/constants.py) already holds g, c, e, h, G and N_A. Class 12 also needs
a few school constants the kernel table does not have (k, epsilon0, mu0 and some atomic ones).
They live here, in one hashed table, so a change is visible and pinned by a test. Values are the
rounded numbers a school paper uses, nothing is copied from a textbook, and `reviewed` stays
False until a person signs the table off. A stem always states every constant it uses.
"""

from __future__ import annotations

from app.factory.kernel import constants as kernel_constants
from app.factory.kernel.constants import Constant
from app.factory.kernel.exact import Reject, chash

LANE_CONSTANTS_VERSION = "2026-11-26.1"
LANE_CONSTANTS_REVIEWED = False  # a person must review these values before anything is served

_HOUSE = "house value, school style (lane table, not yet reviewed)"

LOCAL: tuple[Constant, ...] = (
    Constant("k_coulomb", "9e9", "Nm2/C2", _HOUSE),
    Constant("eps0", "8.85e-12", "C^2/N/m^2", _HOUSE),
    Constant("mu0", "1.256e-6", "N/A^2", _HOUSE),
    Constant("mu0_4pi", "1e-7", "N/A^2", _HOUSE),
    Constant("E_hydrogen", "13.6", "eV", _HOUSE),
    Constant("a0_bohr", "0.53e-10", "m", _HOUSE),
    Constant("v_bohr", "2.2e6", "m/s", _HOUSE),
    Constant("u_energy", "931.5", "MeV/u", _HOUSE),
    Constant("rydberg", "1.1e7", "per_m", _HOUSE),
)
_LOCAL = {c.id: c for c in LOCAL}

# how a stem states each constant it uses: "{v}" is replaced by the number and unit
PHRASE = {
    "g_earth": "{sym} = {v}",
    "c_light": "the speed of light in vacuum, {sym}, = {v}",
    "e_charge": "the charge of one electron, {sym}, = {v}",
    "h_planck": "Planck's constant, {sym}, = {v}",
    "k_coulomb": "{sym} = {v}",
    "eps0": "the permittivity of free space, {sym}, = {v}",
    "mu0": "the permeability of free space, {sym}, = {v}",
    "mu0_4pi": "{sym} (the permeability of free space divided by 4 pi) = {v}",
    "E_hydrogen": "the ground state energy of hydrogen, {sym}, = -{v}",
    "a0_bohr": "the radius of the first Bohr orbit, {sym}, = {v}",
    "v_bohr": "the speed of the electron in the first Bohr orbit, {sym}, = {v}",
    "u_energy": "the energy equivalent of one atomic mass unit, {sym}, = {v}",
    "rydberg": "the Rydberg constant, {sym}, = {v}",
}


def lane_constants_hash() -> str:
    return chash(
        {
            "version": LANE_CONSTANTS_VERSION,
            "local": [[c.id, c.value, c.unit, c.source] for c in LOCAL],
            "kernel": kernel_constants.constants_hash(),
        }
    )


def constant(const_id: str) -> Constant:
    """A constant by id: this lane's table first, then the kernel table."""
    if const_id in _LOCAL:
        return _LOCAL[const_id]
    try:
        return kernel_constants.constant(const_id)
    except Reject:
        raise Reject("unknown_constant", const_id) from None
