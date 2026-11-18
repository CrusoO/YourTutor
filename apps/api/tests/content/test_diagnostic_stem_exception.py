"""The two-shape exception for diagnostic stems is a short, explicit list."""

from __future__ import annotations

from app.content.validator import STEM_MIN_DIAGNOSTIC, STEM_MIN_DIAGNOSTIC_TWO_SHAPES


def test_exception_list_is_small_and_named() -> None:
    assert STEM_MIN_DIAGNOSTIC == 3
    assert STEM_MIN_DIAGNOSTIC_TWO_SHAPES == {
        "MATH.ALG.QUAD.MODEL_NUMBERS",
        "MATH.ALG.QUAD.SOLVE_FACTORISE_MONIC",
    }
