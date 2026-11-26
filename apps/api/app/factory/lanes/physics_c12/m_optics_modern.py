# ruff: noqa: E501
"""Class 12 models, part 3: optics, dual nature, atoms, nuclei and semiconductor electronics.

All wording is original. See m_electric.py for the expression conventions.
"""

from __future__ import annotations

from app.factory.lanes.physics_c12.kit import P, bases, model, reg, var
from app.factory.lanes.physics_c12.quantities import to_si

# ---------------------------------------------------------------- ray optics and instruments
LENS_MAKER = reg(
    model(
        "RAY.LENS_MAKER",
        "RAY",
        "lens_makers_formula",
        "a thin double convex lens in air",
        syms={"f": "m", "n": "unit", "R1": "m", "R2": "m"},
        labels={
            "f": ("focal length", "the focal length is {v}"),
            "n": ("refractive index", "the refractive index of the glass is {v}"),
            "R1": ("first radius", "the radius of curvature of the first face is {v}"),
            "R2": ("second radius", "the radius of curvature of the second face is {v}"),
        },
        base=bases({"n": ("n", "unit"), "R1": ("R1", "cm"), "R2": ("R2", "cm")}),
        derived=lambda p: (("f", "1/((n-1)*(1/R1+1/R2))"),),
        dunits={"f": "cm"},
        laws=("(n - 1)*(R1 + R2)*f - R1*R2",),
        variants={
            v.id: v
            for v in (
                var(
                    "f",
                    "n R1 R2",
                    "1/((n-1)*(1/R1+1/R2))",
                    "1/f = (n - 1) x (1/R1 + 1/R2) for a double convex lens, with the radii as positive numbers",
                    "Find the focal length of the lens.",
                    [
                        ("RECIPROCAL_FORGOTTEN", "@(n-1)*(1/R1_r+1/R2_r)"),
                        ("INDEX_MINUS_ONE_FORGOTTEN", "1/(n*(1/R1+1/R2))"),
                        ("RADII_SUBTRACTED", "1/((n-1)*(1/R1-1/R2))"),
                        ("RADII_ADDED_NOT_RECIPROCAL", "1/((n-1)*(R1+R2))"),
                    ],
                ),
                var(
                    "n",
                    "f R1 R2",
                    "1+R1*R2/(f*(R1+R2))",
                    "1/f = (n - 1) x (1/R1 + 1/R2), so n = 1 + 1/(f x (1/R1 + 1/R2))",
                    "Find the refractive index of the glass.",
                    [
                        ("ONE_FORGOTTEN", "R1*R2/(f*(R1+R2))"),
                        ("ONE_ADDED_TWICE", "2+R1*R2/(f*(R1+R2))"),
                        ("RECIPROCAL_FORGOTTEN", "1+f*(1/R1+1/R2)"),
                    ],
                    laws=("(n - 1)*(R1 + R2)*f - R1*R2",),
                ),
                var(
                    "R1",
                    "n f R2",
                    "1/(1/((n-1)*f)-1/R2)",
                    "1/f = (n - 1) x (1/R1 + 1/R2), so 1/R1 = 1/((n - 1) x f) - 1/R2",
                    "Find the radius of curvature of the first face.",
                    [
                        ("INDEX_MINUS_ONE_FORGOTTEN", "1/(1/(n*f)-1/R2)"),
                        ("RADII_ADDED", "1/(1/((n-1)*f)+1/R2)"),
                        ("RECIPROCAL_FORGOTTEN", "1/((n-1)*f)-1/R2"),
                    ],
                    laws=("(n - 1)*(R1 + R2)*f - R1*R2",),
                ),
            )
        },
    ),
    "Use the lens maker's formula for the focal length, refractive index or a radius",
    (P + "RECIPROCALS", P + "REARRANGE_FORMULA", P + "LENS_BASICS"),
)

SPH_REFRACT = reg(
    model(
        "RAY.SPH_REFRACT",
        "RAY",
        "refraction_at_a_spherical_surface",
        "refraction at a curved glass surface",
        syms={"v": "m", "n": "unit", "R": "m", "d": "m"},
        labels={
            "v": ("image distance", "the image forms {v} from the surface inside the glass"),
            "n": ("refractive index", "the refractive index of the glass is {v}"),
            "R": ("radius", "the radius of curvature of the convex surface is {v}"),
            "d": ("object distance", "a point object in air is {v} from the surface on its axis"),
        },
        base=bases({"n": ("n", "unit"), "R": ("R", "cm"), "d": ("d", "cm")}),
        derived=lambda p: (("v", "n*R*d/((n-1)*d+R)"),),
        dunits={"v": "cm"},
        laws=("n*R*d - v*((n - 1)*d + R)",),
        variants={
            v.id: v
            for v in (
                var(
                    "v",
                    "n R d",
                    "n*R*d/((n-1)*d+R)",
                    "n/v - 1/d = (n - 1)/R, with the distances as positive numbers for a real object and a real image in the glass",
                    "Find the distance of the image from the surface.",
                    [
                        ("INDEX_FORGOTTEN_IN_NUMERATOR", "R*d/((n-1)*d+R)"),
                        ("DISTANCES_SWAPPED", "n*R*d/((n-1)*R+d)"),
                        ("INDEX_MINUS_ONE_FORGOTTEN", "n*R*d/(n*d+R)"),
                        ("OBJECT_DISTANCE_SIGN_SLIP", "n*R*d/((n-1)*d-R)"),
                    ],
                ),
                var(
                    "d",
                    "n R v",
                    "1/(n/v-(n-1)/R)",
                    "n/v - 1/d = (n - 1)/R, so 1/d = n/v - (n - 1)/R",
                    "Find the distance of the object from the surface.",
                    [
                        ("INDEX_MINUS_ONE_FORGOTTEN", "1/(n/v-n/R)"),
                        ("TERMS_ADDED", "1/(n/v+(n-1)/R)"),
                        ("INDEX_FORGOTTEN", "1/(1/v-(n-1)/R)"),
                    ],
                    laws=("n*R*d - v*((n - 1)*d + R)",),
                ),
            )
        },
    ),
    "Use the single surface refraction formula for a real object and a convex glass surface",
    (P + "RECIPROCALS", P + "REARRANGE_FORMULA", "PHY.C12.RAY.LENS_MAKER"),
)

