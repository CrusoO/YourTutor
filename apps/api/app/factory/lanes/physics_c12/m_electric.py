# ruff: noqa: E501
"""Class 12 models, part 1: electric charges and fields, potential and capacitance, current.

All wording is original. Closed forms are over SI values. A wrong procedure is a pair
(short misconception name, expression); see physics/model.py for the expression conventions
(SI names, `name_r` for the raw displayed number, K for the key in the answer unit, `@` prefix
for a value already in the answer unit).
"""

from __future__ import annotations

from fractions import Fraction

from app.factory.lanes.physics_c12.kit import P, bases, model, pairs, reg, var
from app.factory.lanes.physics_c12.quantities import to_si

# ---------------------------------------------------------------- electric charges and fields
_Q = ("1", "2", "3", "4", "5", "6", "9", "10")

COULOMB = reg(
    model(
        "EF.COULOMB",
        "EF",
        "coulomb_law",
        "the force between two point charges",
        syms={"F": "N", "q1": "C", "q2": "C", "r": "m", "k": "Nm2/C2"},
        labels={
            "F": ("force", "the force between them is {v}"),
            "q1": ("first charge", "the first charge is {v}"),
            "q2": ("second charge", "the second charge is {v}"),
            "r": ("separation", "the separation of the charges is {v}"),
        },
        base=bases({"q1": ("q1", "$qu"), "q2": ("q2", "$qu"), "r": ("r", "$ru")}),
        derived=lambda p: (("F", "k*q1*q2/r^2"),),
        dunits={"F": "N"},
        consts={"k": "k_coulomb"},
        laws=("F*r**2 - k*q1*q2",),
        variants={
            v.id: v
            for v in (
                var(
                    "F",
                    "q1 q2 r",
                    "k*q1*q2/r^2",
                    "F = k x q1 x q2 / r^2",
                    "Find the force between the charges.",
                    [
                        ("DISTANCE_NOT_SQUARED", "k*q1*q2/r"),
                        ("CHARGES_ADDED", "k*(q1+q2)/r^2"),
                        ("DISTANCE_UNIT_SLIP", "k*q1*q2/r_r^2"),
                        ("CONSTANT_FORGOTTEN", "q1*q2/r^2"),
                    ],
                ),
                var(
                    "r",
                    "F q1 q2",
                    "sqrt(k*q1*q2/F)",
                    "F = k x q1 x q2 / r^2",
                    "Find the distance between the charges.",
                    [
                        ("ROOT_FORGOTTEN", "k*q1*q2/F"),
                        ("FORMULA_INVERTED", "sqrt(F/(k*q1*q2))"),
                        ("CHARGES_ADDED", "sqrt(k*(q1+q2)/F)"),
                        ("SQUARE_NOT_ROOT", "(k*q1*q2/F)^2"),
                    ],
                    rearr="multiply each side by r^2 and divide each side by F, then take the square root",
                ),
                var(
                    "q2",
                    "F q1 r",
                    "F*r^2/(k*q1)",
                    "F = k x q1 x q2 / r^2",
                    "Find the second charge.",
                    [
                        ("DISTANCE_NOT_SQUARED", "F*r/(k*q1)"),
                        ("FORMULA_INVERTED", "k*q1/(F*r^2)"),
                        ("CHARGES_SUBTRACTED", "F*r^2/k-q1"),
                        ("DISTANCE_UNIT_SLIP", "F*r_r^2/(k*q1)"),
                    ],
                    rearr="multiply each side by r^2 and divide each side by k x q1",
                ),
            )
        },
    ),
    "Use Coulomb's law for the force, distance or a charge",
    (P + "SCI_NOTATION", P + "REARRANGE_FORMULA", P + "UNIT_PREFIXES"),
)

