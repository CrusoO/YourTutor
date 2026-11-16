# ruff: noqa: E501
"""CBSE Class 10 Electricity: the models (relations, variants, named wrong procedures, wording).

All wording is original. Closed forms are over SI values. A wrong procedure is a pair
(misconception id, expression); see model.py for the expression conventions.
"""

from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction
from typing import Any

from app.factory.lanes.physics.model import Model, Variant
from app.factory.lanes.physics.quantities import to_si

CH = "cbse.10.physics.electricity"
E = "PHY.MC.ELEC."
INV, MULT, DIVE, ADD = (
    E + "FORMULA_INVERTED",
    E + "MULTIPLIED_NOT_DIVIDED",
    E + "DIVIDED_NOT_MULTIPLIED",
    E + "ADDED_NOT_MULTIPLIED",
)  # noqa: E501
TIME, SERPAR, PARADD, RECIP = (
    E + "TIME_UNIT_SLIP",
    E + "SERIES_PARALLEL_SWAPPED",
    E + "PARALLEL_RESISTANCES_ADDED",
    E + "FORGOT_FINAL_RECIPROCAL",
)  # noqa: E501
AVG, TWO, SQI, SQV = (
    E + "PARALLEL_AVERAGED",
    E + "TWO_RESISTOR_SHORTCUT_ON_THREE",
    E + "CURRENT_NOT_SQUARED",
    E + "VOLTAGE_NOT_SQUARED",
)  # noqa: E501
PVI, ROOT, AREA, AREAU = (
    E + "POWER_AS_V_OVER_I",
    E + "ROOT_FORGOTTEN",
    E + "AREA_DIRECT_NOT_INVERSE",
    E + "AREA_UNIT_SLIP",
)  # noqa: E501
ONLYL, DIAM, SHARE, EQUAL = (
    E + "ONLY_LENGTH_COUNTED",
    E + "DIAMETER_AS_AREA",
    E + "SERIES_VOLTAGE_NOT_SHARED",
    E + "EQUAL_SHARE_ASSUMED",
)  # noqa: E501
ONER, LEFT, WRONGR, NOSPLIT = (
    E + "ONE_RESISTOR_ONLY",
    E + "RESISTOR_LEFT_OUT",
    E + "WRONG_RESISTOR_USED",
    E + "CURRENT_NOT_SPLIT",
)  # noqa: E501
ELE, TEN, TLEFT, DLEFT = (
    E + "ELECTRON_CHARGE_MISUSE",
    E + "POWER_OF_TEN_SLIP",
    E + "TIME_LEFT_OUT",
    E + "DAYS_LEFT_OUT",
)  # noqa: E501
ONEAPP, WQSQ, PFORM, PDMIX = (
    E + "ONE_APPLIANCE_ONLY",
    E + "WRONG_QUANTITY_SQUARED",
    E + "POWER_FORMULA_MISMATCH",
    E + "PD_FORMULA_MIXED",
)  # noqa: E501
CHARGE_NOT_DIV = E + "CHARGE_NOT_DIVIDED_BY_E"
PREFIX = E + "UNIT_PREFIX_SLIP"


def _bases(spec: Mapping[str, tuple[str, str]]) -> Any:
    """spec: symbol -> (value param, unit or '$unit param')."""

    def build(p: Mapping[str, Any]) -> tuple[dict[str, Fraction], dict[str, str]]:
        si: dict[str, Fraction] = {}
        un: dict[str, str] = {}
        for sym, (vp, u) in spec.items():
            unit = str(p[u[1:]]) if u.startswith("$") else u
            si[sym] = to_si(p[vp], unit)
            un[sym] = unit
        return si, un

    return build


def rvals(p: Mapping[str, Any]) -> list[int]:
    return [int(x) for x in str(p["rset"]).split(",")]


def _rset_base(p: Mapping[str, Any], extra: Mapping[str, tuple[str, str]] | None = None) -> Any:
    si: dict[str, Fraction] = {}
    un: dict[str, str] = {}
    for i, r in enumerate(rvals(p), start=1):
        si[f"R{i}"] = Fraction(r)
        un[f"R{i}"] = "ohm"
    if extra:
        more_si, more_un = _bases(extra)(p)
        si.update(more_si)
        un.update(more_un)
    return si, un


def _n(p: Mapping[str, Any]) -> int:
    return len(rvals(p))


def _sum(n: int) -> str:
    return "+".join(f"R{i}" for i in range(1, n + 1))


def _par(n: int) -> str:
    return "+".join(f"1/R{i}" for i in range(1, n + 1))


# ---------------------------------------------------------------- 1. charge and current
CHARGE = Model(
    id="ELEC.CHARGE_CURRENT",
    skill="PHY.ELEC.CHARGE_CURRENT",
    chapter=CH,
    technique="charge_current_time",
    topic="charge flowing in a wire",
    syms={"Q": "C", "I": "A", "t": "s"},
    labels={
        "Q": ("charge", "the charge is {v}"),
        "I": ("current", "the current is {v}"),
        "t": ("time", "the time is {v}"),
    },
    base=_bases({"I": ("I", "$iu"), "t": ("t", "$tu")}),
    derived=lambda p: (("Q", "I*t"),),
    dunits={"Q": "C"},
    laws=("Q - I*t",),
    variants={
        "Q_from_It": Variant(
            "Q_from_It",
            "Q",
            ("I", "t"),
            "I*t",
            ("1", "I*t"),
            "charge Q = current I x time t",
            "How much charge flows?",
            ((INV, "I/t"), (TIME, "I*t_r"), (PREFIX, "I_r*t"), (ADD, "I+t")),
        ),
        "I_from_Qt": Variant(
            "I_from_Qt",
            "I",
            ("Q", "t"),
            "Q/t",
            ("t", "Q"),
            "charge Q = current I x time t",
            "What is the current?",
            ((MULT, "Q*t"), (INV, "t/Q"), (TIME, "Q/t_r"), (DIVE, "Q-t")),
            rearr="divide each side of Q = I x t by t",
        ),
        "t_from_QI": Variant(
            "t_from_QI",
            "t",
            ("Q", "I"),
            "Q/I",
            ("I", "Q"),
            "charge Q = current I x time t",
            "For how long does the current flow?",
            ((MULT, "Q*I"), (INV, "I/Q"), (PREFIX, "Q/I_r"), (DIVE, "Q-I")),
            rearr="divide each side of Q = I x t by I",
        ),
    },
    sizes={"I": (Fraction(1, 1000), Fraction(20)), "t": (Fraction(1), Fraction(7200))},
)