TELESCOPE = reg(
    model(
        "RAY.TELESCOPE",
        "RAY",
        "astronomical_telescope",
        "an astronomical telescope in normal adjustment",
        syms={"M": "unit", "fo": "m", "fe": "m", "L": "m"},
        labels={
            "M": ("magnifying power", "the magnifying power is {v}"),
            "fo": ("objective focal length", "the focal length of the objective is {v}"),
            "fe": ("eyepiece focal length", "the focal length of the eyepiece is {v}"),
            "L": ("tube length", "the distance between the lenses is {v}"),
        },
        base=bases({"fo": ("fo", "cm"), "fe": ("fe", "cm")}),
        derived=lambda p: (("M", "fo/fe"), ("L", "fo+fe")),
        dunits={"M": "unit", "L": "cm"},
        laws=("M*fe - fo",),
        variants={
            v.id: v
            for v in (
                var(
                    "M",
                    "fo fe",
                    "fo/fe",
                    "M = fo / fe in normal adjustment",
                    "Find the magnifying power.",
                    [
                        ("RATIO_INVERTED", "fe/fo"),
                        ("FOCAL_LENGTHS_ADDED", "(fo+fe)/fe"),
                        ("FOCAL_LENGTHS_MULTIPLIED", "@fo_r*fe_r"),
                        ("UNIT_PREFIX_SLIP", "@fo_r/fe_r*10"),
                    ],
                ),
                var(
                    "fo",
                    "M fe",
                    "M*fe",
                    "M = fo / fe in normal adjustment",
                    "Find the focal length of the objective.",
                    [
                        ("DIVIDED_NOT_MULTIPLIED", "fe/M"),
                        ("MAGNIFICATION_ADDED", "M+fe"),
                        ("EYEPIECE_COPIED", "fe"),
                    ],
                    laws=("M*fe - fo",),
                    rearr="multiply each side by fe",
                ),
                var(
                    "fe",
                    "M fo",
                    "fo/M",
                    "M = fo / fe in normal adjustment",
                    "Find the focal length of the eyepiece.",
                    [
                        ("MULTIPLIED_NOT_DIVIDED", "fo*M"),
                        ("FORMULA_INVERTED", "M/fo"),
                        ("OBJECTIVE_COPIED", "fo"),
                    ],
                    laws=("M*fe - fo",),
                    rearr="divide each side by M",
                ),
                var(
                    "L",
                    "fo fe",
                    "fo+fe",
                    "tube length = fo + fe in normal adjustment",
                    "Find the distance between the two lenses.",
                    [
                        ("FOCAL_LENGTHS_SUBTRACTED", "fo-fe"),
                        ("FOCAL_LENGTHS_MULTIPLIED", "@fo_r*fe_r"),
                        ("RATIO_USED", "@fo_r/fe_r"),
                    ],
                    laws=("L - fo - fe",),
                ),
                var(
                    "fe",
                    "L fo",
                    "L-fo",
                    "tube length = fo + fe in normal adjustment",
                    "Find the focal length of the eyepiece.",
                    [
                        ("TUBE_LENGTH_ADDED", "L+fo"),
                        ("TUBE_LENGTH_COPIED", "L"),
                        ("RATIO_USED", "@L_r/fo_r"),
                    ],
                    laws=("L - fo - fe",),
                    rearr="subtract fo from each side",
                ),
            )
        },
    ),
    "Find the magnifying power, a focal length or the tube length of an astronomical telescope",
    (P + "RATIO_PROPORTION", P + "REARRANGE_FORMULA", "PHY.C12.RAY.LENS_MAKER"),
)