FIELD_POINT = reg(
    model(
        "EF.FIELD_POINT",
        "EF",
        "point_charge_field",
        "the electric field of a point charge",
        syms={"E": "N/C", "q": "C", "r": "m", "k": "Nm2/C2"},
        labels={
            "E": ("electric field", "the field is {v}"),
            "q": ("charge", "the charge is {v}"),
            "r": ("distance", "the distance from the charge is {v}"),
        },
        base=bases({"q": ("q", "$qu"), "r": ("r", "$ru")}),
        derived=lambda p: (("E", "k*q/r^2"),),
        dunits={"E": "N/C"},
        consts={"k": "k_coulomb"},
        laws=("E*r**2 - k*q",),
        variants={
            v.id: v
            for v in (
                var(
                    "E",
                    "q r",
                    "k*q/r^2",
                    "E = k x q / r^2",
                    "Find the magnitude of the electric field.",
                    [
                        ("DISTANCE_NOT_SQUARED", "k*q/r"),
                        ("FORMULA_INVERTED", "r^2/(k*q)"),
                        ("DISTANCE_UNIT_SLIP", "k*q/r_r^2"),
                        ("POTENTIAL_FORMULA_USED", "k*q/r"),
                    ],
                ),
                var(
                    "q",
                    "E r",
                    "E*r^2/k",
                    "E = k x q / r^2",
                    "Find the charge.",
                    [
                        ("DISTANCE_NOT_SQUARED", "E*r/k"),
                        ("FORMULA_INVERTED", "k/(E*r^2)"),
                        ("DISTANCE_UNIT_SLIP", "E*r_r^2/k"),
                    ],
                    rearr="multiply each side by r^2 and divide each side by k",
                ),
                var(
                    "r",
                    "E q",
                    "sqrt(k*q/E)",
                    "E = k x q / r^2",
                    "Find the distance from the charge.",
                    [
                        ("ROOT_FORGOTTEN", "k*q/E"),
                        ("FORMULA_INVERTED", "sqrt(E/(k*q))"),
                        ("SQUARE_NOT_ROOT", "(k*q/E)^2"),
                    ],
                    rearr="multiply each side by r^2, divide each side by E, then take the square root",
                ),
            )
        },
    ),
    "Find the electric field of a point charge, or the charge or distance behind it",
    (P + "SCI_NOTATION", P + "REARRANGE_FORMULA", "PHY.C12.EF.COULOMB"),
)

DIPOLE = reg(
    model(
        "EF.DIPOLE",
        "EF",
        "dipole_moment_torque",
        "an electric dipole in a uniform field",
        syms={"p": "Cm", "q": "C", "d": "m", "E": "N/C", "tau": "Nm", "s": "unit"},
        labels={
            "p": ("dipole moment", "the dipole moment is {v}"),
            "q": ("charge of each end", "the charge on each end is {v}"),
            "d": ("separation", "the two charges are {v} apart"),
            "E": ("field", "the uniform field is {v}"),
            "tau": ("torque", "the torque on the dipole is {v}"),
            "s": (
                "sine of the angle",
                "the sine of the angle between the dipole and the field is {v}",
            ),
        },
        base=bases({"q": ("q", "$qu"), "d": ("d", "cm"), "E": ("E", "N/C"), "s": ("s", "unit")}),
        derived=lambda p: (("p", "q*d"), ("tau", "p*E*s")),
        dunits={"p": "Cm", "tau": "Nm"},
        laws=("p - q*d",),
        variants={
            v.id: v
            for v in (
                var(
                    "p",
                    "q d",
                    "q*d",
                    "p = q x d, charge times separation",
                    "Find the dipole moment.",
                    [
                        ("DIVIDED_NOT_MULTIPLIED", "q/d"),
                        ("HALF_SEPARATION_USED", "q*d/2"),
                        ("DOUBLE_SEPARATION_USED", "2*q*d"),
                        ("DISTANCE_UNIT_SLIP", "q*d_r"),
                    ],
                    laws=("p - q*d",),
                ),
                var(
                    "tau",
                    "p E s",
                    "p*E*s",
                    "torque = p x E x sine of the angle",
                    "Find the torque on the dipole.",
                    [
                        ("SINE_FORGOTTEN", "p*E"),
                        ("SINE_DIVIDED", "p*E/s"),
                        ("FIELD_DIVIDED", "p*s/E"),
                    ],
                    laws=("tau - p*E*s",),
                ),
                var(
                    "E",
                    "tau p s",
                    "tau/(p*s)",
                    "torque = p x E x sine of the angle",
                    "Find the strength of the field.",
                    [
                        ("SINE_FORGOTTEN", "tau/p"),
                        ("MULTIPLIED_NOT_DIVIDED", "tau*p*s"),
                        ("FORMULA_INVERTED", "p*s/tau"),
                    ],
                    laws=("tau - p*E*s",),
                    rearr="divide each side of torque = p x E x sine of the angle by p x sine of the angle",
                ),
                var(
                    "p",
                    "tau E s",
                    "tau/(E*s)",
                    "torque = p x E x sine of the angle",
                    "Find the dipole moment.",
                    [
                        ("SINE_FORGOTTEN", "tau/E"),
                        ("MULTIPLIED_NOT_DIVIDED", "tau*E*s"),
                        ("FORMULA_INVERTED", "E*s/tau"),
                    ],
                    laws=("tau - p*E*s",),
                    rearr="divide each side of torque = p x E x sine of the angle by E x sine of the angle",
                ),
            )
        },
    ),
    "Find a dipole moment, or the torque on a dipole in a uniform field",
    (P + "REARRANGE_FORMULA", P + "SCI_NOTATION", "PHY.C12.EF.FIELD_POINT"),
)

