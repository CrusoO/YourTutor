from __future__ import annotations

import pytest

from app.content.math_parse import ParseError, normalize
from app.verifier.check import verify_response


def test_unicode_decimal_digits_normalize() -> None:
    assert normalize("५") == "5"
    assert normalize("৫") == "5"
    assert normalize("٤") == "4"
    assert normalize("๓") == "3"


def test_decimal_comma_profile() -> None:
    assert normalize("2,5", notation_profile="decimal_comma") == "2.5"
    assert verify_response("2,5", answer_sympy="2.5", notation_profile="decimal_comma")
    with pytest.raises(ParseError):
        normalize("2,5", notation_profile="default_ascii")
    assert verify_response("2,5", answer_sympy="2.5", notation_profile="default_ascii") is False