# ---------------------------------------------------------------- wave optics
YDSE = reg(
    model(
        "WAVE.YDSE",
        "WAVE",
        "double_slit_fringes",
        "Young's double slit experiment",
        syms={"beta": "m", "lam": "m", "D": "m", "d": "m", "n": "unit", "x": "m"},
        labels={
            "beta": ("fringe width", "the fringe width is {v}"),
            "lam": ("wavelength", "the wavelength of the light is {v}"),
            "D": ("screen distance", "the screen is {v} from the slits"),
            "d": ("slit separation", "the slits are {v} apart"),
            "n": ("fringe order", "the order of the bright fringe is {v}"),
            "x": ("position", "the bright fringe is {v} from the centre"),
        },
        base=bases({"lam": ("lam", "nm"), "D": ("D", "m"), "d": ("d", "mm"), "n": ("n", "unit")}),
        derived=lambda p: (("beta", "lam*D/d"), ("x", "n*lam*D/d")),
        dunits={"beta": "mm", "x": "mm"},
        laws=("beta*d - lam*D",),
        variants={
            v.id: v
            for v in (
                var(
                    "beta",
                    "lam D d",
                    "lam*D/d",
                    "fringe width = wavelength x D / d",
                    "Find the fringe width.",
                    [
                        ("SLIT_SEPARATION_MULTIPLIED", "lam*D*d"),
                        ("FORMULA_INVERTED", "d/(lam*D)"),
                        ("WAVELENGTH_UNIT_SLIP", "lam_r*D/d"),
                        ("SLIT_UNIT_SLIP", "lam*D/d_r"),
                    ],
                ),
                var(
                    "lam",
                    "beta D d",
                    "beta*d/D",
                    "fringe width = wavelength x D / d",
                    "Find the wavelength of the light.",
                    [
                        ("FORMULA_INVERTED", "D/(beta*d)"),
                        ("SLIT_SEPARATION_DIVIDED", "beta/(d*D)"),
                        ("SLIT_UNIT_SLIP", "beta*d_r/D"),
                    ],
                    laws=("beta*d - lam*D",),
                    rearr="multiply each side by d and divide each side by D",
                ),
                var(
                    "d",
                    "beta lam D",
                    "lam*D/beta",
                    "fringe width = wavelength x D / d",
                    "Find the separation of the slits.",
                    [
                        ("FORMULA_INVERTED", "beta/(lam*D)"),
                        ("WAVELENGTH_UNIT_SLIP", "lam_r*D/beta"),
                        ("SCREEN_DISTANCE_FORGOTTEN", "lam/beta"),
                    ],
                    laws=("beta*d - lam*D",),
                ),
                var(
                    "D",
                    "beta lam d",
                    "beta*d/lam",
                    "fringe width = wavelength x D / d",
                    "Find the distance from the slits to the screen.",
                    [
                        ("FORMULA_INVERTED", "lam/(beta*d)"),
                        ("SLIT_SEPARATION_FORGOTTEN", "beta/lam"),
                        ("WAVELENGTH_UNIT_SLIP", "beta*d/lam_r"),
                    ],
                    laws=("beta*d - lam*D",),
                ),
                var(
                    "x",
                    "n lam D d",
                    "n*lam*D/d",
                    "the n-th bright fringe is at x = n x wavelength x D / d",
                    "Find the distance of that bright fringe from the central one.",
                    [
                        ("ORDER_FORGOTTEN", "lam*D/d"),
                        ("ORDER_ADDED_ONE", "(n+1)*lam*D/d"),
                        ("FORMULA_INVERTED", "d/(n*lam*D)"),
                        ("WAVELENGTH_UNIT_SLIP", "n*lam_r*D/d"),
                    ],
                    laws=("x*d - n*lam*D",),
                ),
            )
        },
    ),
    "Find the fringe width, the wavelength, or a distance in a double slit experiment",
    (P + "REARRANGE_FORMULA", P + "UNIT_PREFIXES", P + "SCI_NOTATION"),
)

MALUS = reg(
    model(
        "WAVE.MALUS",
        "WAVE",
        "malus_law",
        "polarised light through an analyser",
        syms={"I0": "W/m^2", "I": "W/m^2", "I2": "W/m^2", "cs": "unit"},
        labels={
            "I0": ("incident intensity", "the intensity of the incident light is {v}"),
            "I": ("transmitted intensity", "the transmitted intensity is {v}"),
            "I2": ("final intensity", "the final intensity is {v}"),
            "cs": (
                "cosine of the angle",
                "the cosine of the angle between the pass directions is {v}",
            ),
        },
        base=bases({"I0": ("I0", "W/m^2"), "cs": ("cs", "unit")}),
        derived=lambda p: (("I", "I0*cs^2"), ("I2", "I0*cs^2/2")),
        dunits={"I": "W/m^2", "I2": "W/m^2"},
        laws=("I - I0*cs**2",),
        variants={
            v.id: v
            for v in (
                var(
                    "I",
                    "I0 cs",
                    "I0*cs^2",
                    "I = I0 x cosine squared of the angle for polarised light",
                    "Find the transmitted intensity.",
                    [
                        ("COSINE_NOT_SQUARED", "I0*cs"),
                        ("HALF_USED_FOR_POLARISED_LIGHT", "I0*cs^2/2"),
                        ("SQUARE_OF_INTENSITY", "I0^2*cs^2/100"),
                        ("COSINE_DIVIDED", "I0/cs^2"),
                    ],
                ),
                var(
                    "I0",
                    "I cs",
                    "I/cs^2",
                    "I = I0 x cosine squared of the angle for polarised light",
                    "Find the intensity of the incident light.",
                    [
                        ("COSINE_NOT_SQUARED", "I/cs"),
                        ("MULTIPLIED_NOT_DIVIDED", "I*cs^2"),
                        ("ROOT_TAKEN", "I/cs^2/2"),
                    ],
                    laws=("I - I0*cs**2",),
                    rearr="divide each side by cosine squared of the angle",
                ),
                var(
                    "cs",
                    "I I0",
                    "sqrt(I/I0)",
                    "I = I0 x cosine squared of the angle for polarised light",
                    "Find the cosine of the angle.",
                    [
                        ("ROOT_FORGOTTEN", "I/I0"),
                        ("FORMULA_INVERTED", "sqrt(I0/I)"),
                        ("RATIO_INVERTED", "I0/I"),
                    ],
                    laws=("I - I0*cs**2",),
                    rearr="divide each side by I0, then take the square root",
                ),
                var(
                    "I2",
                    "I0 cs",
                    "I0*cs^2/2",
                    "unpolarised light loses half of its intensity at the first polariser, then I2 = (I0 / 2) x cosine squared of the angle",
                    "Find the intensity after the second polariser.",
                    [
                        ("HALF_FORGOTTEN", "I0*cs^2"),
                        ("COSINE_NOT_SQUARED", "I0*cs/2"),
                        ("HALF_APPLIED_TWICE", "I0*cs^2/4"),
                    ],
                    laws=("I2*2 - I0*cs**2",),
                ),
            )
        },
    ),
    "Use Malus's law for polarised light, and the half rule for unpolarised light",
    (P + "REARRANGE_FORMULA", P + "RATIO_PROPORTION"),
)