COUNT = Model(
    id="ELEC.CHARGE_COUNT",
    skill="PHY.ELEC.CHARGE_COUNT",
    chapter=CH,
    technique="charge_quantisation",
    topic="electrons passing a point in a wire",
    syms={"N": "unit", "I": "A", "t": "s", "e": "C"},
    labels={
        "N": ("number of electrons", "the number of electrons is {v}"),
        "I": ("current", "the current is {v}"),
        "t": ("time", "the time is {v}"),
    },
    base=_bases({"I": ("I", "A"), "t": ("t", "s")}),
    derived=lambda p: (("N", "I*t/e"),),
    dunits={"N": "unit"},
    consts={"e": "e_charge"},
    laws=("N*e - I*t",),
    variants={
        "N_from_It": Variant(
            "N_from_It",
            "N",
            ("I", "t"),
            "I*t/e",
            ("e", "I*t"),
            "charge Q = I x t, and Q = N x e, so N = I x t / e",
            "How many electrons pass a point of the wire in this time?",
            ((ELE, "I*t*e"), (CHARGE_NOT_DIV, "I*t"), (TEN, "@K*10"), (TEN, "@K/10")),
            rearr="divide each side of Q = N x e by e",
            laws=("N*e - I*t",),
        ),
        "t_from_NI": Variant(
            "t_from_NI",
            "t",
            ("N", "I"),
            "N*e/I",
            ("I", "N*e"),
            "charge Q = N x e, and Q = I x t, so t = N x e / I",
            "How long does this many electrons take to pass?",
            ((ELE, "N/(I*e)"), (CHARGE_NOT_DIV, "N/I"), (INV, "I/(N*e)"), (TEN, "@K*10")),
            rearr="divide each side of I x t = N x e by I",
            laws=("N*e - I*t",),
            forms=("num2", "num3", "case4"),
        ),
    },
)

POTDIFF = Model(
    id="ELEC.POT_DIFF",
    skill="PHY.ELEC.POT_DIFF",
    chapter=CH,
    technique="potential_difference",
    topic="work done in moving charge",
    syms={"V": "V", "W": "J", "Q": "C"},
    labels={
        "V": ("potential difference", "the potential difference is {v}"),
        "W": ("work done", "the work done is {v}"),
        "Q": ("charge", "the charge moved is {v}"),
    },
    base=_bases({"V": ("V", "V"), "Q": ("Q", "C")}),
    derived=lambda p: (("W", "V*Q"),),
    dunits={"W": "J"},
    laws=("V*Q - W",),
    variants={
        "V_from_WQ": Variant(
            "V_from_WQ",
            "V",
            ("W", "Q"),
            "W/Q",
            ("Q", "W"),
            "potential difference V = work done W / charge Q",
            "Find the potential difference.",
            ((PDMIX, "W*Q"), (INV, "Q/W"), (ADD, "W+Q")),
            rearr=None,
        ),
        "W_from_VQ": Variant(
            "W_from_VQ",
            "W",
            ("V", "Q"),
            "V*Q",
            ("1", "V*Q"),
            "V = W / Q, so W = V x Q",
            "How much work is done?",
            ((DIVE, "V/Q"), (INV, "Q/V"), (ADD, "V+Q")),
            rearr="multiply each side of V = W / Q by Q",
        ),
        "Q_from_WV": Variant(
            "Q_from_WV",
            "Q",
            ("W", "V"),
            "W/V",
            ("V", "W"),
            "V = W / Q, so Q = W / V",
            "How much charge is moved?",
            ((MULT, "W*V"), (INV, "V/W"), (ADD, "W+V")),
            rearr="multiply each side of V = W / Q by Q, then divide each side by V",
        ),
    },
)

# ---------------------------------------------------------------- 2. Ohm's law
OHM = Model(
    id="ELEC.OHM",
    skill="PHY.ELEC.OHM_LAW",
    chapter=CH,
    technique="ohms_law",
    topic="a resistor in a circuit",
    syms={"V": "V", "I": "A", "R": "ohm"},
    labels={
        "V": ("potential difference", "the potential difference across it is {v}"),
        "I": ("current", "the current through it is {v}"),
        "R": ("resistance", "its resistance is {v}"),
    },
    base=_bases({"I": ("I", "$iu"), "R": ("R", "$ru")}),
    derived=lambda p: (("V", "I*R"),),
    dunits={"V": "V"},
    laws=("V - I*R",),
    variants={
        "V_from_IR": Variant(
            "V_from_IR",
            "V",
            ("I", "R"),
            "I*R",
            ("1", "I*R"),
            "V = I x R",
            "Find the potential difference across the resistor.",
            ((INV, "I/R"), (PREFIX, "I_r*R_r"), (ADD, "I+R"), (DIVE, "R/I")),
        ),
        "I_from_VR": Variant(
            "I_from_VR",
            "I",
            ("V", "R"),
            "V/R",
            ("R", "V"),
            "V = I x R",
            "Find the current through the resistor.",
            ((MULT, "V*R"), (INV, "R/V"), (PREFIX, "V/R_r"), (ADD, "V-R")),
            rearr="divide each side of V = I x R by R",
        ),
        "R_from_VI": Variant(
            "R_from_VI",
            "R",
            ("V", "I"),
            "V/I",
            ("I", "V"),
            "V = I x R",
            "Find the resistance of the resistor.",
            ((MULT, "V*I"), (INV, "I/V"), (PREFIX, "V/I_r"), (ADD, "V-I")),
            rearr="divide each side of V = I x R by I",
        ),
    },
    sizes={"R": (Fraction(1, 10), Fraction(100000)), "V": (Fraction(1, 100), Fraction(500))},
)

