# ruff: noqa: E501
"""Class 12 models, part 2: magnetism, induction, alternating current, electromagnetic waves.

All wording is original. See m_electric.py for the expression conventions.
"""

from __future__ import annotations

from app.factory.lanes.physics_c12.kit import P, bases, model, pairs, reg, var

# ---------------------------------------------------------------- moving charges and magnetism


def _particle(p):  # type: ignore[no-untyped-def]
    """Mass and charge of a fictitious particle come as one 'mass,charge' text parameter."""
    from app.factory.lanes.physics_c12.quantities import to_si

    m, q = str(p["pt"]).split(",")
    base = bases({"v": ("v", "m/s"), "B": ("B", "mT"), "s": ("s", "unit")})(p)
    base[0].update({"m": to_si(m, "kg"), "q": to_si(q, "C")})
    base[1].update({"m": "kg", "q": "C"})
    return base


LORENTZ = reg(
    model(
        "MAG.LORENTZ",
        "MAG",
        "magnetic_force_on_charge",
        "a charged particle moving in a magnetic field",
        syms={"F": "N", "q": "C", "v": "m/s", "B": "T", "s": "unit", "m": "kg", "r": "m"},
        labels={
            "F": ("force", "the magnetic force is {v}"),
            "q": ("charge", "the charge of the particle is {v}"),
            "v": ("speed", "its speed is {v}"),
            "B": ("field", "the magnetic field is {v}"),
            "s": (
                "sine of the angle",
                "the sine of the angle between the velocity and the field is {v}",
            ),
            "m": ("mass", "its mass is {v}"),
            "r": ("radius", "the radius of its circular path is {v}"),
        },
        base=_particle,
        derived=lambda p: (("F", "q*v*B*s"), ("r", "m*v/(q*B)")),
        dunits={"F": "N", "r": "cm"},
        laws=("F - q*v*B*s",),
        variants={
            v.id: v
            for v in (
                var(
                    "F",
                    "q v B s",
                    "q*v*B*s",
                    "F = q x v x B x sine of the angle",
                    "Find the magnitude of the magnetic force.",
                    [
                        ("SINE_FORGOTTEN", "q*v*B"),
                        ("FIELD_DIVIDED", "q*v*s/B"),
                        ("SPEED_FORGOTTEN", "q*B*s"),
                        ("FIELD_UNIT_SLIP", "q*v*B_r*s"),
                    ],
                ),
                var(
                    "B",
                    "F q v s",
                    "F/(q*v*s)",
                    "F = q x v x B x sine of the angle",
                    "Find the strength of the magnetic field.",
                    [
                        ("SINE_FORGOTTEN", "F/(q*v)"),
                        ("MULTIPLIED_NOT_DIVIDED", "F*q*v*s"),
                        ("FORMULA_INVERTED", "q*v*s/F"),
                    ],
                    rearr="divide each side by q x v x sine of the angle",
                ),
                var(
                    "v",
                    "F q B s",
                    "F/(q*B*s)",
                    "F = q x v x B x sine of the angle",
                    "Find the speed of the particle.",
                    [
                        ("SINE_FORGOTTEN", "F/(q*B)"),
                        ("MULTIPLIED_NOT_DIVIDED", "F*q*B*s"),
                        ("FORMULA_INVERTED", "q*B*s/F"),
                    ],
                    rearr="divide each side by q x B x sine of the angle",
                ),
                var(
                    "r",
                    "m v q B",
                    "m*v/(q*B)",
                    "the magnetic force gives the centripetal force: q x v x B = m x v^2 / r, so r = m x v / (q x B)",
                    "Find the radius of the circular path.",
                    [
                        ("FIELD_FORGOTTEN", "m*v/q"),
                        ("FORMULA_INVERTED", "q*B/(m*v)"),
                        ("SPEED_SQUARED", "m*v^2/(q*B)"),
                        ("MASS_FORGOTTEN", "v/(q*B)"),
                    ],
                    laws=("r*q*B - m*v",),
                ),
                var(
                    "v",
                    "m r q B",
                    "q*B*r/m",
                    "q x v x B = m x v^2 / r, so v = q x B x r / m",
                    "Find the speed of the particle.",
                    [
                        ("FORMULA_INVERTED", "m/(q*B*r)"),
                        ("MASS_MULTIPLIED", "q*B*r*m"),
                        ("RADIUS_FORGOTTEN", "q*B/m"),
                    ],
                    laws=("r*q*B - m*v",),
                ),
                var(
                    "B",
                    "m v q r",
                    "m*v/(q*r)",
                    "q x v x B = m x v^2 / r, so B = m x v / (q x r)",
                    "Find the strength of the magnetic field.",
                    [
                        ("RADIUS_MULTIPLIED", "m*v*r/q"),
                        ("FORMULA_INVERTED", "q*r/(m*v)"),
                        ("SPEED_SQUARED", "m*v^2/(q*r)"),
                    ],
                    laws=("r*q*B - m*v",),
                ),
            )
        },
        sizes={},
    ),
    "Find the force on a moving charge, or the radius of its circular path",
    (P + "REARRANGE_FORMULA", P + "SCI_NOTATION", "PHY.C12.EF.FIELD_POINT"),
)