# ---------------------------------------------------------------- dual nature of radiation and matter
PHOTOELECTRIC = reg(
    model(
        "DUAL.PHOTOELECTRIC",
        "DUAL",
        "einstein_photoelectric_equation",
        "the photoelectric effect at a metal surface",
        syms={
            "Eph": "J",
            "phi": "J",
            "K": "J",
            "V0": "V",
            "f": "Hz",
            "Kj": "J",
            "h": "J*s",
            "e": "C",
        },
        labels={
            "Eph": ("photon energy", "the energy of each photon is {v}"),
            "phi": ("work function", "the work function of the metal is {v}"),
            "K": (
                "maximum kinetic energy",
                "the maximum kinetic energy of the emitted electrons is {v}",
            ),
            "V0": ("stopping potential", "the stopping potential is {v}"),
            "f": ("frequency", "the frequency of the light is {v}"),
            "Kj": (
                "maximum kinetic energy",
                "the maximum kinetic energy of the emitted electrons is {v}",
            ),
        },
        base=bases({"Eph": ("Eph", "eV"), "phi": ("phi", "eV"), "f": ("f", "Hz")}),
        derived=lambda p: (("K", "Eph-phi"), ("V0", "(Eph-phi)/e"), ("Kj", "h*f-phi")),
        dunits={"K": "eV", "V0": "V", "Kj": "J"},
        consts={"h": "h_planck", "e": "e_charge"},
        laws=("K - Eph + phi",),
        variants={
            v.id: v
            for v in (
                var(
                    "K",
                    "Eph phi",
                    "Eph-phi",
                    "K = photon energy - work function",
                    "Find the maximum kinetic energy of the emitted electrons.",
                    [
                        ("WORK_FUNCTION_ADDED", "Eph+phi"),
                        ("ENERGIES_MULTIPLIED", "@Eph_r*phi_r"),
                        ("ENERGIES_DIVIDED", "@Eph_r/phi_r"),
                        ("PHOTON_ENERGY_USED_AS_K", "Eph"),
                    ],
                ),
                var(
                    "phi",
                    "Eph K",
                    "Eph-K",
                    "K = photon energy - work function",
                    "Find the work function of the metal.",
                    [
                        ("KINETIC_ENERGY_ADDED", "Eph+K"),
                        ("ENERGIES_MULTIPLIED", "@Eph_r*K_r"),
                        ("KINETIC_ENERGY_COPIED", "K"),
                    ],
                    laws=("K - Eph + phi",),
                    rearr="rearrange K = photon energy - work function for the work function",
                ),
                var(
                    "Eph",
                    "K phi",
                    "K+phi",
                    "K = photon energy - work function",
                    "Find the energy of each photon.",
                    [
                        ("WORK_FUNCTION_SUBTRACTED", "K-phi"),
                        ("ENERGIES_MULTIPLIED", "@K_r*phi_r"),
                        ("KINETIC_ENERGY_COPIED", "K"),
                    ],
                    laws=("K - Eph + phi",),
                ),
                var(
                    "V0",
                    "Eph phi",
                    "(Eph-phi)/e",
                    "e x V0 = K = photon energy - work function",
                    "Find the stopping potential.",
                    [
                        ("WORK_FUNCTION_IGNORED", "Eph/e"),
                        ("WORK_FUNCTION_ADDED", "(Eph+phi)/e"),
                        ("ENERGIES_MULTIPLIED", "@Eph_r*phi_r"),
                        ("CHARGE_ONLY", "@Eph_r-phi_r+1"),
                    ],
                    laws=("V0*e - Eph + phi",),
                ),
                var(
                    "Eph",
                    "V0 phi",
                    "e*V0+phi",
                    "e x V0 = K = photon energy - work function, so photon energy = e x V0 + work function",
                    "Find the energy of each photon.",
                    [
                        ("WORK_FUNCTION_IGNORED", "e*V0"),
                        ("WORK_FUNCTION_SUBTRACTED", "e*V0-phi"),
                        ("CHARGE_FORGOTTEN", "@V0_r+phi_r*2"),
                        ("ENERGIES_MULTIPLIED", "@V0_r*phi_r"),
                    ],
                    laws=("V0*e - Eph + phi",),
                ),
                var(
                    "Kj",
                    "f phi",
                    "h*f-phi",
                    "K = h x f - work function (all in joules)",
                    "Find the maximum kinetic energy of the electrons.",
                    [
                        ("WORK_FUNCTION_ADDED", "h*f+phi"),
                        ("PLANCK_FORGOTTEN", "f-phi"),
                        ("WORK_FUNCTION_IGNORED", "h*f"),
                        ("FREQUENCY_DIVIDED", "h/f-phi"),
                    ],
                    laws=("Kj - h*f + phi",),
                ),
                var(
                    "f",
                    "Kj phi",
                    "(Kj+phi)/h",
                    "K = h x f - work function, so f = (K + work function) / h",
                    "Find the frequency of the light.",
                    [
                        ("WORK_FUNCTION_SUBTRACTED", "(Kj-phi)/h"),
                        ("PLANCK_MULTIPLIED", "(Kj+phi)*h"),
                        ("WORK_FUNCTION_IGNORED", "Kj/h"),
                    ],
                    laws=("Kj - h*f + phi",),
                ),
            )
        },
    ),
    "Apply Einstein's photoelectric equation to find an energy, a stopping potential or a frequency",
    (P + "SCI_NOTATION", P + "REARRANGE_FORMULA", P + "UNIT_PREFIXES"),
)


def _debroglie(p):  # type: ignore[no-untyped-def]
    base = bases({"lam": ("lam", "nm"), "m": ("m", "kg")})(p)
    return base