# ---------------------------------------------------------------- 3. resistivity
RESIST = Model(
    id="ELEC.RESISTIVITY",
    skill="PHY.ELEC.RESISTIVITY",
    chapter=CH,
    technique="resistivity",
    topic="a uniform wire",
    syms={"R": "ohm", "rho": "ohm*m", "L": "m", "A": "m^2"},
    labels={
        "R": ("resistance", "its resistance is {v}"),
        "rho": ("resistivity", "the resistivity of its material is {v}"),
        "L": ("length", "its length is {v}"),
        "A": ("cross-section area", "its cross-section area is {v}"),
    },  # noqa: E501
    base=_bases({"rho": ("rho", "ohm*m"), "L": ("L", "$lu"), "A": ("A", "$au")}),
    derived=lambda p: (("R", "rho*L/A"),),
    dunits={"R": "ohm"},
    laws=("R*A - rho*L",),
    variants={
        "R_from_rhoLA": Variant(
            "R_from_rhoLA",
            "R",
            ("rho", "L", "A"),
            "rho*L/A",
            ("A", "rho*L"),
            "R = resistivity x length / area",
            "Find the resistance of the wire.",
            ((AREA, "rho*A/L"), (AREAU, "rho*L/A_r"), (MULT, "rho*L*A"), (INV, "A/(rho*L)")),
        ),
        "L_from_RrhoA": Variant(
            "L_from_RrhoA",
            "L",
            ("R", "rho", "A"),
            "R*A/rho",
            ("rho", "R*A"),
            "R = resistivity x length / area",
            "Find the length of the wire.",
            ((AREA, "R*rho/A"), (AREAU, "R*A_r/rho"), (MULT, "R*A*rho"), (INV, "rho/(R*A)")),
            rearr="multiply each side of R = resistivity x L / A by A, then divide each side by the resistivity",
        ),  # noqa: E501
    },
)


def _scale_base(p: Mapping[str, Any]) -> tuple[dict[str, Fraction], dict[str, str]]:
    k = Fraction(str(p["k"]))
    if p["case"] == "stretch":
        kl, ka = k, 1 / k
    elif p["case"] == "diameter":
        kl, ka = Fraction(1), k * k
    else:
        raise ValueError("unknown case")
    return {"kL": kl, "kA": ka}, {"kL": "unit", "kA": "unit"}


SCALE = Model(
    id="ELEC.RESIST_SCALE",
    skill="PHY.ELEC.RESIST_FACTORS",
    chapter=CH,
    technique="resistance_proportionality",
    topic="how a wire's resistance changes",
    syms={"F": "unit", "kL": "unit", "kA": "unit"},
    labels={
        "F": ("number the resistance is multiplied by", "x"),
        "kL": ("length factor", "x"),
        "kA": ("area factor", "x"),
    },
    base=_scale_base,
    derived=lambda p: (("F", "kL/kA"),),
    dunits={"F": "unit"},
    laws=("F*kA - kL",),
    rule_derived=True,
    variants={
        "F_from_change": Variant(
            "F_from_change",
            "F",
            ("kL", "kA"),
            "kL/kA",
            ("kA", "kL"),
            "R is proportional to length and inversely proportional to area, so the new resistance divided by the old one equals the length factor divided by the area factor",  # noqa: E501
            "By what number is the resistance multiplied?",
            ((ONLYL, "kL"), (DIAM, "1/sqrt(kA)"), (INV, "kA/kL"), (AREA, "kL*kA")),
            rearr=None,
            kind="rule",
            forms=("mcq1", "num2", "num3"),
        ),
    },
)

# ---------------------------------------------------------------- 4. series and parallel
SERIES = Model(
    id="ELEC.SERIES",
    skill="PHY.ELEC.SERIES",
    chapter=CH,
    technique="series_resistors",
    topic="resistors joined in series",
    syms={"R1": "ohm", "R2": "ohm", "R3": "ohm", "Rs": "ohm"},
    labels={
        "R1": ("first resistance", "the first resistor is {v}"),
        "R2": ("second resistance", "the second resistor is {v}"),
        "R3": ("third resistance", "the third resistor is {v}"),
        "Rs": ("total resistance", "the total resistance is {v}"),
    },
    base=lambda p: _rset_base(p),
    derived=lambda p: (("Rs", _sum(_n(p))),),
    dunits={"Rs": "ohm"},
    laws=("Rs - R1 - R2 - R3",),
    variants={
        "Rs_two": Variant(
            "Rs_two",
            "Rs",
            ("R1", "R2"),
            "R1+R2",
            ("1", "R1+R2"),
            "in series the resistances add: Rs = R1 + R2",
            "Find the total resistance.",
            ((SERPAR, "R1*R2/(R1+R2)"), (MULT, "R1*R2"), (RECIP, "1/R1+1/R2"), (ONER, "R2")),
            laws=("Rs - R1 - R2",),
        ),
        "Rs_three": Variant(
            "Rs_three",
            "Rs",
            ("R1", "R2", "R3"),
            "R1+R2+R3",
            ("1", "R1+R2+R3"),
            "in series the resistances add: Rs = R1 + R2 + R3",
            "Find the total resistance.",
            (
                (SERPAR, "1/(1/R1+1/R2+1/R3)"),
                (MULT, "R1*R2*R3"),
                (RECIP, "1/R1+1/R2+1/R3"),
                (LEFT, "R1+R2"),
            ),
            laws=("Rs - R1 - R2 - R3",),
        ),
        "R2_from_Rs": Variant(
            "R2_from_Rs",
            "R2",
            ("R1", "Rs"),
            "Rs-R1",
            ("1", "Rs-R1"),
            "in series Rs = R1 + R2",
            "Find the second resistance.",
            ((ADD, "Rs+R1"), (SERPAR, "1/(1/Rs-1/R1)"), (DIVE, "Rs/R1"), (MULT, "Rs*R1")),
            rearr="subtract R1 from each side of Rs = R1 + R2",
            laws=("Rs - R1 - R2",),
        ),
        "R3_from_Rs": Variant(
            "R3_from_Rs",
            "R3",
            ("R1", "R2", "Rs"),
            "Rs-R1-R2",
            ("1", "Rs-R1-R2"),
            "in series Rs = R1 + R2 + R3",
            "Find the third resistance.",
            (
                (ADD, "Rs+R1+R2"),
                (SERPAR, "1/(1/Rs-1/R1-1/R2)"),
                (DIVE, "Rs/(R1+R2)"),
                (MULT, "Rs*R1*R2"),
            ),
            rearr="subtract R1 and R2 from each side of Rs = R1 + R2 + R3",
            laws=("Rs - R1 - R2 - R3",),
        ),
    },
)

