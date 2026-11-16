"""The ONE sign convention of this lane: the Cartesian sign convention used in school.

Recorded as data so a test can pin it and every other module reads it from here. Origin at the
pole of a mirror or the optical centre of a lens. The direction of the incident light is
positive. Distances against the incident light are negative. Heights above the principal axis
are positive, below it negative.

    mirror formula        1/v + 1/u = 1/f      magnification  m = -v/u = h'/h
    thin lens formula     1/v - 1/u = 1/f      magnification  m =  v/u = h'/h
    power                 P = 1/f (f in metres), in dioptres

Real objects have u < 0. A concave mirror and a concave lens have negative f, a convex mirror and
a convex lens have positive f. A person must review this table before anything is served.
"""

from __future__ import annotations

SIGN_CONVENTION_VERSION = "1"

FOCAL_SIGN = {
    "concave_mirror": -1,
    "convex_mirror": +1,
    "convex_lens": +1,
    "concave_lens": -1,
}

# What sign a distance or a height gets, by its role, for a mirror and for a lens.
MIRROR_ROLE_SIGN = {
    "object_distance": -1,  # a real object stands in front of the mirror
    "image_real": -1,  # a real image forms in front of the mirror
    "image_virtual": +1,  # a virtual image is behind the mirror
    "height_object": +1,
    "height_image_erect": +1,
    "height_image_inverted": -1,
}
LENS_ROLE_SIGN = {
    "object_distance": -1,  # a real object is on the side the light comes from
    "image_real": +1,  # a real image forms on the far side
    "image_virtual": -1,  # a virtual image is on the same side as the object
    "height_object": +1,
    "height_image_erect": +1,
    "height_image_inverted": -1,
}
FORMULAS = {
    "mirror": "1/v + 1/u = 1/f",
    "lens": "1/v - 1/u = 1/f",
    "mirror_magnification": "m = -v/u",
    "lens_magnification": "m = v/u",
    "power": "P = 1/f",
}

SIGN_CONVENTION = {
    "name": "Cartesian sign convention (school form)",
    "version": SIGN_CONVENTION_VERSION,
    "reviewed": False,  # a person must review this table before any item is served
    "focal_sign": FOCAL_SIGN,
    "mirror_role_sign": MIRROR_ROLE_SIGN,
    "lens_role_sign": LENS_ROLE_SIGN,
    "formulas": FORMULAS,
}


def role_sign(device: str, role: str) -> int:
    """Sign for a quantity in its role. `device` is concave_mirror, convex_lens and so on."""
    if role in ("focal", "power"):
        return FOCAL_SIGN[device]
    table = MIRROR_ROLE_SIGN if device.endswith("mirror") else LENS_ROLE_SIGN
    return table[role]