B_FIELD = reg(
    model(
        "MAG.B_FIELD",
        "MAG",
        "field_of_a_current",
        "the magnetic field of a current",
        syms={
            "Bw": "T",
            "Bl": "T",
            "Bs": "T",
            "I": "A",
            "I2": "A",
            "r": "m",
            "N": "unit",
            "n": "per_m",
            "f": "N/m",
            "mu0": "N/A^2",
            "mu0_4pi": "N/A^2",
        },
        labels={
            "Bw": ("field of the wire", "the field of the wire is {v}"),
            "Bl": ("field at the centre", "the field at the centre of the loop is {v}"),
            "Bs": ("field inside", "the field inside the solenoid is {v}"),
            "I": ("current", "the current is {v}"),
            "I2": ("second current", "the current in the second wire is {v}"),
            "r": ("distance", "the distance is {v}"),
            "N": ("number of turns", "the number of turns is {v}"),
            "n": ("turns per metre", "the number of turns per metre is {v}"),
            "f": ("force per unit length", "the force on each metre of wire is {v}"),
        },
        base=bases(
            {
                "I": ("I", "A"),
                "I2": ("I2", "A"),
                "r": ("r", "cm"),
                "N": ("N", "unit"),
                "n": ("n", "per_m"),
            }
        ),
        derived=lambda p: (
            ("Bw", "2*mu0_4pi*I/r"),
            ("Bl", "mu0*N*I/(2*r)"),
            ("Bs", "mu0*n*I"),
            ("f", "2*mu0_4pi*I*I2/r"),
        ),
        dunits={"Bw": "uT", "Bl": "uT", "Bs": "mT", "f": "mN/m"},
        consts={"mu0": "mu0", "mu0_4pi": "mu0_4pi"},
        laws=("Bw*r - 2*mu0_4pi*I",),
        variants={
            v.id: v
            for v in (
                var(
                    "Bw",
                    "I r",
                    "2*mu0_4pi*I/r",
                    "B = (mu0 / 4 pi) x 2 x I / r for a long straight wire",
                    "Find the field at that distance from the wire.",
                    [
                        ("DISTANCE_SQUARED", "2*mu0_4pi*I/r^2"),
                        ("FACTOR_TWO_FORGOTTEN", "mu0_4pi*I/r"),
                        ("MU0_USED_FOR_MU0_OVER_4PI", "mu0*I/r"),
                        ("DISTANCE_UNIT_SLIP", "2*mu0_4pi*I/r_r"),
                    ],
                ),
                var(
                    "I",
                    "Bw r",
                    "Bw*r/(2*mu0_4pi)",
                    "B = (mu0 / 4 pi) x 2 x I / r for a long straight wire",
                    "Find the current in the wire.",
                    [
                        ("FACTOR_TWO_FORGOTTEN", "Bw*r/mu0_4pi"),
                        ("DISTANCE_SQUARED", "Bw*r^2/(2*mu0_4pi)"),
                        ("FORMULA_INVERTED", "2*mu0_4pi/(Bw*r)"),
                    ],
                    laws=("Bw*r - 2*mu0_4pi*I",),
                    rearr="multiply each side by r and divide each side by 2 x (mu0 / 4 pi)",
                ),
                var(
                    "Bl",
                    "N I r",
                    "mu0*N*I/(2*r)",
                    "B = mu0 x N x I / (2 x r) at the centre of a circular coil",
                    "Find the field at the centre of the coil.",
                    [
                        ("HALF_FORGOTTEN", "mu0*N*I/r"),
                        ("TURNS_FORGOTTEN", "mu0*I/(2*r)"),
                        ("DISTANCE_UNIT_SLIP", "mu0*N*I/(2*r_r)"),
                        ("DISTANCE_SQUARED", "mu0*N*I/(2*r^2)"),
                    ],
                    laws=("Bl*2*r - mu0*N*I",),
                ),
                var(
                    "I",
                    "Bl N r",
                    "2*r*Bl/(mu0*N)",
                    "B = mu0 x N x I / (2 x r) at the centre of a circular coil",
                    "Find the current in the coil.",
                    [
                        ("HALF_FORGOTTEN", "r*Bl/(mu0*N)"),
                        ("TURNS_FORGOTTEN", "2*r*Bl/mu0"),
                        ("FORMULA_INVERTED", "mu0*N/(2*r*Bl)"),
                    ],
                    laws=("Bl*2*r - mu0*N*I",),
                    rearr="multiply each side by 2 x r and divide each side by mu0 x N",
                ),
                var(
                    "Bs",
                    "n I",
                    "mu0*n*I",
                    "B = mu0 x n x I inside a long solenoid",
                    "Find the field inside the solenoid.",
                    [
                        ("TURNS_DIVIDED", "mu0*I/n"),
                        ("TURNS_FORGOTTEN", "mu0*I"),
                        ("CURRENT_FORGOTTEN", "mu0*n"),
                        ("TURNS_SQUARED", "mu0*n^2*I"),
                    ],
                    laws=("Bs - mu0*n*I",),
                ),
                var(
                    "n",
                    "Bs I",
                    "Bs/(mu0*I)",
                    "B = mu0 x n x I inside a long solenoid",
                    "Find the number of turns on each metre of the solenoid.",
                    [
                        ("MULTIPLIED_NOT_DIVIDED", "Bs*mu0*I"),
                        ("CURRENT_FORGOTTEN", "Bs/mu0"),
                        ("FORMULA_INVERTED", "mu0*I/Bs"),
                    ],
                    laws=("Bs - mu0*n*I",),
                    rearr="divide each side by mu0 x I",
                ),
                var(
                    "f",
                    "I I2 r",
                    "2*mu0_4pi*I*I2/r",
                    "force per metre = (mu0 / 4 pi) x 2 x I1 x I2 / d for two long parallel wires",
                    "Find the force on each metre of either wire.",
                    [
                        ("FACTOR_TWO_FORGOTTEN", "mu0_4pi*I*I2/r"),
                        ("DISTANCE_SQUARED", "2*mu0_4pi*I*I2/r^2"),
                        ("CURRENTS_ADDED", "2*mu0_4pi*(I+I2)/r"),
                        ("DISTANCE_UNIT_SLIP", "2*mu0_4pi*I*I2/r_r"),
                    ],
                    laws=("f*r - 2*mu0_4pi*I*I2",),
                ),
            )
        },
    ),
    "Find the field of a straight wire, a coil or a solenoid, or the force between two wires",
    (P + "SCI_NOTATION", P + "REARRANGE_FORMULA", "PHY.C12.MAG.LORENTZ"),
)

FORCE_WIRE = reg(
    model(
        "MAG.FORCE_WIRE",
        "MAG",
        "force_and_torque_on_current",
        "a current-carrying conductor in a magnetic field",
        syms={
            "F": "N",
            "B": "T",
            "I": "A",
            "L": "m",
            "s": "unit",
            "N": "unit",
            "A": "m^2",
            "tau": "Nm",
        },
        labels={
            "F": ("force", "the force on the wire is {v}"),
            "B": ("field", "the magnetic field is {v}"),
            "I": ("current", "the current is {v}"),
            "L": ("length", "the length of wire in the field is {v}"),
            "s": (
                "sine of the angle",
                "the sine of the angle between the wire and the field is {v}",
            ),
            "N": ("number of turns", "the number of turns is {v}"),
            "A": ("area", "the area of the coil is {v}"),
            "tau": ("torque", "the torque on the coil is {v}"),
        },
        base=bases(
            {
                "B": ("B", "mT"),
                "I": ("I", "A"),
                "L": ("L", "cm"),
                "s": ("s", "unit"),
                "N": ("N", "unit"),
                "A": ("A", "cm^2"),
            }
        ),
        derived=lambda p: (("F", "B*I*L*s"), ("tau", "N*I*A*B*s")),
        dunits={"F": "mN", "tau": "mNm"},
        laws=("F - B*I*L*s",),
        variants={
            v.id: v
            for v in (
                var(
                    "F",
                    "B I L s",
                    "B*I*L*s",
                    "F = B x I x L x sine of the angle",
                    "Find the force on the wire.",
                    [
                        ("SINE_FORGOTTEN", "B*I*L"),
                        ("LENGTH_UNIT_SLIP", "B*I*L_r*s"),
                        ("FIELD_DIVIDED", "I*L*s/B"),
                        ("CURRENT_FORGOTTEN", "B*L*s"),
                    ],
                ),
                var(
                    "B",
                    "F I L s",
                    "F/(I*L*s)",
                    "F = B x I x L x sine of the angle",
                    "Find the strength of the field.",
                    [
                        ("SINE_FORGOTTEN", "F/(I*L)"),
                        ("MULTIPLIED_NOT_DIVIDED", "F*I*L*s"),
                        ("LENGTH_UNIT_SLIP", "F/(I*L_r*s)"),
                    ],
                    rearr="divide each side by I x L x sine of the angle",
                ),
                var(
                    "I",
                    "F B L s",
                    "F/(B*L*s)",
                    "F = B x I x L x sine of the angle",
                    "Find the current in the wire.",
                    [
                        ("SINE_FORGOTTEN", "F/(B*L)"),
                        ("MULTIPLIED_NOT_DIVIDED", "F*B*L*s"),
                        ("LENGTH_UNIT_SLIP", "F/(B*L_r*s)"),
                    ],
                    rearr="divide each side by B x L x sine of the angle",
                ),
                var(
                    "tau",
                    "N I A B s",
                    "N*I*A*B*s",
                    "torque = N x I x A x B x sine of the angle on a flat coil",
                    "Find the torque on the coil.",
                    [
                        ("SINE_FORGOTTEN", "N*I*A*B"),
                        ("TURNS_FORGOTTEN", "I*A*B*s"),
                        ("AREA_UNIT_SLIP", "N*I*A_r*B*s"),
                        ("FIELD_UNIT_SLIP", "N*I*A*B_r*s"),
                    ],
                    laws=("tau - N*I*A*B*s",),
                ),
                var(
                    "N",
                    "tau I A B s",
                    "tau/(I*A*B*s)",
                    "torque = N x I x A x B x sine of the angle on a flat coil",
                    "Find the number of turns on the coil.",
                    [
                        ("SINE_FORGOTTEN", "tau/(I*A*B)"),
                        ("MULTIPLIED_NOT_DIVIDED", "tau*I*A*B*s"),
                        ("AREA_UNIT_SLIP", "tau/(I*A_r*B*s)"),
                    ],
                    laws=("tau - N*I*A*B*s",),
                    rearr="divide each side by I x A x B x sine of the angle",
                ),
            )
        },
    ),
    "Find the force on a current-carrying wire, or the torque on a coil, in a magnetic field",
    (P + "REARRANGE_FORMULA", P + "UNIT_PREFIXES", "PHY.C12.MAG.B_FIELD"),
)