PARALLEL = Model(
    id="ELEC.PARALLEL",
    skill="PHY.ELEC.PARALLEL",
    chapter=CH,
    technique="parallel_resistors",
    topic="resistors joined in parallel",
    syms={"R1": "ohm", "R2": "ohm", "R3": "ohm", "Rp": "ohm"},
    labels={**SERIES.labels, "Rp": ("total resistance", "the combined resistance is {v}")},
    base=lambda p: _rset_base(p),
    derived=lambda p: (("Rp", f"1/({_par(_n(p))})"),),
    dunits={"Rp": "ohm"},
    laws=("1/Rp - 1/R1 - 1/R2 - 1/R3",),
    variants={
        "Rp_two": Variant(
            "Rp_two",
            "Rp",
            ("R1", "R2"),
            "R1*R2/(R1+R2)",
            ("R1+R2", "R1*R2"),
            "in parallel the reciprocals add: 1/Rp = 1/R1 + 1/R2",
            "Find the combined resistance.",
            ((PARADD, "R1+R2"), (RECIP, "1/R1+1/R2"), (AVG, "(R1+R2)/2"), (MULT, "R1*R2")),
            laws=("1/Rp - 1/R1 - 1/R2",),
        ),
        "Rp_three": Variant(
            "Rp_three",
            "Rp",
            ("R1", "R2", "R3"),
            "1/(1/R1+1/R2+1/R3)",
            ("1/R1+1/R2+1/R3", "1"),
            "in parallel the reciprocals add: 1/Rp = 1/R1 + 1/R2 + 1/R3",
            "Find the combined resistance.",
            (
                (PARADD, "R1+R2+R3"),
                (RECIP, "1/R1+1/R2+1/R3"),
                (TWO, "R1*R2/(R1+R2)"),
                (AVG, "(R1+R2+R3)/3"),
            ),
        ),
        "R2_from_Rp": Variant(
            "R2_from_Rp",
            "R2",
            ("R1", "Rp"),
            "1/(1/Rp-1/R1)",
            ("R1-Rp", "Rp*R1"),
            "1/Rp = 1/R1 + 1/R2",
            "Find the second resistance.",
            ((ADD, "Rp+R1"), (MULT, "Rp*R1"), (RECIP, "1/Rp-1/R1"), (AVG, "2*Rp-R1")),
            rearr="subtract 1/R1 from each side of 1/Rp = 1/R1 + 1/R2, then take the reciprocal of each side",  # noqa: E501
            laws=("1/Rp - 1/R1 - 1/R2",),
        ),
        "R3_from_Rp": Variant(
            "R3_from_Rp",
            "R3",
            ("R1", "R2", "Rp"),
            "1/(1/Rp-1/R1-1/R2)",
            ("1/Rp-1/R1-1/R2", "1"),
            "1/Rp = 1/R1 + 1/R2 + 1/R3",
            "Find the third resistance.",
            ((ADD, "Rp+R1+R2"), (RECIP, "1/Rp-1/R1-1/R2"), (AVG, "3*Rp-R1-R2"), (MULT, "Rp*R1*R2")),
            rearr="subtract 1/R1 and 1/R2 from each side of 1/Rp = 1/R1 + 1/R2 + 1/R3, then take the reciprocal of each side",  # noqa: E501
            laws=("1/Rp - 1/R1 - 1/R2 - 1/R3",),
        ),
    },
)

# ---------------------------------------------------------------- 5. circuits with a source
SCIRC = Model(
    id="ELEC.SERIES_CIRCUIT",
    skill="PHY.ELEC.SERIES_CIRCUIT",
    chapter=CH,
    technique="series_circuit",
    topic="a battery connected to resistors in series",
    syms={"V": "V", "V2": "V", "I": "A", "R1": "ohm", "R2": "ohm", "R3": "ohm"},
    labels={
        "V": ("battery voltage", "the battery gives {v}"),
        "I": ("current", "the current is {v}"),
        "V2": (
            "potential difference across the second resistor",
            "the potential difference across the second resistor is {v}",
        ),  # noqa: E501
        "R1": ("first resistance", "the first resistor is {v}"),
        "R2": ("second resistance", "the second resistor is {v}"),
        "R3": ("third resistance", "the third resistor is {v}"),
    },
    base=lambda p: _rset_base(p, {"I": ("I", "A")}),
    derived=lambda p: (("V", f"I*({_sum(_n(p))})"), ("V2", "I*R2")),
    dunits={"V": "V", "V2": "V"},
    laws=("V - I*(R1+R2+R3)", "V2 - I*R2"),
    variants={
        "I_two": Variant(
            "I_two",
            "I",
            ("V", "R1", "R2"),
            "V/(R1+R2)",
            ("R1+R2", "V"),
            "the same current flows through every resistor in series: I = V / (R1 + R2)",
            "Find the current in the circuit.",
            ((ONER, "V/R1"), (MULT, "V*(R1+R2)"), (SERPAR, "V*(1/R1+1/R2)"), (INV, "(R1+R2)/V")),
            rearr="divide each side of V = I x (R1 + R2) by (R1 + R2)",
            laws=("V - I*(R1+R2)",),
            forms=("num2", "num3", "case4"),
        ),
        "I_three": Variant(
            "I_three",
            "I",
            ("V", "R1", "R2", "R3"),
            "V/(R1+R2+R3)",
            ("R1+R2+R3", "V"),
            "the same current flows through every resistor in series",
            "Find the current in the circuit.",
            (
                (ONER, "V/R1"),
                (MULT, "V*(R1+R2+R3)"),
                (SERPAR, "V*(1/R1+1/R2+1/R3)"),
                (INV, "(R1+R2+R3)/V"),
            ),
            rearr="divide each side of V = I x (R1 + R2 + R3) by (R1 + R2 + R3)",
            laws=("V - I*(R1+R2+R3)",),
            forms=("num3", "case4"),
        ),
        "V2_two": Variant(
            "V2_two",
            "V2",
            ("V", "R1", "R2"),
            "V*R2/(R1+R2)",
            ("R1+R2", "V*R2"),
            "find the current from the whole circuit, then use V = I x R on one resistor",
            "Find the potential difference across the second resistor.",
            ((SHARE, "V"), (EQUAL, "V/2"), (WRONGR, "V*R1/(R1+R2)"), (ONER, "V/R2")),
            laws=("V - I*(R1+R2)", "V2 - I*R2"),
            forms=("num3", "case4"),
        ),
        "V2_three": Variant(
            "V2_three",
            "V2",
            ("V", "R1", "R2", "R3"),
            "V*R2/(R1+R2+R3)",
            ("R1+R2+R3", "V*R2"),
            "find the current from the whole circuit, then use V = I x R on one resistor",
            "Find the potential difference across the second resistor.",
            (
                (SHARE, "V"),
                (EQUAL, "V/3"),
                (WRONGR, "V*R1/(R1+R2+R3)"),
                (WRONGR, "V*(R2+R3)/(R1+R2+R3)"),
            ),
            laws=("V - I*(R1+R2+R3)", "V2 - I*R2"),
            forms=("case4",),
        ),
    },
)