DE_BROGLIE = reg(
    model(
        "DUAL.DE_BROGLIE",
        "DUAL",
        "de_broglie_wavelength",
        "the wave nature of a moving particle",
        syms={"lam": "m", "p": "kgm/s", "m": "kg", "v": "m/s", "h": "J*s"},
        labels={
            "lam": ("de Broglie wavelength", "the de Broglie wavelength is {v}"),
            "p": ("momentum", "the momentum of the particle is {v}"),
            "m": ("mass", "its mass is {v}"),
            "v": ("speed", "its speed is {v}"),
        },
        base=_debroglie,
        derived=lambda p: (("p", "h/lam"), ("v", "h/(lam*m)")),
        dunits={"p": "kgm/s", "v": "m/s"},
        consts={"h": "h_planck"},
        laws=("lam*p - h",),
        variants={
            v.id: v
            for v in (
                var(
                    "lam",
                    "p",
                    "h/p",
                    "wavelength = h / p",
                    "Find the de Broglie wavelength.",
                    [
                        ("MULTIPLIED_NOT_DIVIDED", "h*p"),
                        ("FORMULA_INVERTED", "p/h"),
                        ("PLANCK_FORGOTTEN", "1/p"),
                    ],
                    laws=("lam*p - h",),
                ),
                var(
                    "p",
                    "lam",
                    "h/lam",
                    "wavelength = h / p, so p = h / wavelength",
                    "Find the momentum of the particle.",
                    [
                        ("MULTIPLIED_NOT_DIVIDED", "h*lam"),
                        ("FORMULA_INVERTED", "lam/h"),
                        ("PLANCK_FORGOTTEN", "1/lam"),
                    ],
                    laws=("lam*p - h",),
                    rearr="multiply each side by p and divide each side by the wavelength",
                ),
                var(
                    "lam",
                    "m v",
                    "h/(m*v)",
                    "p = m x v, then wavelength = h / p",
                    "Find the de Broglie wavelength.",
                    [
                        ("MASS_FORGOTTEN", "h/v"),
                        ("SPEED_FORGOTTEN", "h/m"),
                        ("MOMENTUM_MULTIPLIED", "h*m*v"),
                        ("SPEED_SQUARED", "h/(m*v^2)"),
                    ],
                    laws=("lam*m*v - h",),
                ),
                var(
                    "v",
                    "m lam",
                    "h/(m*lam)",
                    "wavelength = h / (m x v), so v = h / (m x wavelength)",
                    "Find the speed of the particle.",
                    [
                        ("MASS_FORGOTTEN", "h/lam"),
                        ("MULTIPLIED_NOT_DIVIDED", "h*m*lam"),
                        ("WAVELENGTH_UNIT_SLIP", "h/(m*lam_r)"),
                    ],
                    laws=("lam*m*v - h",),
                ),
                var(
                    "m",
                    "lam v",
                    "h/(lam*v)",
                    "wavelength = h / (m x v), so m = h / (wavelength x v)",
                    "Find the mass of the particle.",
                    [
                        ("SPEED_FORGOTTEN", "h/lam"),
                        ("MULTIPLIED_NOT_DIVIDED", "h*lam*v"),
                        ("WAVELENGTH_UNIT_SLIP", "h/(lam_r*v)"),
                    ],
                    laws=("lam*m*v - h",),
                ),
            )
        },
    ),
    "Find a de Broglie wavelength, or the momentum, speed or mass behind it",
    (P + "SCI_NOTATION", P + "REARRANGE_FORMULA", "PHY.C12.DUAL.PHOTOELECTRIC"),
)

# ---------------------------------------------------------------- atoms
BOHR = reg(
    model(
        "ATOM.BOHR",
        "ATOM",
        "bohr_model_hydrogen",
        "the hydrogen atom in the Bohr model",
        syms={
            "En": "J",
            "dE": "J",
            "r": "m",
            "vn": "m/s",
            "kk": "per_m",
            "n": "unit",
            "ni": "unit",
            "nf": "unit",
            "E1": "J",
            "a0": "m",
            "v1": "m/s",
            "Ry": "per_m",
        },
        labels={
            "En": ("energy of the level", "the energy of the level is {v}"),
            "dE": ("photon energy", "the photon energy is {v}"),
            "r": ("orbit radius", "the orbit radius is {v}"),
            "vn": ("orbital speed", "the orbital speed is {v}"),
            "kk": ("wave number", "the wave number of the line is {v}"),
            "n": ("quantum number", "the principal quantum number is {v}"),
            "ni": ("starting level", "the electron falls from the level with n = {v}"),
            "nf": ("final level", "to the level with n = {v}"),
        },
        base=bases({"n": ("n", "unit"), "ni": ("ni", "unit"), "nf": ("nf", "unit")}),
        derived=lambda p: (
            ("En", "E1/n^2"),
            ("dE", "E1*(1/nf^2-1/ni^2)"),
            ("r", "a0*n^2"),
            ("vn", "v1/n"),
            ("kk", "Ry*(1/nf^2-1/ni^2)"),
        ),
        dunits={"En": "eV", "dE": "eV", "r": "pm", "vn": "m/s", "kk": "per_m"},
        consts={"E1": "E_hydrogen", "a0": "a0_bohr", "v1": "v_bohr", "Ry": "rydberg"},
        laws=("En*n**2 - E1",),
        variants={
            v.id: v
            for v in (
                var(
                    "En",
                    "n",
                    "E1/n^2",
                    "the magnitude of the energy is E1 divided by n squared",
                    "Find the magnitude of the energy of that level.",
                    [
                        ("QUANTUM_NUMBER_NOT_SQUARED", "E1/n"),
                        ("MULTIPLIED_NOT_DIVIDED", "E1*n^2"),
                        ("QUANTUM_NUMBER_CUBED", "E1/n^3"),
                        ("ENERGY_GROWS_WITH_N", "E1*n"),
                    ],
                    laws=("En*n**2 - E1",),
                ),
                var(
                    "dE",
                    "ni nf",
                    "E1*(1/nf^2-1/ni^2)",
                    "photon energy = 13.6 x (1/nf^2 - 1/ni^2) electron-volts",
                    "Find the energy of the photon given out.",
                    [
                        ("LEVELS_NOT_SQUARED", "E1*(1/nf-1/ni)"),
                        ("ENERGY_OF_FINAL_LEVEL_ONLY", "E1/nf^2"),
                        ("ENERGY_OF_START_LEVEL_ONLY", "E1/ni^2"),
                        ("SQUARES_ADDED", "E1*(1/nf^2+1/ni^2)"),
                    ],
                    laws=("dE - E1*(1/nf**2 - 1/ni**2)",),
                ),
                var(
                    "r",
                    "n",
                    "a0*n^2",
                    "the radius of the n-th orbit is a0 times n squared",
                    "Find the radius of that orbit.",
                    [
                        ("QUANTUM_NUMBER_NOT_SQUARED", "a0*n"),
                        ("DIVIDED_NOT_MULTIPLIED", "a0/n^2"),
                        ("QUANTUM_NUMBER_CUBED", "a0*n^3"),
                    ],
                    laws=("r - a0*n**2",),
                ),
                var(
                    "n",
                    "r",
                    "sqrt(r/a0)",
                    "the radius of the n-th orbit is a0 times n squared",
                    "Find the principal quantum number of the orbit.",
                    [
                        ("ROOT_FORGOTTEN", "r/a0"),
                        ("FORMULA_INVERTED", "sqrt(a0/r)"),
                        ("SQUARE_NOT_ROOT", "(r/a0)^2"),
                    ],
                    laws=("r - a0*n**2",),
                    rearr="divide each side by a0, then take the square root",
                ),
                var(
                    "vn",
                    "n",
                    "v1/n",
                    "the speed in the n-th orbit is v1 / n",
                    "Find the speed of the electron in that orbit.",
                    [
                        ("SPEED_INCREASES_WITH_N", "v1*n"),
                        ("QUANTUM_NUMBER_SQUARED", "v1/n^2"),
                        ("QUANTUM_NUMBER_SQUARED_UP", "v1*n^2"),
                    ],
                    laws=("vn*n - v1",),
                ),
                var(
                    "kk",
                    "ni nf",
                    "Ry*(1/nf^2-1/ni^2)",
                    "1 / wavelength = R x (1/nf^2 - 1/ni^2)",
                    "Find the wave number (1 / wavelength) of the line.",
                    [
                        ("LEVELS_NOT_SQUARED", "Ry*(1/nf-1/ni)"),
                        ("SQUARES_ADDED", "Ry*(1/nf^2+1/ni^2)"),
                        ("FINAL_LEVEL_ONLY", "Ry/nf^2"),
                        ("RATIO_INVERTED", "Ry/(1/nf^2-1/ni^2)"),
                    ],
                    laws=("kk - Ry*(1/nf**2 - 1/ni**2)",),
                ),
            )
        },
    ),
    "Use the Bohr model for energies, photon energies, orbit radii and speeds in hydrogen",
    (P + "RECIPROCALS", P + "SCI_NOTATION", "PHY.C12.DUAL.PHOTOELECTRIC"),
)