def _galv(p):  # type: ignore[no-untyped-def]
    return bases({"G": ("G", "ohm"), "Ig": ("Ig", "mA"), "n": ("n", "unit"), "V": ("V", "V")})(p)


GALV = reg(
    model(
        "MAG.GALV",
        "MAG",
        "galvanometer_conversion",
        "converting a galvanometer into an ammeter or a voltmeter",
        syms={"G": "ohm", "Ig": "A", "n": "unit", "I": "A", "S": "ohm", "V": "V", "Rs": "ohm"},
        labels={
            "G": ("coil resistance", "the galvanometer coil has a resistance of {v}"),
            "Ig": ("full scale current", "its full scale deflection needs {v}"),
            "I": ("ammeter range", "the ammeter must read up to {v}"),
            "S": ("shunt", "the shunt resistance is {v}"),
            "V": ("voltmeter range", "the voltmeter must read up to {v}"),
            "Rs": ("series resistance", "the series resistance is {v}"),
        },
        base=_galv,
        derived=lambda p: (("I", "n*Ig"), ("S", "G/(n-1)"), ("Rs", "V/Ig-G")),
        dunits={"I": "mA", "S": "ohm", "Rs": "ohm"},
        laws=("S*(I - Ig) - G*Ig",),
        variants={
            v.id: v
            for v in (
                var(
                    "S",
                    "G Ig I",
                    "G*Ig/(I-Ig)",
                    "the shunt takes the extra current: Ig x G = (I - Ig) x S",
                    "Find the shunt resistance needed.",
                    [
                        ("TOTAL_CURRENT_USED", "G*Ig/I"),
                        ("FORMULA_INVERTED", "G*(I-Ig)/Ig"),
                        ("SHUNT_IN_SERIES", "G*I/Ig"),
                        ("CURRENTS_ADDED", "G*Ig/(I+Ig)"),
                    ],
                    laws=("S*(I - Ig) - G*Ig",),
                    rearr="divide each side of Ig x G = (I - Ig) x S by (I - Ig)",
                ),
                var(
                    "I",
                    "G Ig S",
                    "Ig*(G+S)/S",
                    "Ig x G = (I - Ig) x S, so I = Ig x (G + S) / S",
                    "Find the largest current the ammeter can read.",
                    [
                        ("SHUNT_ONLY_CURRENT", "Ig*S/(G+S)"),
                        ("RESISTANCES_NOT_ADDED", "Ig*G/S"),
                        ("FULL_SCALE_CURRENT_COPIED", "Ig+Ig*G/S+Ig"),
                        ("FORMULA_INVERTED", "S*Ig/G"),
                    ],
                    laws=("S*(I - Ig) - G*Ig",),
                ),
                var(
                    "Rs",
                    "V Ig G",
                    "V/Ig-G",
                    "V = Ig x (G + Rs), so Rs = V / Ig - G",
                    "Find the series resistance needed.",
                    [
                        ("COIL_RESISTANCE_FORGOTTEN", "V/Ig"),
                        ("COIL_RESISTANCE_ADDED", "V/Ig+G"),
                        ("FORMULA_INVERTED", "Ig/V-G"),
                        ("CURRENT_UNIT_SLIP", "V/Ig_r-G"),
                    ],
                    laws=("V - Ig*(G+Rs)",),
                ),
                var(
                    "V",
                    "Ig G Rs",
                    "Ig*(G+Rs)",
                    "V = Ig x (G + Rs)",
                    "Find the largest voltage the voltmeter can read.",
                    [
                        ("COIL_RESISTANCE_FORGOTTEN", "Ig*Rs"),
                        ("DIVIDED_NOT_MULTIPLIED", "Ig/(G+Rs)"),
                        ("CURRENT_UNIT_SLIP", "Ig_r*(G+Rs)"),
                    ],
                    laws=("V - Ig*(G+Rs)",),
                ),
            )
        },
    ),
    "Convert a galvanometer into an ammeter with a shunt or a voltmeter with a series resistor",
    (P + "SERIES_RESISTORS", P + "PARALLEL_RESISTORS", P + "REARRANGE_FORMULA"),
)