# ---------------------------------------------------------------- potential and capacitance
POT_POINT = reg(
    model(
        "CAP.POT_POINT",
        "CAP",
        "point_charge_potential",
        "the electric potential of a point charge",
        syms={"V": "V", "q": "C", "r": "m", "k": "Nm2/C2"},
        labels={
            "V": ("potential", "the potential is {v}"),
            "q": ("charge", "the charge is {v}"),
            "r": ("distance", "the distance from the charge is {v}"),
        },
        base=bases({"q": ("q", "$qu"), "r": ("r", "$ru")}),
        derived=lambda p: (("V", "k*q/r"),),
        dunits={"V": "V"},
        consts={"k": "k_coulomb"},
        laws=("V*r - k*q",),
        variants={
            v.id: v
            for v in (
                var(
                    "V",
                    "q r",
                    "k*q/r",
                    "V = k x q / r",
                    "Find the potential at that point.",
                    [
                        ("DISTANCE_SQUARED", "k*q/r^2"),
                        ("DISTANCE_UNIT_SLIP", "k*q/r_r"),
                        ("FORMULA_INVERTED", "r/(k*q)"),
                    ],
                ),
                var(
                    "q",
                    "V r",
                    "V*r/k",
                    "V = k x q / r",
                    "Find the charge.",
                    [
                        ("DISTANCE_SQUARED", "V*r^2/k"),
                        ("FORMULA_INVERTED", "k/(V*r)"),
                        ("DISTANCE_UNIT_SLIP", "V*r_r/k"),
                    ],
                    rearr="multiply each side by r and divide each side by k",
                ),
                var(
                    "r",
                    "V q",
                    "k*q/V",
                    "V = k x q / r",
                    "Find the distance from the charge.",
                    [
                        ("SQUARE_ROOT_TAKEN", "sqrt(k*q/V)"),
                        ("FORMULA_INVERTED", "V/(k*q)"),
                        ("MULTIPLIED_NOT_DIVIDED", "k*q*V"),
                    ],
                    rearr="multiply each side by r and divide each side by V",
                ),
            )
        },
    ),
    "Find the potential of a point charge, or the charge or distance behind it",
    (P + "SCI_NOTATION", P + "REARRANGE_FORMULA", "PHY.C12.EF.FIELD_POINT"),
)

