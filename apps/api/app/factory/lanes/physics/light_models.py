# ruff: noqa: E501
"""CBSE Class 10 Light (reflection and refraction): numerical models, one sign convention.

Every signed value follows convention.py. A displayed distance is a magnitude plus a role (object,
real image, virtual image, focal length): the sign is applied by the methods, never typed in the
stem. Ray-diagram, graph and experiment questions are out of scope.
"""

from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction
from typing import Any

from app.factory.lanes.physics.convention import FOCAL_SIGN, role_sign
from app.factory.lanes.physics.model import Model, Variant
from app.factory.lanes.physics.quantities import to_si

CH = "cbse.10.physics.light"
L = "PHY.MC.LIGHT."
USIGN, FSIGN, VSIGN = L + "U_SIGN_DROPPED", L + "F_SIGN_WRONG", L + "V_SIGN_DROPPED"
MIX, RECIP, RADF = (
    L + "MIRROR_LENS_FORMULA_MIXED",
    L + "FORGOT_FINAL_RECIPROCAL",
    L + "RADIUS_FOCAL_CONFUSED",
)  # noqa: E501
MSIGN, MINV, MINVS = L + "MAG_SIGN_DROPPED", L + "MAG_INVERTED", L + "MAG_INVERTED_SIGN_DROPPED"
PINCM, PSIGN, PNOREC = L + "POWER_IN_CM", L + "POWER_SIGN_IGNORED", L + "POWER_NOT_RECIPROCAL"
FADD, PMUL = L + "FOCAL_LENGTHS_ADDED", L + "POWERS_MULTIPLIED"
NINV, NSLOWER, NTEN = (
    L + "INDEX_INVERTED",
    L + "SPEED_INCREASES_IN_DENSER_MEDIUM",
    L + "POWER_OF_TEN_SLIP",
)  # noqa: E501
SNINV, SNDIFF, SNMUL = (
    L + "SNELL_INVERTED",
    L + "SINES_SUBTRACTED",
    L + "SNELL_MULTIPLIED_WRONG_WAY",
)
RELINV, RELDIFF, RELPROD = (
    L + "RELATIVE_INDEX_INVERTED",
    L + "INDEX_DIFFERENCE_USED",
    L + "INDEX_PRODUCT_USED",
)  # noqa: E501
NATV, NATM, NATS = (
    L + "V_SIGN_MEANING_REVERSED",
    L + "MAG_SIGN_MEANING_REVERSED",
    L + "SIZE_MEANING_REVERSED",
)  # noqa: E501
HNOT = L + "HEIGHT_NOT_USED"

CM = "cm"


def _device(p: Mapping[str, Any]) -> str:
    return str(p["device"])


def _family(device: str) -> str:
    return "mirror" if device.endswith("mirror") else "lens"


def _optics_base(p: Mapping[str, Any]) -> tuple[dict[str, Fraction], dict[str, str]]:
    dev = _device(p)
    f = FOCAL_SIGN[dev] * Fraction(str(p["fm"]))
    si = {"f": to_si(f, CM)}
    un = {"f": CM}
    if "um" in p:
        si["u"] = to_si(-Fraction(str(p["um"])), CM)
        un["u"] = CM
    if "h" in p:
        si["h"] = to_si(p["h"], CM)
        un["h"] = CM
    return si, un