# ---------------------------------------------------------------- magnetism and matter
MAG_MATERIALS = reg(
    model(
        "MAT.MAG_MATERIALS",
        "MAT",
        "magnetic_materials",
        "a magnetic material in an external field",
        syms={"chi": "unit", "mur": "unit", "H": "A/m", "B": "T", "M": "A/m", "mu0": "N/A^2"},
        labels={
            "chi": ("susceptibility", "the magnetic susceptibility is {v}"),
            "mur": ("relative permeability", "the relative permeability is {v}"),
            "H": ("magnetising field", "the magnetising field is {v}"),
            "B": ("magnetic field", "the magnetic field inside the material is {v}"),
            "M": ("magnetisation", "the magnetisation is {v}"),
        },
        base=bases({"chi": ("chi", "unit"), "H": ("H", "A/m")}),
        derived=lambda p: (("mur", "1+chi"), ("B", "mu0*mur*H"), ("M", "chi*H")),
        dunits={"mur": "unit", "B": "mT", "M": "A/m"},
        consts={"mu0": "mu0"},
        laws=("mur - 1 - chi",),
        variants={
            v.id: v
            for v in (
                var(
                    "mur",
                    "chi",
                    "1+chi",
                    "relative permeability = 1 + susceptibility",
                    "Find the relative permeability.",
                    [
                        ("SUSCEPTIBILITY_TAKEN_AS_PERMEABILITY", "chi"),
                        ("SUSCEPTIBILITY_SUBTRACTED", "chi-1"),
                        ("PERMEABILITY_RECIPROCAL", "1/(1+chi)"),
                        ("ONE_FORGOTTEN_TWICE", "chi+2"),
                    ],
                ),
                var(
                    "chi",
                    "mur",
                    "mur-1",
                    "relative permeability = 1 + susceptibility",
                    "Find the magnetic susceptibility.",
                    [
                        ("PERMEABILITY_TAKEN_AS_SUSCEPTIBILITY", "mur"),
                        ("ONE_ADDED", "mur+1"),
                        ("RECIPROCAL_TAKEN", "1/(mur-1)"),
                    ],
                    laws=("mur - 1 - chi",),
                    rearr="subtract 1 from each side",
                ),
                var(
                    "B",
                    "mur H",
                    "mu0*mur*H",
                    "B = mu0 x relative permeability x H",
                    "Find the magnetic field inside the material.",
                    [
                        ("PERMEABILITY_FORGOTTEN", "mu0*H"),
                        ("VACUUM_PERMEABILITY_FORGOTTEN", "mur*H"),
                        ("DIVIDED_NOT_MULTIPLIED", "mu0*H/mur"),
                        ("FIELD_UNIT_SLIP", "mu0*mur*H_r"),
                    ],
                    laws=("B - mu0*mur*H",),
                ),
                var(
                    "H",
                    "B mur",
                    "B/(mu0*mur)",
                    "B = mu0 x relative permeability x H",
                    "Find the magnetising field.",
                    [
                        ("PERMEABILITY_FORGOTTEN", "B/mu0"),
                        ("MULTIPLIED_NOT_DIVIDED", "B*mu0*mur"),
                        ("FORMULA_INVERTED", "mu0*mur/B"),
                    ],
                    laws=("B - mu0*mur*H",),
                    rearr="divide each side by mu0 x relative permeability",
                ),
                var(
                    "M",
                    "chi H",
                    "chi*H",
                    "magnetisation = susceptibility x H",
                    "Find the magnetisation of the material.",
                    [
                        ("DIVIDED_NOT_MULTIPLIED", "H/chi"),
                        ("PERMEABILITY_USED_FOR_SUSCEPTIBILITY", "(1+chi)*H"),
                        ("SUSCEPTIBILITY_ADDED", "chi+H"),
                    ],
                    laws=("M - chi*H",),
                ),
                var(
                    "mur",
                    "B H",
                    "B/(mu0*H)",
                    "B = mu0 x relative permeability x H",
                    "Find the relative permeability.",
                    [
                        ("VACUUM_PERMEABILITY_FORGOTTEN", "B/H"),
                        ("MULTIPLIED_NOT_DIVIDED", "B*mu0*H"),
                        ("FORMULA_INVERTED", "mu0*H/B"),
                    ],
                    laws=("B - mu0*mur*H",),
                ),
            )
        },
    ),
    "Relate susceptibility, relative permeability, magnetisation and the field in a material",
    (P + "REARRANGE_FORMULA", P + "SCI_NOTATION", "PHY.C12.MAG.B_FIELD"),
)

# ---------------------------------------------------------------- electromagnetic induction
FARADAY = reg(
    model(
        "EMI.FARADAY",
        "EMI",
        "faraday_law",
        "a coil in a changing magnetic field",
        syms={"eps": "V", "N": "unit", "dPhi": "Wb", "dt": "s", "dB": "T", "A": "m^2"},
        labels={
            "eps": ("induced emf", "the induced emf is {v}"),
            "N": ("number of turns", "the number of turns is {v}"),
            "dPhi": ("change in flux", "the flux through the coil changes by {v}"),
            "dt": ("time", "the change takes {v}"),
            "dB": ("change in field", "the field changes by {v}"),
            "A": ("area", "the area of the coil is {v}"),
        },
        base=bases({"N": ("N", "unit"), "dB": ("dB", "T"), "A": ("A", "cm^2"), "dt": ("dt", "ms")}),
        derived=lambda p: (("dPhi", "dB*A"), ("eps", "N*dPhi/dt")),
        dunits={"dPhi": "mWb", "eps": "V"},
        laws=("eps*dt - N*dPhi",),
        variants={
            v.id: v
            for v in (
                var(
                    "eps",
                    "N dPhi dt",
                    "N*dPhi/dt",
                    "emf = N x flux change / time",
                    "Find the magnitude of the induced emf.",
                    [
                        ("TURNS_FORGOTTEN", "dPhi/dt"),
                        ("TIME_NOT_DIVIDED", "N*dPhi*dt"),
                        ("TIME_UNIT_SLIP", "N*dPhi/dt_r"),
                        ("FORMULA_INVERTED", "dt/(N*dPhi)"),
                    ],
                    laws=("eps*dt - N*dPhi",),
                ),
                var(
                    "dPhi",
                    "dB A",
                    "dB*A",
                    "change in flux = (change in field) x area, for a field along the normal",
                    "Find the change in magnetic flux through the coil.",
                    [
                        ("AREA_UNIT_SLIP", "dB*A_r"),
                        ("DIVIDED_NOT_MULTIPLIED", "dB/A"),
                        ("FIELDS_ADDED", "dB+A"),
                    ],
                    laws=("dPhi - dB*A",),
                ),
                var(
                    "eps",
                    "N dB A dt",
                    "N*dB*A/dt",
                    "flux change = dB x A, then emf = N x (flux change) / time",
                    "Find the magnitude of the induced emf.",
                    [
                        ("TURNS_FORGOTTEN", "dB*A/dt"),
                        ("AREA_UNIT_SLIP", "N*dB*A_r/dt"),
                        ("TIME_UNIT_SLIP", "N*dB*A/dt_r"),
                        ("TIME_NOT_DIVIDED", "N*dB*A*dt"),
                    ],
                    laws=("eps*dt - N*dB*A",),
                ),
                var(
                    "N",
                    "eps dPhi dt",
                    "eps*dt/dPhi",
                    "emf = N x flux change / time",
                    "Find the number of turns in the coil.",
                    [
                        ("FORMULA_INVERTED", "dPhi/(eps*dt)"),
                        ("TIME_NOT_MULTIPLIED", "eps*dPhi/dt"),
                        ("TIME_UNIT_SLIP", "eps*dt_r/dPhi"),
                    ],
                    laws=("eps*dt - N*dPhi",),
                    rearr="multiply each side by the time and divide each side by the flux change",
                ),
                var(
                    "dt",
                    "eps N dPhi",
                    "N*dPhi/eps",
                    "emf = N x flux change / time",
                    "Find the time taken for the flux to change.",
                    [
                        ("FORMULA_INVERTED", "eps/(N*dPhi)"),
                        ("TURNS_FORGOTTEN", "dPhi/eps"),
                        ("MULTIPLIED_NOT_DIVIDED", "eps*N*dPhi"),
                    ],
                    laws=("eps*dt - N*dPhi",),
                    rearr="multiply each side by the time and divide each side by the emf",
                ),
            )
        },
    ),
    "Find the emf induced in a coil by a changing flux, or the turns or time behind it",
    (P + "REARRANGE_FORMULA", P + "UNIT_PREFIXES", "PHY.C12.MAG.FORCE_WIRE"),
)