CAP_PLATE = reg(
    model(
        "CAP.CAP_PLATE",
        "CAP",
        "parallel_plate_capacitor",
        "a parallel plate capacitor",
        syms={"C": "F", "K": "unit", "A": "m^2", "d": "m", "eps0": "C^2/N/m^2"},
        labels={
            "C": ("capacitance", "the capacitance is {v}"),
            "K": (
                "dielectric constant",
                "the dielectric constant of the material between the plates is {v}",
            ),
            "A": ("plate area", "the area of each plate is {v}"),
            "d": ("plate gap", "the gap between the plates is {v}"),
        },
        base=bases({"K": ("K", "unit"), "A": ("A", "cm^2"), "d": ("d", "mm")}),
        derived=lambda p: (("C", "K*eps0*A/d"),),
        dunits={"C": "pF"},
        consts={"eps0": "eps0"},
        laws=("C*d - K*eps0*A",),
        variants={
            v.id: v
            for v in (
                var(
                    "C",
                    "K A d",
                    "K*eps0*A/d",
                    "C = K x eps0 x A / d",
                    "Find the capacitance.",
                    [
                        ("GAP_NOT_INVERTED", "K*eps0*A*d"),
                        ("DIELECTRIC_FORGOTTEN", "eps0*A/d"),
                        ("AREA_UNIT_SLIP", "K*eps0*A_r/d"),
                        ("GAP_UNIT_SLIP", "K*eps0*A/d_r"),
                    ],
                ),
                var(
                    "d",
                    "C K A",
                    "K*eps0*A/C",
                    "C = K x eps0 x A / d",
                    "Find the gap between the plates.",
                    [
                        ("FORMULA_INVERTED", "C/(K*eps0*A)"),
                        ("DIELECTRIC_FORGOTTEN", "eps0*A/C"),
                        ("AREA_UNIT_SLIP", "K*eps0*A_r/C"),
                    ],
                    rearr="multiply each side by d and divide each side by C",
                ),
                var(
                    "A",
                    "C K d",
                    "C*d/(K*eps0)",
                    "C = K x eps0 x A / d",
                    "Find the area of each plate.",
                    [
                        ("DIELECTRIC_FORGOTTEN", "C*d/eps0"),
                        ("FORMULA_INVERTED", "K*eps0/(C*d)"),
                        ("GAP_UNIT_SLIP", "C*d_r/(K*eps0)"),
                    ],
                    rearr="multiply each side by d and divide each side by K x eps0",
                ),
                var(
                    "K",
                    "C A d",
                    "C*d/(eps0*A)",
                    "C = K x eps0 x A / d",
                    "Find the dielectric constant of the material.",
                    [
                        ("FORMULA_INVERTED", "eps0*A/(C*d)"),
                        ("GAP_NOT_INVERTED", "C/(eps0*A*d)"),
                        ("AREA_UNIT_SLIP", "C*d/(eps0*A_r)"),
                    ],
                    rearr="multiply each side by d and divide each side by eps0 x A",
                ),
            )
        },
    ),
    "Find the capacitance of a parallel plate capacitor, or the area, gap or dielectric constant",
    (P + "SCI_NOTATION", P + "REARRANGE_FORMULA", P + "UNIT_PREFIXES"),
)