# ---------------------------------------------------------------- nuclei


def _decay(p):  # type: ignore[no-untyped-def]
    unit = str(p["tu"])
    n = to_si(p["n"], "unit")
    t_half = to_si(p["T"], unit)
    return (
        {"T": t_half, "n": n, "N0": to_si(p["N0"], "unit"), "t": n * t_half},
        {"T": unit, "n": "unit", "N0": "unit", "t": unit},
    )


DECAY = reg(
    model(
        "NUC.DECAY",
        "NUC",
        "radioactive_half_life",
        "a radioactive sample decaying by half-lives",
        syms={"N0": "unit", "N": "unit", "T": "s", "t": "s", "n": "unit", "x": "unit"},
        labels={
            "N0": ("starting number of nuclei", "the sample starts with {v} undecayed nuclei"),
            "N": ("remaining number of nuclei", "the number of undecayed nuclei left is {v}"),
            "T": ("half-life", "the half-life is {v}"),
            "t": ("time", "the time that passes is {v}"),
            "n": ("number of half-lives", "the number of half-lives that pass is {v}"),
        },
        base=_decay,
        derived=lambda p: (("N", "N0/2^n"),),
        dunits={"N": "unit"},
        laws=("N*2**n - N0",),
        variants={
            v.id: v
            for v in (
                var(
                    "N",
                    "N0 n",
                    "N0/2^n",
                    "after n half-lives the number left is N0 / 2^n",
                    "Find how many undecayed nuclei are left.",
                    [
                        ("HALVED_ONCE_ONLY", "N0/2"),
                        ("DIVIDED_BY_N", "N0/n"),
                        ("MULTIPLIED_BY_POWER", "N0*2^n"),
                        ("SUBTRACTED_N_HALVES", "N0-N0*n/2"),
                    ],
                    laws=("N*2**n - N0",),
                ),
                var(
                    "N",
                    "N0 t T",
                    "N0/2^(t/T)",
                    "the number of half-lives is t / T, then N = N0 / 2^(t/T)",
                    "Find how many undecayed nuclei are left.",
                    [
                        ("TIME_NOT_DIVIDED_BY_HALF_LIFE", "N0/2^t"),
                        ("HALVED_ONCE_ONLY", "N0/2"),
                        ("DIVIDED_BY_N", "N0*T/t"),
                        ("EXPONENT_INVERTED", "N0/2^(T/t)"),
                    ],
                    laws=("N*2**x - N0", "x*T - t"),
                ),
                var(
                    "N0",
                    "N n",
                    "N*2^n",
                    "after n half-lives the number left is N0 / 2^n",
                    "Find the starting number of nuclei.",
                    [
                        ("HALVED_NOT_DOUBLED", "N/2^n"),
                        ("DOUBLED_ONCE_ONLY", "N*2"),
                        ("MULTIPLIED_BY_N", "N*n"),
                    ],
                    laws=("N*2**n - N0",),
                ),
                var(
                    "T",
                    "t n",
                    "t/n",
                    "the number of half-lives is t / T",
                    "Find the half-life.",
                    [
                        ("MULTIPLIED_NOT_DIVIDED", "t*n"),
                        ("FORMULA_INVERTED", "n/t"),
                        ("POWER_OF_TWO_USED", "t/2^n"),
                    ],
                    laws=("n*T - t",),
                ),
                var(
                    "t",
                    "T n",
                    "n*T",
                    "the number of half-lives is t / T",
                    "Find the time that has passed.",
                    [
                        ("DIVIDED_NOT_MULTIPLIED", "T/n"),
                        ("POWER_OF_TWO_USED", "T*2^n"),
                        ("TIMES_ADDED", "T+n"),
                    ],
                    laws=("n*T - t",),
                ),
            )
        },
    ),
    "Use half-lives to find the number of nuclei left, the starting number, the half-life or the time",
    (P + "RATIO_PROPORTION", P + "POWERS_OF_TWO", P + "REARRANGE_FORMULA"),
)