PCIRC = Model(
    id="ELEC.PARALLEL_CIRCUIT",
    skill="PHY.ELEC.PARALLEL_CIRCUIT",
    chapter=CH,
    technique="parallel_circuit",
    topic="a battery connected to resistors in parallel",
    syms={
        "V": "V",
        "It": "A",
        "I1": "A",
        "I2": "A",
        "I3": "A",
        "R1": "ohm",
        "R2": "ohm",
        "R3": "ohm",
    },
    labels={
        "V": ("battery voltage", "the battery gives {v}"),
        "It": ("total current", "the total current from the battery is {v}"),
        "I2": ("current in the second resistor", "the current in the second resistor is {v}"),
        "R1": ("first resistance", "the first resistor is {v}"),
        "R2": ("second resistance", "the second resistor is {v}"),
        "R3": ("third resistance", "the third resistor is {v}"),
    },
    base=lambda p: _rset_base(p, {"V": ("V", "V")}),
    derived=lambda p: (("It", "+".join(f"V/R{i}" for i in range(1, _n(p) + 1))), ("I2", "V/R2")),
    dunits={"It": "A", "I2": "A"},
    laws=("V - I1*R1", "V - I2*R2", "It - I1 - I2"),
    variants={
        "It_two": Variant(
            "It_two",
            "It",
            ("V", "R1", "R2"),
            "V/R1+V/R2",
            ("R1*R2", "V*(R1+R2)"),
            "each branch has the full battery voltage: I = V / R for each, and the branch currents add",  # noqa: E501
            "Find the total current drawn from the battery.",
            ((ONER, "V/R1"), (SERPAR, "V/(R1+R2)"), (MULT, "V*(R1+R2)"), (ONER, "V/R2")),
            laws=("V - I1*R1", "V - I2*R2", "It - I1 - I2"),
            forms=("num2", "num3", "case4"),
        ),
        "It_three": Variant(
            "It_three",
            "It",
            ("V", "R1", "R2", "R3"),
            "V/R1+V/R2+V/R3",
            ("R1*R2*R3", "V*(R2*R3+R1*R3+R1*R2)"),
            "each branch has the full battery voltage: I = V / R for each, and the branch currents add",  # noqa: E501
            "Find the total current drawn from the battery.",
            ((ONER, "V/R1"), (SERPAR, "V/(R1+R2+R3)"), (MULT, "V*(R1+R2+R3)"), (LEFT, "V/R1+V/R2")),  # noqa: E501
            laws=("V - I1*R1", "V - I2*R2", "V - I3*R3", "It - I1 - I2 - I3"),
            forms=("num3", "case4"),
        ),
        "I2_split": Variant(
            "I2_split",
            "I2",
            ("It", "R1", "R2"),
            "It*R1/(R1+R2)",
            ("R1+R2", "It*R1"),
            "the branches share one voltage, so the larger resistor takes the smaller current: I1 x R1 = I2 x R2 and I1 + I2 = total",  # noqa: E501
            "Find the current in the second resistor.",
            ((EQUAL, "It/2"), (WRONGR, "It*R2/(R1+R2)"), (NOSPLIT, "It"), (ONER, "It*R1/R2")),
            laws=("It - I1 - I2", "I1*R1 - I2*R2"),
            forms=("num3", "case4"),
        ),
    },
)