CAP_COMBINE = reg(
    model(
        "CAP.CAP_COMBINE",
        "CAP",
        "capacitor_combination",
        "two capacitors joined together",
        syms={"C1": "F", "C2": "F", "Cs": "F", "Cp": "F"},
        labels={
            "C1": ("first capacitance", "the first capacitor is {v}"),
            "C2": ("second capacitance", "the second capacitor is {v}"),
            "Cs": ("series capacitance", "the series combination is {v}"),
            "Cp": ("parallel capacitance", "the parallel combination is {v}"),
        },
        base=pairs(("C1", "C2"), "cset", "uF", "uF"),
        derived=lambda p: (("Cs", "C1*C2/(C1+C2)"), ("Cp", "C1+C2")),
        dunits={"Cs": "uF", "Cp": "uF"},
        laws=("Cs*(C1+C2) - C1*C2",),
        variants={
            v.id: v
            for v in (
                var(
                    "Cs",
                    "C1 C2",
                    "C1*C2/(C1+C2)",
                    "series: 1/C = 1/C1 + 1/C2, so C = C1 x C2 / (C1 + C2)",
                    "Find the capacitance of the series combination.",
                    [
                        ("PARALLEL_RULE_USED", "C1+C2"),
                        ("FORGOT_FINAL_RECIPROCAL", "@1/C1_r+1/C2_r"),
                        ("CAPACITANCES_AVERAGED", "(C1+C2)/2"),
                        ("CAPACITANCES_MULTIPLIED", "@C1_r*C2_r"),
                    ],
                ),
                var(
                    "Cp",
                    "C1 C2",
                    "C1+C2",
                    "parallel: C = C1 + C2",
                    "Find the capacitance of the parallel combination.",
                    [
                        ("SERIES_RULE_USED", "C1*C2/(C1+C2)"),
                        ("CAPACITANCES_AVERAGED", "(C1+C2)/2"),
                        ("CAPACITANCES_MULTIPLIED", "@C1_r*C2_r"),
                        ("FORGOT_FINAL_RECIPROCAL", "@1/C1_r+1/C2_r"),
                    ],
                    laws=("Cp - C1 - C2",),
                ),
                var(
                    "C2",
                    "Cs C1",
                    "Cs*C1/(C1-Cs)",
                    "series: 1/Cs = 1/C1 + 1/C2",
                    "Find the second capacitance.",
                    [
                        ("FORMULA_INVERTED", "Cs*C1/(C1+Cs)"),
                        ("CAPACITANCES_SUBTRACTED", "C1-Cs"),
                        ("CAPACITANCES_MULTIPLIED", "@Cs_r*C1_r"),
                        ("PARALLEL_RULE_USED", "Cs+C1"),
                    ],
                    rearr="write 1/C2 = 1/Cs - 1/C1 and combine the fractions",
                ),
                var(
                    "C2",
                    "Cp C1",
                    "Cp-C1",
                    "parallel: Cp = C1 + C2",
                    "Find the second capacitance.",
                    [
                        ("PARALLEL_RULE_USED", "Cp+C1"),
                        ("SERIES_RULE_USED", "Cp*C1/(Cp+C1)"),
                        ("CAPACITANCES_AVERAGED", "(Cp+C1)/2"),
                        ("CAPACITANCES_DIVIDED", "@Cp_r/C1_r"),
                    ],
                    laws=("Cp - C1 - C2",),
                    rearr="subtract C1 from each side",
                ),
            )
        },
    ),
    "Combine two capacitors in series or in parallel",
    (P + "RECIPROCALS", P + "REARRANGE_FORMULA", "PHY.C12.CAP.CAP_PLATE"),
)