BINDING = reg(
    model(
        "NUC.BINDING",
        "NUC",
        "mass_defect_energy",
        "the binding energy of a nucleus",
        syms={"dm": "kg", "E": "J", "A": "unit", "Ebn": "J", "ue": "J/kg"},
        labels={
            "dm": ("mass defect", "the mass defect is {v}"),
            "E": ("binding energy", "the binding energy is {v}"),
            "A": ("mass number", "the mass number is {v}"),
            "Ebn": ("binding energy per nucleon", "the binding energy per nucleon is {v}"),
        },
        base=bases({"dm": ("dm", "u"), "A": ("A", "unit")}),
        derived=lambda p: (("E", "dm*ue"), ("Ebn", "dm*ue/A")),
        dunits={"E": "MeV", "Ebn": "MeV"},
        consts={"ue": "u_energy"},
        laws=("E - dm*ue",),
        variants={
            v.id: v
            for v in (
                var(
                    "E",
                    "dm",
                    "dm*ue",
                    "binding energy = mass defect x energy of one atomic mass unit",
                    "Find the binding energy.",
                    [
                        ("DIVIDED_NOT_MULTIPLIED", "dm/ue"),
                        ("ENERGY_PER_UNIT_FORGOTTEN", "@dm_r"),
                        ("MASS_DEFECT_UNIT_SLIP", "dm*ue*1000"),
                        ("MASS_DEFECT_SQUARED", "dm*dm*ue"),
                    ],
                    laws=("E - dm*ue",),
                ),
                var(
                    "dm",
                    "E",
                    "E/ue",
                    "binding energy = mass defect x energy of one atomic mass unit",
                    "Find the mass defect.",
                    [
                        ("MULTIPLIED_NOT_DIVIDED", "E*ue"),
                        ("FORMULA_INVERTED", "ue/E"),
                        ("ENERGY_PER_UNIT_FORGOTTEN", "@E_r"),
                    ],
                    laws=("E - dm*ue",),
                    rearr="divide each side by the energy of one atomic mass unit",
                ),
                var(
                    "Ebn",
                    "dm A",
                    "dm*ue/A",
                    "binding energy per nucleon = mass defect x energy of one atomic mass unit / A",
                    "Find the binding energy per nucleon.",
                    [
                        ("TOTAL_ENERGY_GIVEN", "dm*ue"),
                        ("MASS_NUMBER_MULTIPLIED", "dm*ue*A"),
                        ("MASS_NUMBER_FORGOTTEN_AND_MASS_DEFECT_DIVIDED", "@dm_r/A"),
                        ("HALF_THE_NUCLEONS", "dm*ue/(A/2)"),
                    ],
                    laws=("Ebn*A - dm*ue",),
                ),
                var(
                    "A",
                    "E Ebn",
                    "E/Ebn",
                    "binding energy per nucleon = binding energy / A",
                    "Find the mass number.",
                    [
                        ("MULTIPLIED_NOT_DIVIDED", "E*Ebn"),
                        ("FORMULA_INVERTED", "Ebn/E"),
                        ("ENERGY_PER_NUCLEON_ONLY", "@Ebn_r"),
                    ],
                    laws=("Ebn*A - E",),
                ),
                var(
                    "E",
                    "Ebn A",
                    "Ebn*A",
                    "binding energy per nucleon = binding energy / A",
                    "Find the total binding energy.",
                    [
                        ("DIVIDED_NOT_MULTIPLIED", "Ebn/A"),
                        ("MASS_NUMBER_FORGOTTEN", "Ebn"),
                        ("MASS_NUMBER_ADDED", "Ebn+A"),
                    ],
                    laws=("Ebn*A - E",),
                ),
            )
        },
    ),
    "Find the binding energy, the mass defect or the binding energy per nucleon",
    (P + "REARRANGE_FORMULA", P + "UNIT_PREFIXES", "PHY.C12.NUC.DECAY"),
)