MIXED = Model(
    id="ELEC.MIXED_NETWORK",
    skill="PHY.ELEC.MIXED_NETWORK",
    chapter=CH,
    technique="mixed_network",
    topic="a resistor in series with two resistors in parallel",
    syms={
        "V": "V",
        "Vp": "V",
        "I": "A",
        "I2": "A",
        "R1": "ohm",
        "R2": "ohm",
        "R3": "ohm",
        "Rp": "ohm",
        "Rt": "ohm",
    },
    labels={
        "V": ("battery voltage", "the battery gives {v}"),
        "R1": ("series resistance", "the resistor in series with the pair is {v}"),
        "R2": ("first parallel resistance", "one resistor of the parallel pair is {v}"),
        "R3": ("second parallel resistance", "the other resistor of the pair is {v}"),
        "Rt": ("total resistance", "the total resistance is {v}"),
        "I": ("battery current", "the battery current is {v}"),
        "Vp": (
            "potential difference across the pair",
            "the potential difference across the pair is {v}",
        ),  # noqa: E501
        "I2": (
            "current in the first parallel resistor",
            "the current in the first resistor of the pair is {v}",
        ),
    },  # noqa: E501
    base=lambda p: _mixed_base(p),
    derived=lambda p: (
        ("Rp", "R2*R3/(R2+R3)"),
        ("Rt", "R1+Rp"),
        ("V", "I*Rt"),
        ("Vp", "I*Rp"),
        ("I2", "Vp/R2"),
    ),
    dunits={"V": "V", "Vp": "V", "I2": "A", "Rt": "ohm"},
    laws=("Rp*(R2+R3) - R2*R3", "Rt - R1 - Rp", "V - I*Rt", "Vp - I*Rp", "Vp - I2*R2"),
    variants={
        "Rt_mixed": Variant(
            "Rt_mixed",
            "Rt",
            ("R1", "R2", "R3"),
            "R1+R2*R3/(R2+R3)",
            ("R2+R3", "R1*(R2+R3)+R2*R3"),
            "combine the parallel pair first (1/Rp = 1/R2 + 1/R3), then add the series resistor",
            "Find the total resistance of the network.",
            (
                (PARADD, "R1+R2+R3"),
                (SERPAR, "1/(1/R1+1/R2+1/R3)"),
                (RECIP, "R1+1/R2+1/R3"),
                (AVG, "R1+(R2+R3)/2"),
            ),
            laws=("Rp*(R2+R3) - R2*R3", "Rt - R1 - Rp"),
            forms=("num3", "case4"),
        ),
        "I_mixed": Variant(
            "I_mixed",
            "I",
            ("V", "R1", "R2", "R3"),
            "V/(R1+R2*R3/(R2+R3))",
            ("R1*(R2+R3)+R2*R3", "V*(R2+R3)"),
            "find the total resistance first, then use V = I x R for the whole network",
            "Find the current drawn from the battery.",
            (
                (PARADD, "V/(R1+R2+R3)"),
                (ONER, "V/R1"),
                (SERPAR, "V*(1/R1+1/R2+1/R3)"),
                (AVG, "V/(R1+(R2+R3)/2)"),
            ),
            laws=("Rp*(R2+R3) - R2*R3", "Rt - R1 - Rp", "V - I*Rt"),
            forms=("case4",),
        ),
        "Vp_mixed": Variant(
            "Vp_mixed",
            "Vp",
            ("V", "R1", "R2", "R3"),
            "V*R2*R3/(R1*(R2+R3)+R2*R3)",
            ("R1*(R2+R3)+R2*R3", "V*R2*R3"),
            "find the battery current, then use V = I x R on the parallel pair alone",
            "Find the potential difference across the parallel pair.",
            (
                (SHARE, "V"),
                (EQUAL, "V/2"),
                (WRONGR, "V*R1*(R2+R3)/(R1*(R2+R3)+R2*R3)"),
                (PARADD, "V*(R2+R3)/(R1+R2+R3)"),
            ),
            laws=("Rp*(R2+R3) - R2*R3", "Rt - R1 - Rp", "V - I*Rt", "Vp - I*Rp"),
            forms=("case4",),
        ),
        "I2_mixed": Variant(
            "I2_mixed",
            "I2",
            ("V", "R1", "R2", "R3"),
            "V*R3/(R1*(R2+R3)+R2*R3)",
            ("R1*(R2+R3)+R2*R3", "V*R3"),
            "find the voltage across the pair, then divide by the resistor of interest",
            "Find the current in the first resistor of the pair.",
            (
                (NOSPLIT, "V/(R1+R2*R3/(R2+R3))"),
                (EQUAL, "V/(R1+R2*R3/(R2+R3))/2"),
                (ONER, "V/R2"),
                (WRONGR, "V*R2/(R1*(R2+R3)+R2*R3)"),
            ),
            laws=("Rp*(R2+R3) - R2*R3", "Rt - R1 - Rp", "V - I*Rt", "Vp - I*Rp", "Vp - I2*R2"),
            forms=("case4",),
        ),
    },
)


def _mixed_base(p: Mapping[str, Any]) -> tuple[dict[str, Fraction], dict[str, str]]:
    r2, r3 = (int(x) for x in str(p["pair"]).split(","))
    si = {
        "R1": Fraction(str(p["R1"])),
        "R2": Fraction(r2),
        "R3": Fraction(r3),
        "I": Fraction(str(p["I"])),
    }
    return si, {"R1": "ohm", "R2": "ohm", "R3": "ohm", "I": "A"}


# ---------------------------------------------------------------- 6. power, energy, heating
_PW_LAWS = ("P - V*I", "V - I*R")
POWER = Model(
    id="ELEC.POWER",
    skill="PHY.ELEC.POWER",
    chapter=CH,
    technique="electric_power",
    topic="an electrical appliance",
    syms={"P": "W", "V": "V", "I": "A", "R": "ohm"},
    labels={
        "P": ("power", "its power is {v}"),
        "V": ("voltage", "the voltage across it is {v}"),
        "I": ("current", "the current through it is {v}"),
        "R": ("resistance", "its resistance is {v}"),
    },
    base=_bases({"I": ("I", "A"), "R": ("R", "ohm")}),
    derived=lambda p: (("V", "I*R"), ("P", "I*I*R")),
    dunits={"P": "W", "V": "V"},
    laws=_PW_LAWS,
    sizes={"V": (Fraction(1, 10), Fraction(500)), "P": (Fraction(1), Fraction(5000))},
    variants={
        "P_from_VI": Variant(
            "P_from_VI",
            "P",
            ("V", "I"),
            "V*I",
            ("1", "V*I"),
            "P = V x I",
            "Find the power.",
            ((PVI, "V/I"), (ADD, "V+I"), (INV, "I/V")),
            laws=("P - V*I",),
            forms=("mcq1", "num2"),
        ),
        "P_from_IR": Variant(
            "P_from_IR",
            "P",
            ("I", "R"),
            "I*I*R",
            ("1", "I^2*R"),
            "P = I x I x R (from P = V x I and V = I x R)",
            "Find the power.",
            ((SQI, "I*R"), (PFORM, "I^2/R"), (WQSQ, "(I*R)^2"), (INV, "R/I^2")),
            laws=_PW_LAWS,
        ),
        "P_from_VR": Variant(
            "P_from_VR",
            "P",
            ("V", "R"),
            "V*V/R",
            ("R", "V^2"),
            "P = V x V / R (from P = V x I and I = V / R)",
            "Find the power.",
            ((SQV, "V/R"), (MULT, "V*R"), (INV, "R/V^2"), (PFORM, "V^2*R")),
            laws=("P*R - V**2",),
        ),
        "I_from_PV": Variant(
            "I_from_PV",
            "I",
            ("P", "V"),
            "P/V",
            ("V", "P"),
            "P = V x I",
            "Find the current drawn.",
            ((MULT, "P*V"), (INV, "V/P"), (PFORM, "P/V^2"), (ADD, "P-V")),
            rearr="divide each side of P = V x I by V",
            laws=("P - V*I",),
        ),
        "R_from_VP": Variant(
            "R_from_VP",
            "R",
            ("V", "P"),
            "V*V/P",
            ("P", "V^2"),
            "P = V x V / R",
            "Find the resistance of the appliance.",
            ((SQV, "V/P"), (MULT, "V^2*P"), (INV, "P/V^2"), (PFORM, "P/V")),
            rearr="multiply each side of P = V x V / R by R, then divide each side by P",
            laws=("P*R - V**2",),
            forms=("num2", "num3", "case4"),
        ),
        "I_from_PR": Variant(
            "I_from_PR",
            "I",
            ("P", "R"),
            "sqrt(P/R)",
            ("1", "sqrt(P/R)"),
            "P = I x I x R",
            "Find the current.",
            ((ROOT, "P/R"), (PFORM, "sqrt(R/P)"), (MULT, "P*R"), (WQSQ, "P/R^2")),
            rearr="divide each side of P = I x I x R by R, then take the square root of each side",
            laws=("P - I**2*R",),
            forms=("num3", "case4"),
        ),
    },
)