CAP_ENERGY = reg(
    model(
        "CAP.CAP_ENERGY",
        "CAP",
        "capacitor_charge_energy",
        "a charged capacitor",
        syms={"C": "F", "V": "V", "Q": "C", "U": "J"},
        labels={
            "C": ("capacitance", "the capacitance is {v}"),
            "V": ("potential difference", "the potential difference across it is {v}"),
            "Q": ("charge", "the charge stored is {v}"),
            "U": ("stored energy", "the energy stored is {v}"),
        },
        base=bases({"C": ("C", "uF"), "V": ("V", "V")}),
        derived=lambda p: (("Q", "C*V"), ("U", "C*V^2/2")),
        dunits={"Q": "uC", "U": "uJ"},
        laws=("Q - C*V",),
        variants={
            v.id: v
            for v in (
                var(
                    "Q",
                    "C V",
                    "C*V",
                    "Q = C x V",
                    "Find the charge on the capacitor.",
                    [
                        ("DIVIDED_NOT_MULTIPLIED", "C/V"),
                        ("ENERGY_FORMULA_USED", "C*V^2/2"),
                        ("VOLTAGE_SQUARED", "C*V^2"),
                    ],
                    laws=("Q - C*V",),
                ),
                var(
                    "U",
                    "C V",
                    "C*V^2/2",
                    "U = (1/2) x C x V^2",
                    "Find the energy stored.",
                    [
                        ("HALF_FORGOTTEN", "C*V^2"),
                        ("VOLTAGE_NOT_SQUARED", "C*V/2"),
                        ("CHARGE_FORMULA_USED", "C*V"),
                        ("SQUARED_AFTER_HALVING", "(C*V/2)^2"),
                    ],
                    laws=("U*2 - C*V**2",),
                ),
                var(
                    "U",
                    "Q V",
                    "Q*V/2",
                    "U = (1/2) x Q x V",
                    "Find the energy stored.",
                    [
                        ("HALF_FORGOTTEN", "Q*V"),
                        ("DIVIDED_NOT_MULTIPLIED", "Q/V/2"),
                        ("CHARGE_SQUARED", "Q^2/2"),
                    ],
                    laws=("U*2 - Q*V",),
                ),
                var(
                    "U",
                    "Q C",
                    "Q^2/(2*C)",
                    "U = Q^2 / (2 x C)",
                    "Find the energy stored.",
                    [
                        ("CHARGE_NOT_SQUARED", "Q/(2*C)"),
                        ("HALF_FORGOTTEN", "Q^2/C"),
                        ("CAPACITANCE_MULTIPLIED", "Q^2*C/2"),
                    ],
                    laws=("U*2*C - Q**2",),
                ),
                var(
                    "V",
                    "U C",
                    "sqrt(2*U/C)",
                    "U = (1/2) x C x V^2",
                    "Find the potential difference.",
                    [
                        ("ROOT_FORGOTTEN", "2*U/C"),
                        ("HALF_FORGOTTEN", "sqrt(U/C)"),
                        ("FORMULA_INVERTED", "sqrt(C/(2*U))"),
                    ],
                    laws=("U*2 - C*V**2",),
                    rearr="multiply each side by 2, divide each side by C, then take the square root",
                ),
                var(
                    "C",
                    "Q V",
                    "Q/V",
                    "Q = C x V",
                    "Find the capacitance.",
                    [
                        ("MULTIPLIED_NOT_DIVIDED", "Q*V"),
                        ("FORMULA_INVERTED", "V/Q"),
                        ("ENERGY_FORMULA_USED", "2*Q/V^2"),
                    ],
                    laws=("Q - C*V",),
                    rearr="divide each side of Q = C x V by V",
                ),
            )
        },
    ),
    "Find the charge, energy, potential difference or capacitance of a charged capacitor",
    (P + "REARRANGE_FORMULA", P + "UNIT_PREFIXES", "PHY.C12.CAP.CAP_PLATE"),
)

# ---------------------------------------------------------------- current electricity
DRIFT = reg(
    model(
        "CUR.DRIFT",
        "CUR",
        "drift_current",
        "current carried by free electrons in a wire",
        syms={"I": "A", "n": "per_m3", "e": "C", "A": "m^2", "vd": "m/s"},
        labels={
            "I": ("current", "the current is {v}"),
            "n": ("electron density", "the free electron density is {v}"),
            "A": ("cross section", "the cross-sectional area is {v}"),
            "vd": ("drift speed", "the drift speed is {v}"),
        },
        base=bases({"n": ("n", "per_m3"), "A": ("A", "mm^2"), "vd": ("vd", "mm/s")}),
        derived=lambda p: (("I", "n*e*A*vd"),),
        dunits={"I": "A"},
        consts={"e": "e_charge"},
        laws=("I - n*e*A*vd",),
        variants={
            v.id: v
            for v in (
                var(
                    "I",
                    "n A vd",
                    "n*e*A*vd",
                    "I = n x e x A x v_d",
                    "Find the current in the wire.",
                    [
                        ("CHARGE_FORGOTTEN", "n*A*vd"),
                        ("AREA_UNIT_SLIP", "n*e*A_r*vd"),
                        ("SPEED_UNIT_SLIP", "n*e*A*vd_r"),
                        ("DIVIDED_NOT_MULTIPLIED", "n*e*A/vd"),
                    ],
                ),
                var(
                    "vd",
                    "I n A",
                    "I/(n*e*A)",
                    "I = n x e x A x v_d",
                    "Find the drift speed of the electrons.",
                    [
                        ("MULTIPLIED_NOT_DIVIDED", "I*n*e*A"),
                        ("CHARGE_FORGOTTEN", "I/(n*A)"),
                        ("AREA_UNIT_SLIP", "I/(n*e*A_r)"),
                    ],
                    rearr="divide each side by n x e x A",
                ),
                var(
                    "n",
                    "I A vd",
                    "I/(e*A*vd)",
                    "I = n x e x A x v_d",
                    "Find the number of free electrons in each cubic metre.",
                    [
                        ("CHARGE_FORGOTTEN", "I/(A*vd)"),
                        ("MULTIPLIED_NOT_DIVIDED", "I*e*A*vd"),
                        ("SPEED_UNIT_SLIP", "I/(e*A*vd_r)"),
                    ],
                    rearr="divide each side by e x A x v_d",
                ),
                var(
                    "A",
                    "I n vd",
                    "I/(n*e*vd)",
                    "I = n x e x A x v_d",
                    "Find the cross-sectional area of the wire.",
                    [
                        ("CHARGE_FORGOTTEN", "I/(n*vd)"),
                        ("MULTIPLIED_NOT_DIVIDED", "I*n*e*vd"),
                        ("SPEED_UNIT_SLIP", "I/(n*e*vd_r)"),
                    ],
                    rearr="divide each side by n x e x v_d",
                ),
            )
        },
        sizes={
            "vd": (Fraction(1, 10**6), Fraction(1, 10)),
            "A": (Fraction(1, 10**7), Fraction(1, 10**4)),
        },
    ),
    "Relate current to the drift speed of free electrons",
    (P + "SCI_NOTATION", P + "REARRANGE_FORMULA", P + "UNIT_PREFIXES"),
)