# ---------------------------------------------------------------- semiconductor electronics
GATES = reg(
    model(
        "SEMI.GATES",
        "SEMI",
        "logic_gate_truth_table",
        "the truth table of a logic gate",
        syms={"n": "unit", "R": "unit", "Ro": "unit", "Rx": "unit"},
        labels={
            "n": ("number of inputs", "the gate has {v} inputs"),
            "R": ("number of rows in the truth table", "the table has {v} rows"),
            "Ro": ("number of rows with output 1", "the table has {v} rows with output 1"),
            "Rx": ("number of rows with output 1", "the table has {v} rows with output 1"),
        },
        base=bases({"n": ("n", "unit")}),
        derived=lambda p: (("R", "2^n"), ("Ro", "2^n-1"), ("Rx", "2^(n-1)")),
        dunits={"R": "unit", "Ro": "unit", "Rx": "unit"},
        laws=("R - 2**n",),
        variants={
            v.id: v
            for v in (
                var(
                    "R",
                    "n",
                    "2^n",
                    "a truth table lists every combination of n inputs, so it has 2^n rows",
                    "How many rows does its truth table have?",
                    [
                        ("INPUTS_DOUBLED", "n*2"),
                        ("INPUTS_SQUARED", "n^2"),
                        ("TWO_ADDED", "n+2"),
                        ("POWER_OF_TWO_OFF_BY_ONE", "2^(n-1)"),
                    ],
                    laws=("R - 2**n",),
                ),
                var(
                    "Ro",
                    "n",
                    "2^n-1",
                    "an OR gate gives 0 only when every input is 0, so it gives 1 in 2^n - 1 of the 2^n rows",
                    "For an OR gate with this many inputs, in how many rows is the output 1?",
                    [
                        ("ALL_ROWS_COUNTED", "2^n"),
                        ("TWO_ROWS_LEFT_OUT", "2^n-2"),
                        ("INPUTS_DOUBLED_LESS_ONE", "n*2-1"),
                        ("XOR_RULE_USED", "2^(n-1)"),
                    ],
                    laws=("Ro - 2**n + 1",),
                ),
                var(
                    "Rx",
                    "n",
                    "2^(n-1)",
                    "an XOR gate gives 1 in exactly half of the rows",
                    "For an XOR gate with this many inputs, in how many rows is the output 1?",
                    [
                        ("ALL_ROWS_COUNTED", "2^n"),
                        ("OR_RULE_USED", "2^n-1"),
                        ("INPUTS_HALVED", "n/2"),
                        ("INPUTS_COPIED", "n"),
                    ],
                    laws=("Rx*2 - 2**n",),
                ),
            )
        },
    ),
    "Count the rows and the output-1 rows in the truth table of a gate",
    (P + "POWERS_OF_TWO", P + "COUNTING_RULES"),
)

TRANSISTOR = reg(
    model(
        "SEMI.TRANSISTOR",
        "SEMI",
        "transistor_current_gain",
        "a transistor in the common emitter connection",
        syms={
            "Ib": "A",
            "beta": "unit",
            "Ic": "A",
            "Ie": "A",
            "Rl": "ohm",
            "Rb": "ohm",
            "Av": "unit",
        },
        labels={
            "Ib": ("base current", "the base current is {v}"),
            "beta": ("current gain", "the current gain is {v}"),
            "Ic": ("collector current", "the collector current is {v}"),
            "Ie": ("emitter current", "the emitter current is {v}"),
            "Rl": ("load resistance", "the load resistance is {v}"),
            "Rb": ("input resistance", "the input resistance is {v}"),
            "Av": ("voltage gain", "the voltage gain is {v}"),
        },
        base=bases(
            {
                "Ib": ("Ib", "uA"),
                "beta": ("beta", "unit"),
                "Rl": ("Rl", "kohm"),
                "Rb": ("Rb", "kohm"),
            }
        ),
        derived=lambda p: (("Ic", "beta*Ib"), ("Ie", "Ib+beta*Ib"), ("Av", "beta*Rl/Rb")),
        dunits={"Ic": "mA", "Ie": "mA", "Av": "unit"},
        laws=("Ic - beta*Ib",),
        variants={
            v.id: v
            for v in (
                var(
                    "Ic",
                    "beta Ib",
                    "beta*Ib",
                    "collector current = beta x base current",
                    "Find the collector current.",
                    [
                        ("DIVIDED_NOT_MULTIPLIED", "Ib/beta"),
                        ("BASE_CURRENT_ADDED", "(beta+1)*Ib"),
                        ("CURRENT_UNIT_SLIP", "beta*Ib_r"),
                        ("GAIN_ONLY", "@beta_r"),
                    ],
                    laws=("Ic - beta*Ib",),
                ),
                var(
                    "Ie",
                    "Ib Ic",
                    "Ib+Ic",
                    "emitter current = base current + collector current",
                    "Find the emitter current.",
                    [
                        ("BASE_CURRENT_SUBTRACTED", "Ic-Ib"),
                        ("COLLECTOR_CURRENT_COPIED", "Ic"),
                        ("CURRENTS_MULTIPLIED", "@Ib_r*Ic_r/1000"),
                    ],
                    laws=("Ie - Ib - Ic",),
                ),
                var(
                    "beta",
                    "Ic Ib",
                    "Ic/Ib",
                    "beta = collector current / base current",
                    "Find the current gain.",
                    [
                        ("FORMULA_INVERTED", "Ib/Ic"),
                        ("EMITTER_CURRENT_USED", "(Ic+Ib)/Ib"),
                        ("CURRENT_UNIT_SLIP", "Ic/Ib_r"),
                    ],
                    laws=("beta*Ib - Ic",),
                ),
                var(
                    "Ib",
                    "Ic Ie",
                    "Ie-Ic",
                    "emitter current = base current + collector current",
                    "Find the base current.",
                    [
                        ("CURRENTS_ADDED", "Ie+Ic"),
                        ("EMITTER_CURRENT_COPIED", "Ie"),
                        ("GAIN_USED", "Ic/100"),
                    ],
                    laws=("Ie - Ib - Ic",),
                ),
                var(
                    "Av",
                    "beta Rl Rb",
                    "beta*Rl/Rb",
                    "voltage gain = beta x load resistance / input resistance",
                    "Find the voltage gain.",
                    [
                        ("RESISTANCES_SWAPPED", "beta*Rb/Rl"),
                        ("GAIN_FORGOTTEN", "Rl/Rb"),
                        ("RESISTANCES_MULTIPLIED", "beta*Rl*Rb/1000000"),
                        ("LOAD_ONLY", "beta*Rl/1000"),
                    ],
                    laws=("Av*Rb - beta*Rl",),
                ),
            )
        },
    ),
    "Find the collector, emitter or base current, the current gain or the voltage gain of a transistor",
    (P + "REARRANGE_FORMULA", P + "UNIT_PREFIXES", P + "RATIO_PROPORTION"),
)