MOTIONAL = reg(
    model(
        "EMI.MOTIONAL",
        "EMI",
        "motional_emf",
        "a rod sliding on rails in a magnetic field",
        syms={"eps": "V", "B": "T", "l": "m", "v": "m/s", "R": "ohm", "I": "A", "F": "N"},
        labels={
            "eps": ("induced emf", "the induced emf is {v}"),
            "B": ("field", "the magnetic field is {v}"),
            "l": ("rod length", "the rod is {v} long"),
            "v": ("speed", "the speed of the rod is {v}"),
            "R": ("resistance", "the resistance of the circuit is {v}"),
            "I": ("current", "the induced current is {v}"),
            "F": ("force", "the force needed to keep it moving steadily is {v}"),
        },
        base=bases({"B": ("B", "mT"), "l": ("l", "cm"), "v": ("v", "m/s"), "R": ("R", "ohm")}),
        derived=lambda p: (("eps", "B*l*v"), ("I", "B*l*v/R"), ("F", "B*B*l*l*v/R")),
        dunits={"eps": "mV", "I": "mA", "F": "mN"},
        laws=("eps - B*l*v",),
        variants={
            v.id: v
            for v in (
                var(
                    "eps",
                    "B l v",
                    "B*l*v",
                    "emf = B x l x v",
                    "Find the induced emf across the rod.",
                    [
                        ("SPEED_FORGOTTEN", "B*l"),
                        ("LENGTH_UNIT_SLIP", "B*l_r*v"),
                        ("DIVIDED_NOT_MULTIPLIED", "B*l/v"),
                        ("FIELD_UNIT_SLIP", "B_r*l*v"),
                    ],
                ),
                var(
                    "v",
                    "eps B l",
                    "eps/(B*l)",
                    "emf = B x l x v",
                    "Find the speed of the rod.",
                    [
                        ("MULTIPLIED_NOT_DIVIDED", "eps*B*l"),
                        ("LENGTH_FORGOTTEN", "eps/B"),
                        ("LENGTH_UNIT_SLIP", "eps/(B*l_r)"),
                    ],
                    laws=("eps - B*l*v",),
                    rearr="divide each side by B x l",
                ),
                var(
                    "I",
                    "B l v R",
                    "B*l*v/R",
                    "emf = B x l x v, then I = emf / R",
                    "Find the current in the circuit.",
                    [
                        ("RESISTANCE_MULTIPLIED", "B*l*v*R"),
                        ("LENGTH_UNIT_SLIP", "B*l_r*v/R"),
                        ("EMF_AS_CURRENT", "B*l*v"),
                        ("SPEED_FORGOTTEN", "B*l/R"),
                    ],
                    laws=("I*R - B*l*v",),
                ),
                var(
                    "F",
                    "B I l",
                    "B*I*l",
                    "F = B x I x l on the current-carrying rod",
                    "Find the force on the rod.",
                    [
                        ("LENGTH_UNIT_SLIP", "B*I*l_r"),
                        ("CURRENT_FORGOTTEN", "B*l"),
                        ("DIVIDED_NOT_MULTIPLIED", "B*I/l"),
                    ],
                    laws=("F - B*I*l",),
                ),
                var(
                    "l",
                    "eps B v",
                    "eps/(B*v)",
                    "emf = B x l x v",
                    "Find the length of the rod.",
                    [
                        ("MULTIPLIED_NOT_DIVIDED", "eps*B*v"),
                        ("SPEED_FORGOTTEN", "eps/B"),
                        ("FORMULA_INVERTED", "B*v/eps"),
                    ],
                    laws=("eps - B*l*v",),
                    rearr="divide each side by B x v",
                ),
            )
        },
    ),
    "Find the motional emf, the current and the force on a rod moving in a field",
    (P + "REARRANGE_FORMULA", P + "UNIT_PREFIXES", "PHY.C12.MAG.FORCE_WIRE"),
)

INDUCTOR = reg(
    model(
        "EMI.INDUCTOR",
        "EMI",
        "self_inductance",
        "an inductor in a circuit",
        syms={"L": "H", "dI": "A", "dt": "s", "eps": "V", "I": "A", "U": "J"},
        labels={
            "L": ("inductance", "the inductance is {v}"),
            "dI": ("change in current", "the current changes by {v}"),
            "dt": ("time", "the change takes {v}"),
            "eps": ("induced emf", "the induced emf is {v}"),
            "I": ("current", "the steady current is {v}"),
            "U": ("stored energy", "the energy stored in the magnetic field is {v}"),
        },
        base=bases({"L": ("L", "mH"), "dI": ("dI", "A"), "dt": ("dt", "ms"), "I": ("I", "A")}),
        derived=lambda p: (("eps", "L*dI/dt"), ("U", "L*I^2/2")),
        dunits={"eps": "V", "U": "mJ"},
        laws=("eps*dt - L*dI",),
        variants={
            v.id: v
            for v in (
                var(
                    "eps",
                    "L dI dt",
                    "L*dI/dt",
                    "emf = L x current change / time",
                    "Find the magnitude of the induced emf.",
                    [
                        ("TIME_NOT_DIVIDED", "L*dI*dt"),
                        ("TIME_UNIT_SLIP", "L*dI/dt_r"),
                        ("FORMULA_INVERTED", "dt/(L*dI)"),
                        ("INDUCTANCE_UNIT_SLIP", "L_r*dI/dt"),
                    ],
                ),
                var(
                    "L",
                    "eps dI dt",
                    "eps*dt/dI",
                    "emf = L x current change / time",
                    "Find the inductance of the coil.",
                    [
                        ("FORMULA_INVERTED", "dI/(eps*dt)"),
                        ("TIME_NOT_MULTIPLIED", "eps*dI/dt"),
                        ("TIME_UNIT_SLIP", "eps*dt_r/dI"),
                    ],
                    laws=("eps*dt - L*dI",),
                    rearr="multiply each side by the time and divide each side by the change in current",
                ),
                var(
                    "dI",
                    "eps dt L",
                    "eps*dt/L",
                    "emf = L x current change / time",
                    "Find the change in current.",
                    [
                        ("FORMULA_INVERTED", "L/(eps*dt)"),
                        ("TIME_NOT_MULTIPLIED", "eps/(L*dt)"),
                        ("INDUCTANCE_UNIT_SLIP", "eps*dt/L_r"),
                    ],
                    laws=("eps*dt - L*dI",),
                ),
                var(
                    "U",
                    "L I",
                    "L*I^2/2",
                    "U = (1/2) x L x I^2",
                    "Find the energy stored in the inductor.",
                    [
                        ("HALF_FORGOTTEN", "L*I^2"),
                        ("CURRENT_NOT_SQUARED", "L*I/2"),
                        ("SQUARED_AFTER_HALVING", "(L*I/2)^2"),
                        ("INDUCTANCE_UNIT_SLIP", "L_r*I^2/2"),
                    ],
                    laws=("U*2 - L*I**2",),
                ),
                var(
                    "I",
                    "U L",
                    "sqrt(2*U/L)",
                    "U = (1/2) x L x I^2",
                    "Find the current in the inductor.",
                    [
                        ("ROOT_FORGOTTEN", "2*U/L"),
                        ("HALF_FORGOTTEN", "sqrt(U/L)"),
                        ("FORMULA_INVERTED", "sqrt(L/(2*U))"),
                    ],
                    laws=("U*2 - L*I**2",),
                    rearr="multiply each side by 2, divide each side by L, then take the square root",
                ),
                var(
                    "L",
                    "U I",
                    "2*U/I^2",
                    "U = (1/2) x L x I^2",
                    "Find the inductance.",
                    [
                        ("HALF_FORGOTTEN", "U/I^2"),
                        ("CURRENT_NOT_SQUARED", "2*U/I"),
                        ("MULTIPLIED_NOT_DIVIDED", "2*U*I^2"),
                    ],
                    laws=("U*2 - L*I**2",),
                ),
            )
        },
    ),
    "Find the emf across an inductor, or its inductance, current or stored energy",
    (P + "REARRANGE_FORMULA", P + "UNIT_PREFIXES", "PHY.C12.EMI.FARADAY"),
)