CELL_INTERNAL = reg(
    model(
        "CUR.CELL_INTERNAL",
        "CUR",
        "emf_terminal_voltage",
        "a cell with internal resistance driving a resistor",
        syms={"E": "V", "r": "ohm", "R": "ohm", "I": "A", "Vt": "V"},
        labels={
            "E": ("emf", "the emf of the cell is {v}"),
            "r": ("internal resistance", "its internal resistance is {v}"),
            "R": ("external resistance", "the external resistor is {v}"),
            "I": ("current", "the current is {v}"),
            "Vt": ("terminal voltage", "the terminal voltage is {v}"),
        },
        base=bases({"E": ("E", "V"), "r": ("r", "ohm"), "R": ("R", "ohm")}),
        derived=lambda p: (("I", "E/(R+r)"), ("Vt", "E*R/(R+r)")),
        dunits={"I": "A", "Vt": "V"},
        laws=("E - I*(R+r)",),
        variants={
            v.id: v
            for v in (
                var(
                    "I",
                    "E R r",
                    "E/(R+r)",
                    "E = I x (R + r)",
                    "Find the current in the circuit.",
                    [
                        ("INTERNAL_RESISTANCE_IGNORED", "E/R"),
                        ("EXTERNAL_RESISTANCE_IGNORED", "E/r"),
                        ("RESISTANCES_SUBTRACTED", "E/(R-r)"),
                        ("MULTIPLIED_NOT_DIVIDED", "E*(R+r)"),
                    ],
                    rearr="divide each side of E = I x (R + r) by (R + r)",
                ),
                var(
                    "Vt",
                    "E R r",
                    "E*R/(R+r)",
                    "I = E / (R + r), and the terminal voltage is V = I x R",
                    "Find the terminal voltage of the cell.",
                    [
                        ("EMF_TAKEN_AS_TERMINAL", "E"),
                        ("INTERNAL_RESISTANCE_IGNORED", "E*R/R"),
                        ("DROP_ADDED", "E+E*r/(R+r)"),
                        ("FORMULA_INVERTED", "E*(R+r)/R"),
                    ],
                    laws=("E - I*(R+r)", "Vt - I*R"),
                ),
                var(
                    "r",
                    "E I R",
                    "E/I-R",
                    "E = I x (R + r)",
                    "Find the internal resistance of the cell.",
                    [
                        ("EXTERNAL_RESISTANCE_IGNORED", "E/I"),
                        ("RESISTANCES_ADDED", "E/I+R"),
                        ("MULTIPLIED_NOT_DIVIDED", "E*I-R"),
                        ("FORMULA_INVERTED", "I/E-R"),
                    ],
                    rearr="divide each side of E = I x (R + r) by I, then subtract R",
                ),
                var(
                    "E",
                    "I R r",
                    "I*(R+r)",
                    "E = I x (R + r)",
                    "Find the emf of the cell.",
                    [
                        ("INTERNAL_RESISTANCE_IGNORED", "I*R"),
                        ("EXTERNAL_RESISTANCE_IGNORED", "I*r"),
                        ("DIVIDED_NOT_MULTIPLIED", "I/(R+r)"),
                        ("RESISTANCES_SUBTRACTED", "I*(R-r)"),
                    ],
                ),
                var(
                    "Vt",
                    "E I r",
                    "E-I*r",
                    "terminal voltage V = E - I x r",
                    "Find the terminal voltage of the cell.",
                    [
                        ("DROP_ADDED", "E+I*r"),
                        ("EMF_TAKEN_AS_TERMINAL", "E"),
                        ("DROP_FORGOTTEN_RESISTANCE", "E-I"),
                        ("DIVIDED_NOT_MULTIPLIED", "E-I/r"),
                    ],
                    laws=("Vt - E + I*r",),
                ),
            )
        },
    ),
    "Find the current, terminal voltage, emf or internal resistance of a cell",
    (P + "REARRANGE_FORMULA", P + "SERIES_RESISTORS", "PHY.C12.CUR.DRIFT"),
)


