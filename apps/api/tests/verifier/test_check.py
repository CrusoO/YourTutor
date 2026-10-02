from __future__ import annotations

from app.content.math_parse import ParseError, normalize, parse_math
from app.verifier.check import leak_check, verify_response


def test_allowlist_rejects_malicious_strings() -> None:
    for raw in ("__import__('os')", "os.system('id')", "x" * 80, "(" * 12 + "1" + ")" * 12):
        try:
            parse_math(raw)
            raise AssertionError(f"should reject {raw!r}")
        except ParseError:
            assert verify_response(raw, answer_sympy="5") is False


def test_normalises_digits_and_equation_form() -> None:
    assert normalize("५") == "5"
    assert normalize("৫") == "5"
    assert verify_response("x = 5", answer_sympy="5")
    assert verify_response("−3", answer_sympy="-3")


def test_dont_know_is_incorrect() -> None:
    assert verify_response("I don't know", answer_sympy="5") is False
    assert verify_response("idk", answer_sympy="yes") is False


def test_leak_check_levels() -> None:
    assert leak_check("The answer is 5", "5", level=1)
    assert leak_check("The answer is 5", "5", level=2)
    assert not leak_check("The answer is 5", "5", level=3)
    assert not leak_check("What undoes the operation?", "5", level=1)


def test_mcq_and_verify_kinds() -> None:
    assert verify_response(
        "yes",
        answer_sympy="yes",
        item_type="mcq",
        options=[{"id": "yes", "en": "Yes"}, {"id": "no", "en": "No"}],
        verify={"kind": "substitution", "equation": "2x + 1 = 9", "value": "4"},
    )
    assert verify_response(
        "every",
        answer_sympy="every",
        item_type="mcq",
        options=[
            {"id": "none", "en": "No solution"},
            {"id": "one", "en": "One solution"},
            {"id": "every", "en": "Every x works"},
        ],
        verify={"kind": "solution_count", "equation": "2(x + 3) = 2x + 6"},
    )