# ---------------------------------------------------------------- alternating current
REACTANCE = reg(
    model(
        "AC.REACTANCE",
        "AC",
        "reactance",
        "an inductor or a capacitor in an alternating circuit",
        syms={"w": "rad/s", "L": "H", "C": "F", "XL": "ohm", "XC": "ohm"},
        labels={
            "w": ("angular frequency", "the angular frequency of the supply is {v}"),
            "L": ("inductance", "the inductance is {v}"),
            "C": ("capacitance", "the capacitance is {v}"),
            "XL": ("inductive reactance", "the inductive reactance is {v}"),
            "XC": ("capacitive reactance", "the capacitive reactance is {v}"),
        },
        base=bases({"w": ("w", "rad/s"), "L": ("L", "mH"), "C": ("C", "uF")}),
        derived=lambda p: (("XL", "w*L"), ("XC", "1/(w*C)")),
        dunits={"XL": "ohm", "XC": "ohm"},
        laws=("XL - w*L",),
        variants={
            v.id: v
            for v in (
                var(
                    "XL",
                    "w L",
                    "w*L",
                    "XL = w x L",
                    "Find the inductive reactance.",
                    [
                        ("DIVIDED_NOT_MULTIPLIED", "w/L"),
                        ("INDUCTANCE_UNIT_SLIP", "w*L_r"),
                        ("CAPACITIVE_FORMULA_USED", "1/(w*L)"),
                    ],
                ),
                var(
                    "XC",
                    "w C",
                    "1/(w*C)",
                    "XC = 1 / (w x C)",
                    "Find the capacitive reactance.",
                    [
                        ("RECIPROCAL_FORGOTTEN", "w*C"),
                        ("OMEGA_DIVIDED", "w/C"),
                        ("CAPACITANCE_UNIT_SLIP", "1/(w*C_r)"),
                    ],
                    laws=("XC*w*C - 1",),
                ),
                var(
                    "L",
                    "XL w",
                    "XL/w",
                    "XL = w x L",
                    "Find the inductance.",
                    [
                        ("MULTIPLIED_NOT_DIVIDED", "XL*w"),
                        ("FORMULA_INVERTED", "w/XL"),
                        ("CAPACITIVE_FORMULA_USED", "1/(XL*w)"),
                    ],
                    laws=("XL - w*L",),
                    rearr="divide each side by w",
                ),
                var(
                    "C",
                    "XC w",
                    "1/(w*XC)",
                    "XC = 1 / (w x C)",
                    "Find the capacitance.",
                    [
                        ("RECIPROCAL_FORGOTTEN", "XC/w"),
                        ("MULTIPLIED_NOT_DIVIDED", "XC*w"),
                        ("FORMULA_INVERTED", "w*XC"),
                    ],
                    laws=("XC*w*C - 1",),
                    rearr="multiply each side by C, then divide each side by XC x w",
                ),
                var(
                    "w",
                    "XL L",
                    "XL/L",
                    "XL = w x L",
                    "Find the angular frequency of the supply.",
                    [
                        ("MULTIPLIED_NOT_DIVIDED", "XL*L"),
                        ("FORMULA_INVERTED", "L/XL"),
                        ("INDUCTANCE_UNIT_SLIP", "XL/L_r"),
                    ],
                    laws=("XL - w*L",),
                ),
            )
        },
    ),
    "Find the reactance of an inductor or a capacitor, or the quantity behind it",
    (P + "REARRANGE_FORMULA", P + "UNIT_PREFIXES", P + "RECIPROCALS"),
)


def _lcr(p):  # type: ignore[no-untyped-def]
    from app.factory.lanes.physics_c12.quantities import to_si

    r, xl, xc = str(p["rxx"]).split(",")
    return (
        {
            "R": to_si(r, "ohm"),
            "XL": to_si(xl, "ohm"),
            "XC": to_si(xc, "ohm"),
            "V": to_si(p["V"], "V"),
        },
        {"R": "ohm", "XL": "ohm", "XC": "ohm", "V": "V"},
    )


