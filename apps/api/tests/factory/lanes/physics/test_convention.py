"""The single sign convention is pinned: data, worked examples, both copies agree."""

from fractions import Fraction

import pytest

from app.factory.lanes.physics import convention as conv
from app.factory.lanes.physics.methods import ClosedForm, SympyLaws, a_sign
from app.factory.lanes.physics.quantities import evaluate

DEVICES = ("concave_mirror", "convex_mirror", "convex_lens", "concave_lens")
ROLES = ("object_distance", "image_real", "image_virtual", "height_object",
         "height_image_erect", "height_image_inverted", "focal", "power")  # fmt: skip


def test_the_convention_is_recorded_and_not_claimed_reviewed():
    c = conv.SIGN_CONVENTION
    assert c["name"].startswith("Cartesian") and c["reviewed"] is False
    assert c["focal_sign"] == {"concave_mirror": -1, "convex_mirror": 1, "convex_lens": 1,
                               "concave_lens": -1}  # fmt: skip
    assert c["formulas"]["mirror"] == "1/v + 1/u = 1/f"
    assert c["formulas"]["lens"] == "1/v - 1/u = 1/f"
    assert c["formulas"]["mirror_magnification"] == "m = -v/u"
    assert c["formulas"]["lens_magnification"] == "m = v/u"


@pytest.mark.parametrize("device", DEVICES)
@pytest.mark.parametrize("role", ROLES)
def test_hand_written_signs_equal_the_table(device, role):
    assert a_sign(device, role) == conv.role_sign(device, role)


def test_real_objects_are_negative_everywhere():
    assert all(conv.role_sign(d, "object_distance") == -1 for d in DEVICES)


def _v(device: str, u: str, f: str) -> Fraction:
    u_, f_ = Fraction(u), Fraction(f)
    mirror = device.endswith("mirror")
    return evaluate("u*f/(u-f)" if mirror else "u*f/(u+f)", {"u": u_, "f": f_})


def test_worked_examples_follow_the_convention():
    # concave mirror, object 30 cm, f = -10 cm: real, inverted, diminished image at -15 cm
    v = _v("concave_mirror", "-30", "-10")
    assert v == -15 and -v / Fraction(-30) == Fraction(-1, 2)
    # convex mirror, object 20 cm, f = +20 cm: virtual, erect image at +10 cm
    v = _v("convex_mirror", "-20", "20")
    assert v == 10 and -v / Fraction(-20) == Fraction(1, 2)
    # convex lens, object 30 cm, f = +10 cm: real image on the far side at +15 cm, inverted
    v = _v("convex_lens", "-30", "10")
    assert v == 15 and v / Fraction(-30) == Fraction(-1, 2)
    # concave lens, object 30 cm, f = -10 cm: virtual image on the object side at -7.5 cm, erect
    v = _v("concave_lens", "-30", "-10")
    assert v == Fraction(-15, 2) and v / Fraction(-30) == Fraction(1, 4)


def test_both_methods_apply_the_convention_to_a_stem_with_only_magnitudes():
    spec = {
        "physics": {
            "model": "LIGHT.MIRROR_FORMULA", "variant": "v_from_uf", "find": "v",
            "answer_unit": "cm", "device": "concave_mirror",
            "given": {"u": {"value": "30", "unit": "cm", "role": "object_distance"},
                      "f": {"value": "10", "unit": "cm", "role": "focal"}},
        }
    }  # fmt: skip
    expect = {"values": {"v": "-15"}, "unit": "cm"}
    assert ClosedForm().solve(spec) == expect and SympyLaws().solve(spec) == expect


def test_a_sign_error_in_the_stem_is_caught_by_the_other_method():
    spec = {
        "physics": {
            "model": "LIGHT.MIRROR_FORMULA", "variant": "v_from_uf", "find": "v",
            "answer_unit": "cm", "device": "convex_mirror",
            "given": {"u": {"value": "30", "unit": "cm", "role": "object_distance"},
                      "f": {"value": "10", "unit": "cm", "role": "focal"}},
        }
    }  # fmt: skip
    assert ClosedForm().solve(spec) == SympyLaws().solve(spec)
    assert ClosedForm().solve(spec)["values"]["v"] == "7.5"  # virtual, behind the mirror