def _bridge_base(p):  # type: ignore[no-untyped-def]
    l1 = Fraction(str(p["l1"]))
    return (
        {"R": to_si(p["R"], "ohm"), "l1": to_si(l1, "cm"), "l2": to_si(100 - l1, "cm")},
        {"R": "ohm", "l1": "cm", "l2": "cm"},
    )


METRE_BRIDGE = reg(
    model(
        "CUR.METRE_BRIDGE",
        "CUR",
        "wheatstone_balance",
        "a metre bridge at balance",
        syms={"R": "ohm", "S": "ohm", "l1": "m", "l2": "m"},
        labels={
            "R": ("known resistance", "the known resistance in the left gap is {v}"),
            "S": ("unknown resistance", "the unknown resistance in the right gap is {v}"),
            "l1": ("left length", "the balance point is {v} from the left end"),
            "l2": ("right length", "the remaining wire on the right is {v}"),
        },
        base=_bridge_base,
        derived=lambda p: (("S", "R*l2/l1"),),
        dunits={"S": "ohm"},
        laws=("S*l1 - R*l2",),
        variants={
            v.id: v
            for v in (
                var(
                    "S",
                    "R l1 l2",
                    "R*l2/l1",
                    "R / S = l1 / l2",
                    "Find the unknown resistance.",
                    [
                        ("RATIO_INVERTED", "R*l1/l2"),
                        ("LENGTH_NOT_DIVIDED", "R*l2"),
                        ("TOTAL_LENGTH_USED", "R*(l1+l2)/l1"),
                        ("LENGTHS_ADDED", "R+l2-l1"),
                    ],
                    rearr="multiply each side of R / S = l1 / l2 by S, then rearrange for S",
                ),
                var(
                    "R",
                    "S l1 l2",
                    "S*l1/l2",
                    "R / S = l1 / l2",
                    "Find the known resistance.",
                    [
                        ("RATIO_INVERTED", "S*l2/l1"),
                        ("LENGTH_NOT_DIVIDED", "S*l1"),
                        ("TOTAL_LENGTH_USED", "S*(l1+l2)/l2"),
                    ],
                ),
                var(
                    "l2",
                    "R S l1",
                    "l1*S/R",
                    "R / S = l1 / l2",
                    "Find the length of wire on the right of the balance point.",
                    [
                        ("RATIO_INVERTED", "l1*R/S"),
                        ("LENGTH_NOT_DIVIDED", "l1*S*R"),
                        ("LEFT_LENGTH_COPIED", "l1"),
                        ("LENGTHS_ADDED", "l1+S-R"),
                    ],
                    laws=("S*l1 - R*l2",),
                ),
            )
        },
    ),
    "Use the balance condition of a metre bridge",
    (P + "RATIO_PROPORTION", P + "REARRANGE_FORMULA", "PHY.C12.CUR.CELL_INTERNAL"),
)