def _optics_derived(p: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    mirror = _family(_device(p)) == "mirror"
    if "um" not in p:
        return (("R", "2*f"),) if mirror else (("P", "1/f"),)
    if mirror:
        d = (("v", "u*f/(u-f)"), ("m", "-v/u"), ("R", "2*f"))
    else:
        d = (("v", "u*f/(u+f)"), ("m", "v/u"), ("P", "1/f"))
    return d + ((("hi", "m*h"),) if "h" in p else ())


def _optics_roles(
    p: Mapping[str, Any], full: Mapping[str, Fraction]
) -> dict[str, tuple[str, str | None]]:
    dev = _device(p)
    mirror = _family(dev) == "mirror"
    v = full.get("v", Fraction(0))
    real = (v < 0) if mirror else (v > 0)
    out: dict[str, tuple[str, str | None]] = {
        "u": ("object_distance", dev), "f": ("focal", dev), "R": ("focal", dev),
        "v": ("image_real" if real else "image_virtual", dev),
        "h": ("height_object", dev), "P": ("power", dev),
    }  # fmt: skip
    if "hi" in full:
        out["hi"] = ("height_image_erect" if full["hi"] > 0 else "height_image_inverted", dev)
    return out


_LABELS = {
    "u": ("object distance", "the object is {v} from the {dev}"),
    "v": ("image distance", "the image is {v} from the {dev}"),
    "f": ("focal length", "the focal length of the {dev} is {v}"),
    "R": ("radius of curvature", "the radius of curvature of the {dev} is {v}"),
    "h": ("object height", "the object is {v} tall"),
    "hi": ("image height", "the image is {v} tall"),
    "m": ("magnification", "the magnification is {v}"),
    "P": ("power", "the power of the lens is {v}"),
}
_SYMS = {"u": "m", "v": "m", "f": "m", "R": "m", "h": "m", "hi": "m", "m": "unit", "P": "D"}
_SIZES = {s: (Fraction(1, 100), Fraction(3)) for s in ("u", "v", "f", "R")}
_SIZES["hi"] = (Fraction(1, 1000), Fraction(1))

SIGN = Model(
    id="LIGHT.SIGN",
    skill="PHY.LIGHT.SIGN_CONVENTION",
    chapter=CH,
    technique="sign_convention",
    topic="the sign convention for mirrors and lenses",
    syms={"d": "m", "x": "m", "s": "unit"},
    labels={"d": ("magnitude", "the distance is {v}"), "x": ("signed value", "x")},
    base=lambda p: (
        {
            "d": to_si(p["d"], CM),
            "s": Fraction(role_sign(str(p["case"]).split(":")[0], str(p["case"]).split(":")[1])),
        },
        {"d": CM, "s": "unit"},
    ),
    derived=lambda p: (("x", "s*d"),),
    dunits={"x": CM},
    laws=("x - s*d",),
    rule_derived=True,
    device=lambda p: str(p["case"]).split(":")[0],
    variants={
        "x_signed": Variant(
            "x_signed",
            "x",
            ("d",),
            "s*d",
            ("1", "s*d"),
            "apply the Cartesian sign convention: distances measured against the incident light are negative, with the right sign for the role of the quantity",  # noqa: E501
            "Using the Cartesian sign convention, what is the signed value in cm?",
            (),
            rearr=None,
            kind="rule",
            forms=("mcq1", "num2"),
        ),
    },
)


def _sign_wrongs(p: Mapping[str, Any], v: Variant) -> tuple[tuple[str, str], ...]:
    return ((FSIGN, "-s*d"), (RADF, "2*s*d"), (RADF, "s*d/2"), (FSIGN, "-2*s*d"))


SIGN = Model(
    **{
        **SIGN.__dict__,
        "extra_wrongs": _sign_wrongs,
        "mc_prefix": "PHY.MC.LIGHT",
        "signed": True,
        "auto_slips": False,
    }
)


def _mk(
    mid: str,
    skill: str,
    tech: str,
    topic: str,
    laws: tuple[str, ...],
    variants: dict[str, Variant],
    **kw: Any,
) -> Model:
    return Model(
        id=mid,
        skill=skill,
        chapter=CH,
        technique=tech,
        topic=topic,
        syms=_SYMS,
        labels=_LABELS,
        base=_optics_base,
        derived=_optics_derived,
        variants=variants,
        laws=laws,
        signed=True,
        dunits={"v": CM, "R": CM, "hi": CM, "m": "unit", "P": "D"},
        sizes=_SIZES,
        device=_device,
        roles=_optics_roles,
        mc_prefix="PHY.MC.LIGHT",
        **kw,
    )


MIRROR_FOCAL = _mk(
    "LIGHT.MIRROR_FOCAL",
    "PHY.LIGHT.MIRROR_FOCAL",
    "mirror_focal_length",
    "radius of curvature and focal length of a spherical mirror",
    ("2*f - R",),
    {
        "f_from_R": Variant(
            "f_from_R",
            "f",
            ("R",),
            "R/2",
            ("2", "R"),
            "the focal length is half the radius of curvature: f = R / 2, with signs from the convention",  # noqa: E501
            "Find the focal length, with its sign.",
            ((FSIGN, "-R/2"), (RADF, "R"), (RADF, "2*R"), (FSIGN, "-R")),
            rearr="divide each side of R = 2f by 2",
            laws=("2*f - R",),
            forms=("mcq1", "num2"),
        ),
        "R_from_f": Variant(
            "R_from_f",
            "R",
            ("f",),
            "2*f",
            ("1", "2*f"),
            "the radius of curvature is twice the focal length: R = 2f, with signs from the convention",  # noqa: E501
            "Find the radius of curvature, with its sign.",
            ((FSIGN, "-2*f"), (RADF, "f"), (RADF, "f/2"), (FSIGN, "-f")),
            laws=("2*f - R",),
            forms=("mcq1", "num2"),
        ),
    },
)

MIRROR_FORMULA = _mk(
    "LIGHT.MIRROR_FORMULA",
    "PHY.LIGHT.MIRROR_FORMULA",
    "mirror_formula",
    "image formation by a spherical mirror",
    ("1/v + 1/u - 1/f",),
    {
        "v_from_uf": Variant(
            "v_from_uf",
            "v",
            ("u", "f"),
            "u*f/(u-f)",
            ("u-f", "u*f"),
            "mirror formula 1/v + 1/u = 1/f, with u and f signed by the convention",
            "Using the Cartesian sign convention, find the image distance v.",
            (
                (USIGN, "(-u)*f/((-u)-f)"),
                (FSIGN, "u*(-f)/(u+f)"),
                (MIX, "u*f/(u+f)"),
                (RECIP, "1/f-1/u"),
                (VSIGN, "-u*f/(u-f)"),
            ),
            rearr="subtract 1/u from each side of 1/v + 1/u = 1/f, then take the reciprocal of each side",  # noqa: E501
            laws=("1/v + 1/u - 1/f",),
        ),
        "u_from_vf": Variant(
            "u_from_vf",
            "u",
            ("v", "f"),
            "v*f/(v-f)",
            ("v-f", "v*f"),
            "mirror formula 1/v + 1/u = 1/f, with v and f signed by the convention",
            "Using the Cartesian sign convention, find the object distance u.",
            (
                (VSIGN, "(-v)*f/((-v)-f)"),
                (FSIGN, "v*(-f)/(v+f)"),
                (MIX, "v*f/(v+f)"),
                (RECIP, "1/f-1/v"),
                (USIGN, "-v*f/(v-f)"),
            ),
            rearr="subtract 1/v from each side of 1/v + 1/u = 1/f, then take the reciprocal of each side",  # noqa: E501
            laws=("1/v + 1/u - 1/f",),
            forms=("num2", "num3", "case4"),
        ),
        "f_from_uv": Variant(
            "f_from_uv",
            "f",
            ("u", "v"),
            "u*v/(u+v)",
            ("u+v", "u*v"),
            "mirror formula 1/v + 1/u = 1/f, with u and v signed by the convention",
            "Using the Cartesian sign convention, find the focal length f.",
            (
                (USIGN, "(-u)*v/((-u)+v)"),
                (MIX, "u*v/(u-v)"),
                (RECIP, "1/u+1/v"),
                (FSIGN, "-u*v/(u+v)"),
            ),
            rearr="add 1/v and 1/u, then take the reciprocal of each side of 1/f = 1/v + 1/u",
            laws=("1/v + 1/u - 1/f",),
            forms=("num2", "num3", "case4"),
        ),
    },
)

MIRROR_MAG = _mk(
    "LIGHT.MIRROR_MAG",
    "PHY.LIGHT.MIRROR_MAGNIFICATION",
    "mirror_magnification",
    "the magnification of a spherical mirror",
    ("m*u + v", "hi - m*h"),
    {
        "m_from_uv": Variant(
            "m_from_uv",
            "m",
            ("u", "v"),
            "-v/u",
            ("u", "-v"),
            "magnification of a mirror m = -v / u",
            "Find the magnification, with its sign.",
            ((MSIGN, "v/u"), (MINV, "-u/v"), (MINVS, "u/v")),
            laws=("m*u + v",),
            forms=("mcq1", "num2"),
        ),
        "hi_from_uvh": Variant(
            "hi_from_uvh",
            "hi",
            ("u", "v", "h"),
            "-v*h/u",
            ("u", "-v*h"),
            "m = -v / u and m = image height / object height",
            "Find the height of the image, with its sign.",
            ((MSIGN, "v*h/u"), (MINV, "-u*h/v"), (MINVS, "u*h/v"), (HNOT, "-v/u")),
            rearr="multiply each side of m = hi / h by h",
            laws=("m*u + v", "hi - m*h"),
            forms=("num2", "num3", "case4"),
        ),
        "v_from_um": Variant(
            "v_from_um",
            "v",
            ("u", "m"),
            "-m*u",
            ("1", "-m*u"),
            "magnification of a mirror m = -v / u",
            "Find the image distance, with its sign.",
            ((MIX, "m*u"), (MINV, "-u/m"), (MINVS, "u/m")),
            rearr="multiply each side of m = -v / u by u, then change the sign of each side",
            laws=("m*u + v",),
            forms=("num2", "num3"),
        ),
    },
)

MIRROR_NATURE = _mk(
    "LIGHT.MIRROR_NATURE",
    "PHY.LIGHT.IMAGE_NATURE",
    "image_nature_rule",
    "the nature of the image from the mirror and lens formulas",
    ("1/v + 1/u - 1/f", "m*u + v"),
    {
        "nature_mirror": Variant(
            "nature_mirror",
            "v",
            ("u", "f"),
            "u*f/(u-f)",
            ("u-f", "u*f"),
            "find v from the mirror formula, then m = -v / u; a negative v is a real image in front of the mirror, a negative m is inverted, |m| above 1 is magnified",  # noqa: E501
            "What is the nature of the image?",
            (),
            kind="rule",
            nature="mirror",
            laws=("1/v + 1/u - 1/f", "m*u + v"),
            forms=("num2", "num3", "case4"),
        ),
        "nature_lens": Variant(
            "nature_lens",
            "v",
            ("u", "f"),
            "u*f/(u+f)",
            ("u+f", "u*f"),
            "find v from the lens formula, then m = v / u; a positive v is a real image on the far side, a negative m is inverted, |m| above 1 is magnified",  # noqa: E501
            "What is the nature of the image?",
            (),
            kind="rule",
            nature="lens",
            laws=("1/v - 1/u - 1/f", "m*u - v"),
            forms=("num2", "num3", "case4"),
        ),
    },
)

LENS_FORMULA = _mk(
    "LIGHT.LENS_FORMULA",
    "PHY.LIGHT.LENS_FORMULA",
    "lens_formula",
    "image formation by a thin lens",
    ("1/v - 1/u - 1/f",),
    {
        "v_from_uf": Variant(
            "v_from_uf",
            "v",
            ("u", "f"),
            "u*f/(u+f)",
            ("u+f", "u*f"),
            "lens formula 1/v - 1/u = 1/f, with u and f signed by the convention",
            "Using the Cartesian sign convention, find the image distance v.",
            (
                (USIGN, "(-u)*f/((-u)+f)"),
                (FSIGN, "u*(-f)/(u-f)"),
                (MIX, "u*f/(u-f)"),
                (RECIP, "1/f+1/u"),
                (VSIGN, "-u*f/(u+f)"),
            ),
            rearr="add 1/u to each side of 1/v - 1/u = 1/f, then take the reciprocal of each side",
            laws=("1/v - 1/u - 1/f",),
        ),
        "u_from_vf": Variant(
            "u_from_vf",
            "u",
            ("v", "f"),
            "v*f/(f-v)",
            ("f-v", "v*f"),
            "lens formula 1/v - 1/u = 1/f, with v and f signed by the convention",
            "Using the Cartesian sign convention, find the object distance u.",
            (
                (VSIGN, "(-v)*f/(f+v)"),
                (FSIGN, "v*(-f)/(-f-v)"),
                (MIX, "v*f/(v-f)"),
                (RECIP, "1/v-1/f"),
                (USIGN, "-v*f/(f-v)"),
            ),
            rearr="subtract 1/f from each side of 1/v - 1/u = 1/f, then rearrange for 1/u and take the reciprocal",  # noqa: E501
            laws=("1/v - 1/u - 1/f",),
            forms=("num2", "num3", "case4"),
        ),
        "f_from_uv": Variant(
            "f_from_uv",
            "f",
            ("u", "v"),
            "u*v/(u-v)",
            ("u-v", "u*v"),
            "lens formula 1/v - 1/u = 1/f, with u and v signed by the convention",
            "Using the Cartesian sign convention, find the focal length f.",
            (
                (USIGN, "(-u)*v/((-u)-v)"),
                (MIX, "u*v/(u+v)"),
                (RECIP, "1/v-1/u"),
                (FSIGN, "-u*v/(u-v)"),
            ),
            rearr="subtract 1/u from 1/v, then take the reciprocal of each side of 1/f = 1/v - 1/u",
            laws=("1/v - 1/u - 1/f",),
            forms=("num2", "num3", "case4"),
        ),
    },
)

LENS_MAG = _mk(
    "LIGHT.LENS_MAG",
    "PHY.LIGHT.LENS_MAGNIFICATION",
    "lens_magnification",
    "the magnification of a thin lens",
    ("m*u - v", "hi - m*h"),
    {
        "m_from_uv": Variant(
            "m_from_uv",
            "m",
            ("u", "v"),
            "v/u",
            ("u", "v"),
            "magnification of a lens m = v / u",
            "Find the magnification, with its sign.",
            ((MIX, "-v/u"), (MINV, "u/v"), (MINVS, "-u/v")),
            laws=("m*u - v",),
            forms=("mcq1", "num2"),
        ),
        "hi_from_uvh": Variant(
            "hi_from_uvh",
            "hi",
            ("u", "v", "h"),
            "v*h/u",
            ("u", "v*h"),
            "m = v / u and m = image height / object height",
            "Find the height of the image, with its sign.",
            ((MIX, "-v*h/u"), (MINV, "u*h/v"), (MINVS, "-u*h/v"), (HNOT, "v/u")),
            rearr="multiply each side of m = hi / h by h",
            laws=("m*u - v", "hi - m*h"),
            forms=("num2", "num3", "case4"),
        ),
        "v_from_um": Variant(
            "v_from_um",
            "v",
            ("u", "m"),
            "m*u",
            ("1", "m*u"),
            "magnification of a lens m = v / u",
            "Find the image distance, with its sign.",
            ((MIX, "-m*u"), (MINV, "u/m"), (MINVS, "-u/m")),
            rearr="multiply each side of m = v / u by u",
            laws=("m*u - v",),
            forms=("num2", "num3"),
        ),
    },
)

LENS_POWER = _mk(
    "LIGHT.LENS_POWER",
    "PHY.LIGHT.LENS_POWER",
    "lens_power",
    "the power of a lens",
    ("P*f - 1",),
    {
        "P_from_f": Variant(
            "P_from_f",
            "P",
            ("f",),
            "1/f",
            ("f", "1"),
            "power P = 1 / f, with f in metres and its sign from the convention",
            "Find the power of the lens in dioptres, with its sign.",
            ((PSIGN, "abs(1/f)"), (PINCM, "1/f/100"), (PNOREC, "f"), (PSIGN, "-1/f")),
            laws=("P*f - 1",),
            forms=("mcq1", "num2"),
        ),
        "f_from_P": Variant(
            "f_from_P",
            "f",
            ("P",),
            "1/P",
            ("P", "1"),
            "power P = 1 / f, so f = 1 / P in metres",
            "Find the focal length in cm, with its sign.",
            ((PSIGN, "abs(1/P)"), (PINCM, "@K/100"), (PNOREC, "@P_r"), (PINCM, "@K*100")),
            rearr="multiply each side of P = 1 / f by f, then divide each side by P",
            laws=("P*f - 1",),
            forms=("num2", "num3"),
        ),
    },
)


def _comb_base(p: Mapping[str, Any]) -> tuple[dict[str, Fraction], dict[str, str]]:
    f1 = FOCAL_SIGN[str(p["d1"])] * Fraction(str(p["f1"]))
    f2 = FOCAL_SIGN[str(p["d2"])] * Fraction(str(p["f2"]))
    return {"f1": to_si(f1, CM), "f2": to_si(f2, CM)}, {"f1": CM, "f2": CM}


def _comb_roles(
    p: Mapping[str, Any], full: Mapping[str, Fraction]
) -> dict[str, tuple[str, str | None]]:  # noqa: E501
    d1, d2 = str(p["d1"]), str(p["d2"])
    return {"f1": ("focal", d1), "f2": ("focal", d2), "P1": ("power", d1), "P2": ("power", d2)}


LENS_COMB = Model(
    id="LIGHT.LENS_COMB",
    skill="PHY.LIGHT.LENS_COMBINATION",
    chapter=CH,
    technique="lens_combination",
    topic="two thin lenses in contact",
    syms={"f1": "m", "f2": "m", "f": "m", "P1": "D", "P2": "D", "P": "D"},
    labels={
        "f1": (
            "first focal length",
            "the first lens is a {dev} with focal length of magnitude {v}",
        ),  # noqa: E501
        "f2": (
            "second focal length",
            "the second lens is a {dev} with focal length of magnitude {v}",
        ),  # noqa: E501
        "P1": ("first power", "the first lens is a {dev} with power of magnitude {v}"),
        "P2": ("second power", "the second lens is a {dev} with power of magnitude {v}"),
        "P": ("combined power", "x"),
        "f": ("combined focal length", "x"),
    },
    base=_comb_base,
    derived=lambda p: (("P1", "1/f1"), ("P2", "1/f2"), ("P", "P1+P2"), ("f", "1/P")),
    dunits={"P1": "D", "P2": "D", "P": "D", "f": CM},
    signed=True,
    laws=("P - 1/f1 - 1/f2",),
    sizes={"f": (Fraction(1, 100), Fraction(3))},
    device=lambda p: str(p["d1"]),
    roles=_comb_roles,
    mc_prefix="PHY.MC.LIGHT",
    variants={
        "P_from_f1f2": Variant(
            "P_from_f1f2",
            "P",
            ("f1", "f2"),
            "1/f1+1/f2",
            ("f1*f2", "f1+f2"),
            "for thin lenses in contact the powers add: P = 1/f1 + 1/f2 (f in metres, with signs)",
            "Find the power of the combination in dioptres, with its sign.",
            (
                (FADD, "1/(f1+f2)"),
                (PSIGN, "abs(1/f1)+abs(1/f2)"),
                (PMUL, "1/(f1*f2)"),
                (PINCM, "(1/f1+1/f2)/100"),
            ),
            laws=("P - 1/f1 - 1/f2",),
            forms=("num3", "case4"),
        ),
        "f_from_P1P2": Variant(
            "f_from_P1P2",
            "f",
            ("P1", "P2"),
            "1/(P1+P2)",
            ("P1+P2", "1"),
            "the powers add, then f = 1 / P, in metres",
            "Find the focal length of the combination in cm, with its sign.",
            (
                (PSIGN, "1/(abs(P1)+abs(P2))"),
                (PMUL, "1/(P1*P2)"),
                (FADD, "1/P1+1/P2"),
                (PINCM, "@K/100"),
            ),
            rearr="add the powers, then take the reciprocal of each side of P = 1 / f",  # noqa: E501
            laws=("1/f - P1 - P2",),
            forms=("num3", "case4"),
        ),
    },
)


def _n_base(spec: Mapping[str, str]) -> Any:
    def build(p: Mapping[str, Any]) -> tuple[dict[str, Fraction], dict[str, str]]:
        return ({s: to_si(p[k], "unit") for s, k in spec.items()}, {s: "unit" for s in spec})

    return build


REFRACT = Model(
    id="LIGHT.REFRACTIVE_INDEX",
    skill="PHY.LIGHT.REFRACTIVE_INDEX",
    chapter=CH,
    technique="refractive_index_speed",
    topic="light travelling in a transparent medium",
    syms={"n": "unit", "v": "m/s", "c": "m/s"},
    labels={
        "n": ("refractive index", "the refractive index of the medium is {v}"),
        "v": ("speed of light in the medium", "light travels in the medium at {v}"),
    },
    base=_n_base({"n": "n"}),
    derived=lambda p: (("v", "c/n"),),
    dunits={"v": "m/s", "n": "unit"},
    consts={"c": "c_light"},
    laws=("n*v - c",),
    mc_prefix="PHY.MC.LIGHT",
    variants={
        "n_from_v": Variant(
            "n_from_v",
            "n",
            ("v",),
            "c/v",
            ("v", "c"),
            "refractive index n = speed of light in vacuum / speed in the medium",
            "Find the refractive index of the medium.",
            ((NINV, "v/c"), (NTEN, "@K*10"), (NTEN, "@K/10"), (NSLOWER, "(c-v)/c")),
            rearr="multiply each side of n = c / v by v, then divide each side by n",
            laws=("n*v - c",),
            forms=("mcq1", "num2", "num3"),
        ),
        "v_from_n": Variant(
            "v_from_n",
            "v",
            ("n",),
            "c/n",
            ("n", "c"),
            "refractive index n = speed of light in vacuum / speed in the medium",
            "Find the speed of light in the medium.",
            ((NSLOWER, "c*n"), (NTEN, "@K*10"), (NTEN, "@K/10"), (NINV, "c-n")),
            rearr="multiply each side of n = c / v by v, then divide each side by n",
            laws=("n*v - c",),
            forms=("num2", "num3"),
        ),
    },
)

SNELL = Model(
    id="LIGHT.SNELL",
    skill="PHY.LIGHT.SNELL",
    chapter=CH,
    technique="snells_law",
    topic="light entering a transparent medium from air",
    syms={"n": "unit", "si": "unit", "sr": "unit"},
    labels={
        "n": ("refractive index", "the refractive index of the medium is {v}"),
        "si": ("sine of the angle of incidence", "the sine of the angle of incidence is {v}"),
        "sr": ("sine of the angle of refraction", "the sine of the angle of refraction is {v}"),
    },
    base=_n_base({"n": "n", "si": "si"}),
    derived=lambda p: (("sr", "si/n"),),
    dunits={"sr": "unit", "n": "unit", "si": "unit"},
    laws=("n*sr - si",),
    mc_prefix="PHY.MC.LIGHT",
    variants={
        "n_from_sines": Variant(
            "n_from_sines",
            "n",
            ("si", "sr"),
            "si/sr",
            ("sr", "si"),
            "from air into a medium, n = sine of the angle of incidence / sine of the angle of refraction",
            "Find the refractive index of the medium.",
            ((SNINV, "sr/si"), (SNDIFF, "si-sr"), (SNMUL, "si*sr"), (SNDIFF, "si+sr")),
            rearr="divide each side of sin i = n x sin r by sin r",
            laws=("n*sr - si",),
            forms=("mcq1", "num2"),
        ),
        "sr_from_n": Variant(
            "sr_from_n",
            "sr",
            ("n", "si"),
            "si/n",
            ("n", "si"),
            "from air into a medium, sin i = n x sin r",
            "Find the sine of the angle of refraction.",
            ((SNMUL, "si*n"), (SNINV, "n/si"), (SNDIFF, "si-n"), (SNDIFF, "si")),
            rearr="divide each side of sin i = n x sin r by n",
            laws=("n*sr - si",),
            forms=("num2", "num3"),
        ),
        "si_from_n_sr": Variant(
            "si_from_n_sr",
            "si",
            ("n", "sr"),
            "n*sr",
            ("1", "n*sr"),
            "from air into a medium, sin i = n x sin r",
            "Find the sine of the angle of incidence.",
            ((SNINV, "sr/n"), (SNDIFF, "n-sr"), (SNMUL, "n/sr"), (SNDIFF, "n+sr")),
            laws=("n*sr - si",),
            forms=("num2", "num3"),
        ),
    },
)

RELATIVE = Model(
    id="LIGHT.RELATIVE_INDEX",
    skill="PHY.LIGHT.RELATIVE_INDEX",
    chapter=CH,
    technique="relative_refractive_index",
    topic="light passing from one medium into another",
    syms={"n1": "unit", "n2": "unit", "n21": "unit", "v1": "m/s", "v2": "m/s", "c": "m/s"},
    labels={
        "n1": ("refractive index of the first medium", "the first medium has refractive index {v}"),  # noqa: E501
        "n2": (
            "refractive index of the second medium",
            "the second medium has refractive index {v}",
        ),  # noqa: E501
        "n21": (
            "refractive index of the second medium relative to the first",
            "the second medium relative to the first has refractive index {v}",
        ),  # noqa: E501
        "v1": ("speed of light in the first medium", "light travels in the first medium at {v}"),  # noqa: E501
        "v2": ("speed of light in the second medium", "light travels in the second medium at {v}"),
    },  # noqa: E501
    base=_n_base({"n1": "n1", "n2": "n2"}),
    derived=lambda p: (("n21", "n2/n1"), ("v1", "c/n1"), ("v2", "c/n2")),
    dunits={"n21": "unit", "v1": "m/s", "v2": "m/s"},
    consts={"c": "c_light"},
    laws=("n21*n1 - n2",),
    mc_prefix="PHY.MC.LIGHT",
    variants={
        "n21_from_n": Variant(
            "n21_from_n",
            "n21",
            ("n1", "n2"),
            "n2/n1",
            ("n1", "n2"),
            "relative refractive index of medium 2 with respect to medium 1: n21 = n2 / n1",
            "Find the refractive index of the second medium relative to the first.",
            ((RELINV, "n1/n2"), (RELDIFF, "n2-n1"), (RELPROD, "n1*n2")),
            laws=("n21*n1 - n2",),
            forms=("mcq1", "num2"),
        ),
        "n2_from_n21": Variant(
            "n2_from_n21",
            "n2",
            ("n21", "n1"),
            "n21*n1",
            ("1", "n21*n1"),
            "n21 = n2 / n1",
            "Find the refractive index of the second medium.",
            ((RELINV, "n1/n21"), (RELDIFF, "n21+n1"), (RELPROD, "n21/n1")),
            rearr="multiply each side of n21 = n2 / n1 by n1",
            laws=("n21*n1 - n2",),
            forms=("num2", "num3"),
        ),
        "n21_from_v": Variant(
            "n21_from_v",
            "n21",
            ("v1", "v2"),
            "v1/v2",
            ("v2", "v1"),
            "n21 = n2 / n1 and each n = c / v, so n21 = v1 / v2",
            "Find the refractive index of the second medium relative to the first.",
            ((RELINV, "v2/v1"), (RELDIFF, "(v1-v2)/c"), (RELPROD, "v1*v2/c/c")),
            laws=("n21*v2 - v1",),
            forms=("num2", "num3", "case4"),
        ),
    },
)

LIGHT_MODELS: dict[str, Model] = {
    m.id: m
    for m in (
        SIGN,
        MIRROR_FOCAL,
        MIRROR_FORMULA,
        MIRROR_MAG,
        MIRROR_NATURE,
        LENS_FORMULA,
        LENS_MAG,
        LENS_POWER,
        LENS_COMB,
        REFRACT,
        SNELL,
        RELATIVE,
    )
}