LCR = reg(
    model(
        "AC.LCR",
        "AC",
        "series_lcr",
        "a series LCR circuit on an alternating supply",
        syms={
            "R": "ohm",
            "XL": "ohm",
            "XC": "ohm",
            "Z": "ohm",
            "V": "V",
            "I": "A",
            "cosp": "unit",
            "P": "W",
            "tp": "unit",
        },
        labels={
            "R": ("resistance", "the resistance is {v}"),
            "XL": ("inductive reactance", "the inductive reactance is {v}"),
            "XC": ("capacitive reactance", "the capacitive reactance is {v}"),
            "Z": ("impedance", "the impedance is {v}"),
            "V": ("rms voltage", "the rms supply voltage is {v}"),
            "I": ("rms current", "the rms current is {v}"),
            "cosp": ("power factor", "the power factor is {v}"),
            "P": ("average power", "the average power is {v}"),
            "tp": ("tangent of the phase angle", "the tangent of the phase angle is {v}"),
        },
        base=_lcr,
        derived=lambda p: (
            ("Z", "sqrt(R^2+(XL-XC)^2)"),
            ("I", "V/Z"),
            ("cosp", "R/Z"),
            ("P", "I^2*R"),
            ("tp", "(XL-XC)/R"),
        ),
        dunits={"Z": "ohm", "I": "A", "cosp": "unit", "P": "W", "tp": "unit"},
        laws=("Z**2 - R**2 - (XL - XC)**2",),
        variants={
            v.id: v
            for v in (
                var(
                    "Z",
                    "R XL XC",
                    "sqrt(R^2+(XL-XC)^2)",
                    "Z = square root of (R^2 + (XL - XC)^2)",
                    "Find the impedance of the circuit.",
                    [
                        ("REACTANCES_ADDED_TO_RESISTANCE", "R+XL-XC"),
                        ("REACTANCES_BOTH_SQUARED", "sqrt(R^2+XL^2+XC^2)"),
                        ("REACTANCES_ADDED", "sqrt(R^2+(XL+XC)^2)"),
                        ("ROOT_FORGOTTEN", "R^2+(XL-XC)^2"),
                    ],
                ),
                var(
                    "I",
                    "V R XL XC",
                    "V/sqrt(R^2+(XL-XC)^2)",
                    "Z = square root of (R^2 + (XL - XC)^2), then I = V / Z",
                    "Find the rms current.",
                    [
                        ("RESISTANCE_ONLY_USED", "V/R"),
                        ("REACTANCES_ADDED_TO_RESISTANCE", "V/(R+XL-XC)"),
                        ("REACTANCES_ADDED", "V/sqrt(R^2+(XL+XC)^2)"),
                        ("MULTIPLIED_NOT_DIVIDED", "V*sqrt(R^2+(XL-XC)^2)"),
                    ],
                    laws=("I*Z - V", "Z**2 - R**2 - (XL - XC)**2"),
                ),
                var(
                    "cosp",
                    "R Z",
                    "R/Z",
                    "power factor = cosine of phi = R / Z",
                    "Find the power factor of the circuit.",
                    [
                        ("FORMULA_INVERTED", "Z/R"),
                        ("DIFFERENCE_USED", "(Z-R)/Z"),
                        ("RESISTANCES_ADDED", "R/(R+Z)"),
                    ],
                    laws=("cosp*Z - R",),
                    rearr="no rearranging is needed",
                ),
                var(
                    "P",
                    "V I cosp",
                    "V*I*cosp",
                    "P = V x I x cosine of phi",
                    "Find the average power used.",
                    [
                        ("POWER_FACTOR_FORGOTTEN", "V*I"),
                        ("POWER_FACTOR_DIVIDED", "V*I/cosp"),
                        ("VOLTAGE_FORGOTTEN", "I*cosp"),
                    ],
                    laws=("P - V*I*cosp",),
                ),
                var(
                    "P",
                    "I R",
                    "I^2*R",
                    "P = I^2 x R, only the resistor uses power",
                    "Find the average power used.",
                    [
                        ("CURRENT_NOT_SQUARED", "I*R"),
                        ("REACTANCE_POWER_USED", "I^2*R*R"),
                        ("FORMULA_INVERTED", "I^2/R"),
                    ],
                    laws=("P - I**2*R",),
                ),
                var(
                    "tp",
                    "R XL XC",
                    "(XL-XC)/R",
                    "tangent of phi = (XL - XC) / R",
                    "Find tan of the phase angle.",
                    [
                        ("FORMULA_INVERTED", "R/(XL-XC)"),
                        ("REACTANCES_ADDED", "(XL+XC)/R"),
                        ("IMPEDANCE_USED", "sqrt(R^2+(XL-XC)^2)/R"),
                    ],
                    laws=("tp*R - XL + XC",),
                ),
            )
        },
    ),
    "Find the impedance, current, power factor, phase and power of a series LCR circuit",
    (P + "REARRANGE_FORMULA", P + "RIGHT_TRIANGLES", "PHY.C12.AC.REACTANCE"),
)


def _resonance(p):  # type: ignore[no-untyped-def]
    base = pairs(("L", "C"), "lc", "mH", "uF")(p)
    r = bases({"R": ("R", "ohm")})(p)
    base[0].update(r[0])
    base[1].update(r[1])
    return base


RESONANCE = reg(
    model(
        "AC.RESONANCE",
        "AC",
        "lcr_resonance",
        "a series LCR circuit at resonance",
        syms={"w0": "rad/s", "L": "H", "C": "F", "R": "ohm", "Q": "unit"},
        labels={
            "w0": ("resonant angular frequency", "the resonant angular frequency is {v}"),
            "L": ("inductance", "the inductance is {v}"),
            "C": ("capacitance", "the capacitance is {v}"),
            "R": ("resistance", "the resistance is {v}"),
            "Q": ("quality factor", "the quality factor is {v}"),
        },
        base=_resonance,
        derived=lambda p: (("w0", "1/sqrt(L*C)"), ("Q", "w0*L/R")),
        dunits={"w0": "rad/s", "Q": "unit"},
        laws=("w0**2*L*C - 1",),
        variants={
            v.id: v
            for v in (
                var(
                    "w0",
                    "L C",
                    "1/sqrt(L*C)",
                    "w0 = 1 / square root of (L x C)",
                    "Find the resonant angular frequency.",
                    [
                        ("ROOT_FORGOTTEN", "1/(L*C)"),
                        ("PRODUCT_NOT_INVERTED", "sqrt(L*C)"),
                        ("INDUCTANCE_UNIT_SLIP", "1/sqrt(L_r*C)"),
                        ("CAPACITANCE_UNIT_SLIP", "1/sqrt(L*C_r)"),
                    ],
                ),
                var(
                    "C",
                    "w0 L",
                    "1/(w0^2*L)",
                    "w0 = 1 / square root of (L x C), so C = 1 / (w0^2 x L)",
                    "Find the capacitance.",
                    [
                        ("SQUARE_FORGOTTEN", "1/(w0*L)"),
                        ("FORMULA_INVERTED", "w0^2*L"),
                        ("INDUCTANCE_UNIT_SLIP", "1/(w0^2*L_r)"),
                    ],
                    laws=("w0**2*L*C - 1",),
                    rearr="square each side of the relation, then rearrange for C",
                ),
                var(
                    "L",
                    "w0 C",
                    "1/(w0^2*C)",
                    "w0 = 1 / square root of (L x C), so L = 1 / (w0^2 x C)",
                    "Find the inductance.",
                    [
                        ("SQUARE_FORGOTTEN", "1/(w0*C)"),
                        ("FORMULA_INVERTED", "w0^2*C"),
                        ("CAPACITANCE_UNIT_SLIP", "1/(w0^2*C_r)"),
                    ],
                    laws=("w0**2*L*C - 1",),
                    rearr="square each side of the relation, then rearrange for L",
                ),
                var(
                    "Q",
                    "w0 L R",
                    "w0*L/R",
                    "Q = w0 x L / R",
                    "Find the quality factor.",
                    [
                        ("FORMULA_INVERTED", "R/(w0*L)"),
                        ("INDUCTANCE_UNIT_SLIP", "w0*L_r/R"),
                        ("RESISTANCE_MULTIPLIED", "w0*L*R"),
                    ],
                    laws=("Q*R - w0*L",),
                ),
                var(
                    "R",
                    "Q w0 L",
                    "w0*L/Q",
                    "Q = w0 x L / R",
                    "Find the resistance.",
                    [
                        ("FORMULA_INVERTED", "Q/(w0*L)"),
                        ("MULTIPLIED_NOT_DIVIDED", "w0*L*Q"),
                        ("INDUCTANCE_UNIT_SLIP", "w0*L_r/Q"),
                    ],
                    laws=("Q*R - w0*L",),
                ),
            )
        },
    ),
    "Find the resonant frequency of a series LCR circuit, or its capacitance, inductance or quality factor",
    (P + "REARRANGE_FORMULA", P + "UNIT_PREFIXES", "PHY.C12.AC.REACTANCE"),
)