PSCALE = Model(
    id="ELEC.POWER_SCALE",
    skill="PHY.ELEC.POWER_SCALING",
    chapter=CH,
    technique="power_proportionality",
    topic="how power changes when a quantity changes",
    syms={
        "kV": "unit",
        "kI": "unit",
        "kR": "unit",
        "kt": "unit",
        "FV": "unit",
        "FR": "unit",
        "FI": "unit",
        "FVR": "unit",
        "FH": "unit",
    },
    labels={
        **{s: ("factor", "x") for s in ("kV", "kI", "kR", "kt")},
        **{s: ("number the power is multiplied by", "x") for s in ("FV", "FR", "FI", "FVR")},
        "FH": ("number the heat is multiplied by", "x"),
    },
    base=lambda p: (
        {
            "kV": Fraction(str(p["k"])),
            "kI": Fraction(str(p["k"])),
            "kR": Fraction(str(p["k2"])),
            "kt": Fraction(str(p["k2"])),
        },
        {"kV": "unit", "kI": "unit", "kR": "unit", "kt": "unit"},
    ),
    derived=lambda p: (
        ("FV", "kV^2"),
        ("FR", "1/kR"),
        ("FI", "kI^2"),
        ("FVR", "kV^2/kR"),
        ("FH", "kI^2*kt"),
    ),
    dunits={s: "unit" for s in ("FV", "FR", "FI", "FVR", "FH")},
    rule_derived=True,
    laws=(),
    variants={
        "P_V_scaled": Variant(
            "P_V_scaled",
            "FV",
            ("kV",),
            "kV^2",
            ("1", "kV^2"),
            "for a fixed resistor P = V x V / R, so P changes with the square of V",
            "By what number is the power multiplied?",
            (
                (E + "POWER_SCALES_LINEARLY", "kV"),
                (INV, "1/kV^2"),
                (E + "POWER_SCALES_LINEARLY", "kV*2"),
                (E + "POWER_SCALES_LINEARLY", "kV^2*kV"),
            ),
            laws=("FV - kV**2",),
            kind="rule",
            forms=("mcq1", "num2"),
        ),
        "P_R_scaled": Variant(
            "P_R_scaled",
            "FR",
            ("kR",),
            "1/kR",
            ("kR", "1"),
            "at a fixed voltage P = V x V / R, so P is inversely proportional to R",
            "By what number is the power multiplied?",
            ((E + "POWER_SCALES_LINEARLY", "kR"), (INV, "kR^2"), (SQV, "1/kR^2")),
            kind="rule",
            laws=("FR*kR - 1",),
            forms=("mcq1", "num2"),
        ),
        "P_I_scaled": Variant(
            "P_I_scaled",
            "FI",
            ("kI",),
            "kI^2",
            ("1", "kI^2"),
            "for a fixed resistor P = I x I x R, so P changes with the square of I",
            "By what number is the power multiplied?",
            ((E + "POWER_SCALES_LINEARLY", "kI"), (INV, "1/kI^2"), (SQI, "kI*2"), (SQI, "kI^3")),
            kind="rule",
            laws=("FI - kI**2",),
            forms=("mcq1", "num2"),
        ),
        "P_VR_scaled": Variant(
            "P_VR_scaled",
            "FVR",
            ("kV", "kR"),
            "kV^2/kR",
            ("kR", "kV^2"),
            "P = V x V / R, so combine the effect of V, which is squared, with the effect of R, which is inverse",
            "By what number is the power multiplied?",
            (
                (E + "POWER_SCALES_LINEARLY", "kV/kR"),
                (SQV, "kV*kR"),
                (INV, "kR/kV^2"),
                (SQV, "kV^2*kR"),
            ),
            kind="rule",
            laws=("FVR*kR - kV**2",),
            forms=("num2", "num3"),
        ),
        "H_It_scaled": Variant(
            "H_It_scaled",
            "FH",
            ("kI", "kt"),
            "kI^2*kt",
            ("1", "kI^2*kt"),
            "heat H = I x I x R x t: it changes with the square of I and directly with t",
            "By what number is the heat produced multiplied?",
            ((SQI, "kI*kt"), (TLEFT, "kI^2"), (INV, "kt/kI^2"), (SQI, "kI*kt*2")),
            kind="rule",
            laws=("FH - kI**2*kt",),
            forms=("num3", "case4"),
        ),
    },
)

ENERGY = Model(
    id="ELEC.ENERGY",
    skill="PHY.ELEC.ENERGY_KWH",
    chapter=CH,
    technique="electrical_energy",
    topic="the electrical energy an appliance uses",
    syms={"P1": "W", "t1": "h", "P2": "W", "t2": "h", "d": "unit", "E1": "J", "E2": "J"},
    labels={
        "P1": ("power", "the power rating of the first appliance is {v}"),
        "t1": ("time", "the time it is used each day is {v}"),
        "P2": ("second power", "the power rating of the second appliance is {v}"),
        "t2": ("second time", "the time the second one is used each day is {v}"),
        "d": ("number of days", "the number of days is {v}"),
        "E1": ("energy", "the energy used is {v}"),
        "E2": ("energy", "the energy used is {v}"),
    },
    base=_bases(
        {
            "P1": ("P1", "W"),
            "t1": ("t1", "h"),
            "P2": ("P2", "W"),
            "t2": ("t2", "h"),
            "d": ("d", "unit"),
        }
    ),
    derived=lambda p: (("E1", "P1*t1"), ("E2", "(P1*t1+P2*t2)*d")),
    dunits={"E1": "kWh", "E2": "kWh"},
    laws=("E1 - P1*t1",),
    variants={
        "E_one": Variant(
            "E_one",
            "E1",
            ("P1", "t1"),
            "P1*t1",
            ("1", "P1*t1"),
            "energy E = power P x time t; 1 kWh = 1000 W for 1 hour",
            "How much electrical energy is used, in kWh?",
            ((TLEFT, "@P1_r/1000"), (DIVE, "@P1_r/t1_r/1000"), (ADD, "@(P1_r+t1_r)/1000")),
            laws=("E1 - P1*t1",),
            forms=("mcq1", "num2"),
        ),
        "E_two": Variant(
            "E_two",
            "E2",
            ("P1", "t1", "P2", "t2", "d"),
            "(P1*t1+P2*t2)*d",
            ("1", "(P1*t1+P2*t2)*d"),
            "add the energy of each appliance for one day, power times time, then multiply by the days",  # noqa: E501
            "How much electrical energy is used in all, in kWh?",
            (
                (DLEFT, "@(P1_r*t1_r+P2_r*t2_r)/1000"),
                (TLEFT, "@(P1_r+P2_r)*d/1000"),
                (ONEAPP, "@P1_r*t1_r*d/1000"),
                (ADD, "@(P1_r*t1_r+P2_r*t2_r)+d"),
            ),
            laws=("E2 - (P1*t1+P2*t2)*d",),
            forms=("num3", "case4"),
        ),
        "t_from_EP": Variant(
            "t_from_EP",
            "t1",
            ("E1", "P1"),
            "E1/P1",
            ("P1", "E1"),
            "energy E = power P x time t",
            "For how many hours can it run?",
            ((MULT, "@E1_r*P1_r"), (INV, "@P1_r/E1_r/1000"), (TLEFT, "@E1_r*1000")),
            rearr="divide each side of E = P x t by P",
            laws=("E1 - P1*t1",),
            forms=("num2", "num3"),
        ),
    },
)

HEAT = Model(
    id="ELEC.HEATING",
    skill="PHY.ELEC.HEATING",
    chapter=CH,
    technique="joule_heating",
    topic="the heat produced by a current",
    syms={"H": "J", "I": "A", "R": "ohm", "t": "s", "V": "V"},
    labels={
        "H": ("heat produced", "the heat produced is {v}"),
        "I": ("current", "the current is {v}"),
        "R": ("resistance", "the resistance is {v}"),
        "t": ("time", "the time is {v}"),
        "V": ("voltage", "the voltage is {v}"),
    },
    base=_bases({"I": ("I", "A"), "R": ("R", "ohm"), "t": ("t", "$tu")}),
    derived=lambda p: (("V", "I*R"), ("H", "I*I*R*t")),
    dunits={"H": "J", "V": "V"},
    laws=("H - I**2*R*t",),
    variants={
        "H_IRt": Variant(
            "H_IRt",
            "H",
            ("I", "R", "t"),
            "I*I*R*t",
            ("1", "I^2*R*t"),
            "heat H = I x I x R x t",
            "How much heat is produced?",
            ((SQI, "I*R*t"), (TLEFT, "I^2*R"), (TIME, "I^2*R*t_r"), (INV, "I^2*t/R")),
            laws=("H - I**2*R*t",),
        ),
        "H_VRt": Variant(
            "H_VRt",
            "H",
            ("V", "R", "t"),
            "V*V*t/R",
            ("R", "V^2*t"),
            "heat H = V x V x t / R",
            "How much heat is produced?",
            ((SQV, "V*t/R"), (TLEFT, "V^2/R"), (TIME, "V^2*t_r/R"), (INV, "R*t/V^2")),
            laws=("H*R - V**2*t",),
        ),
        "H_VIt": Variant(
            "H_VIt",
            "H",
            ("V", "I", "t"),
            "V*I*t",
            ("1", "V*I*t"),
            "heat H = V x I x t",
            "How much heat is produced?",
            ((TLEFT, "V*I"), (TIME, "V*I*t_r"), (PVI, "V/I*t"), (ADD, "V*I+t")),
            laws=("H - V*I*t",),
            forms=("mcq1", "num2", "num3"),
        ),
        "I_from_HRt": Variant(
            "I_from_HRt",
            "I",
            ("H", "R", "t"),
            "sqrt(H/R/t)",
            ("1", "sqrt(H/R/t)"),
            "heat H = I x I x R x t",
            "Find the current.",
            (
                (ROOT, "H/(R*t)"),
                (TIME, "sqrt(H/(R*t_r))"),
                (PFORM, "H/(R*t)^2"),
                (INV, "sqrt(R*t/H)"),
            ),
            rearr="divide each side of H = I x I x R x t by R x t, then take the square root of each side",  # noqa: E501
            laws=("H - I**2*R*t",),
            forms=("num3", "case4"),
        ),
    },
)

ELEC_MODELS: dict[str, Model] = {
    m.id: m
    for m in (
        CHARGE,
        COUNT,
        POTDIFF,
        OHM,
        RESIST,
        SCALE,
        SERIES,
        PARALLEL,
        SCIRC,
        PCIRC,
        MIXED,
        POWER,
        PSCALE,
        ENERGY,
        HEAT,
    )
}