TRANSFORMER = reg(
    model(
        "AC.TRANSFORMER",
        "AC",
        "ideal_transformer",
        "an ideal transformer",
        syms={"Vp": "V", "Vs": "V", "Np": "unit", "Ns": "unit", "I1": "A", "I2": "A"},
        labels={
            "Vp": ("primary voltage", "the primary voltage is {v}"),
            "Vs": ("secondary voltage", "the secondary voltage is {v}"),
            "Np": ("primary turns", "the number of primary turns is {v}"),
            "Ns": ("secondary turns", "the number of secondary turns is {v}"),
            "I1": ("primary current", "the primary current is {v}"),
            "I2": ("secondary current", "the secondary current is {v}"),
        },
        base=bases(
            {"Vp": ("Vp", "V"), "Np": ("Np", "unit"), "Ns": ("Ns", "unit"), "I1": ("Ip", "A")}
        ),
        derived=lambda p: (("Vs", "Vp*Ns/Np"), ("I2", "I1*Np/Ns")),
        dunits={"Vs": "V", "I2": "A"},
        laws=("Vs*Np - Vp*Ns",),
        variants={
            v.id: v
            for v in (
                var(
                    "Vs",
                    "Vp Np Ns",
                    "Vp*Ns/Np",
                    "Vs / Vp = Ns / Np",
                    "Find the secondary voltage.",
                    [
                        ("TURNS_RATIO_INVERTED", "Vp*Np/Ns"),
                        ("TURNS_ADDED", "Vp+Ns-Np"),
                        ("PRIMARY_TURNS_ONLY", "Vp/Np"),
                        ("TURNS_NOT_DIVIDED", "Vp*Ns"),
                    ],
                    laws=("Vs*Np - Vp*Ns",),
                ),
                var(
                    "Ns",
                    "Vp Vs Np",
                    "Np*Vs/Vp",
                    "Vs / Vp = Ns / Np",
                    "Find the number of secondary turns.",
                    [
                        ("TURNS_RATIO_INVERTED", "Np*Vp/Vs"),
                        ("VOLTAGE_NOT_DIVIDED", "Np*Vs"),
                        ("VOLTAGES_SUBTRACTED", "Np+Vs-Vp"),
                    ],
                    laws=("Vs*Np - Vp*Ns",),
                ),
                var(
                    "Np",
                    "Vp Vs Ns",
                    "Ns*Vp/Vs",
                    "Vs / Vp = Ns / Np",
                    "Find the number of primary turns.",
                    [
                        ("TURNS_RATIO_INVERTED", "Ns*Vs/Vp"),
                        ("VOLTAGE_NOT_DIVIDED", "Ns*Vp"),
                        ("VOLTAGES_SUBTRACTED", "Ns+Vp-Vs"),
                    ],
                    laws=("Vs*Np - Vp*Ns",),
                ),
                var(
                    "I2",
                    "I1 Np Ns",
                    "I1*Np/Ns",
                    "an ideal transformer has Vp x I1 = Vs x I2, so I2 = I1 x Np / Ns",
                    "Find the secondary current.",
                    [
                        ("VOLTAGE_RATIO_USED_FOR_CURRENT", "I1*Ns/Np"),
                        ("CURRENT_NOT_TRANSFORMED", "I1"),
                        ("TURNS_NOT_DIVIDED", "I1*Np"),
                        ("TURNS_ADDED", "I1+Np-Ns"),
                    ],
                    laws=("I2*Ns - I1*Np",),
                ),
                var(
                    "I1",
                    "I2 Np Ns",
                    "I2*Ns/Np",
                    "an ideal transformer has Vp x I1 = Vs x I2, so I1 = I2 x Ns / Np",
                    "Find the primary current.",
                    [
                        ("VOLTAGE_RATIO_USED_FOR_CURRENT", "I2*Np/Ns"),
                        ("TURNS_NOT_DIVIDED", "I2*Ns"),
                        ("CURRENT_NOT_TRANSFORMED", "I2"),
                    ],
                    laws=("I2*Ns - I1*Np",),
                ),
            )
        },
    ),
    "Use the turns ratio of an ideal transformer for voltages and currents",
    (P + "RATIO_PROPORTION", P + "REARRANGE_FORMULA", "PHY.C12.AC.REACTANCE"),
)

# ---------------------------------------------------------------- electromagnetic waves
EM_WAVE = reg(
    model(
        "EMW.EM_WAVE",
        "EMW",
        "wave_speed_field_ratio",
        "a plane electromagnetic wave in vacuum",
        syms={"f": "Hz", "lam": "m", "c": "m/s", "E0": "V/m", "B0": "T"},
        labels={
            "f": ("frequency", "the frequency is {v}"),
            "lam": ("wavelength", "the wavelength is {v}"),
            "E0": ("electric amplitude", "the amplitude of the electric field is {v}"),
            "B0": ("magnetic amplitude", "the amplitude of the magnetic field is {v}"),
        },
        base=bases({"f": ("f", "MHz"), "E0": ("E0", "V/m")}),
        derived=lambda p: (("lam", "c/f"), ("B0", "E0/c")),
        dunits={"lam": "m", "B0": "nT"},
        consts={"c": "c_light"},
        laws=("c - f*lam",),
        variants={
            v.id: v
            for v in (
                var(
                    "lam",
                    "f",
                    "c/f",
                    "c = f x wavelength",
                    "Find the wavelength.",
                    [
                        ("MULTIPLIED_NOT_DIVIDED", "c*f"),
                        ("FORMULA_INVERTED", "f/c"),
                        ("FREQUENCY_UNIT_SLIP", "c/f_r"),
                    ],
                    laws=("c - f*lam",),
                    rearr="divide each side by the frequency",
                ),
                var(
                    "f",
                    "lam",
                    "c/lam",
                    "c = f x wavelength",
                    "Find the frequency.",
                    [
                        ("MULTIPLIED_NOT_DIVIDED", "c*lam"),
                        ("FORMULA_INVERTED", "lam/c"),
                        ("SPEED_FORGOTTEN", "1/lam"),
                    ],
                    laws=("c - f*lam",),
                    rearr="divide each side by the wavelength",
                ),
                var(
                    "B0",
                    "E0",
                    "E0/c",
                    "E0 / B0 = c",
                    "Find the amplitude of the magnetic field.",
                    [
                        ("MULTIPLIED_NOT_DIVIDED", "E0*c"),
                        ("FORMULA_INVERTED", "c/E0"),
                        ("SPEED_UNIT_SLIP", "E0/(c/1000)"),
                    ],
                    laws=("E0 - c*B0",),
                    rearr="divide each side by c",
                ),
                var(
                    "E0",
                    "B0",
                    "c*B0",
                    "E0 / B0 = c",
                    "Find the amplitude of the electric field.",
                    [
                        ("DIVIDED_NOT_MULTIPLIED", "B0/c"),
                        ("FORMULA_INVERTED", "1/(c*B0)"),
                        ("SPEED_UNIT_SLIP", "c*B0/1000"),
                    ],
                    laws=("E0 - c*B0",),
                ),
            )
        },
    ),
    "Relate frequency and wavelength, and the electric and magnetic amplitudes, of an electromagnetic wave",
    (P + "SCI_NOTATION", P + "REARRANGE_FORMULA", P + "UNIT_PREFIXES"),
)
