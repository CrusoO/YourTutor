"""Worked example lane (test data for the loop, not content for students).

Backward construction: choose integer roots and a leading coefficient, expand to a x^2 + b x + c,
solve forward with two independent methods, verify with the kernel, certify the whole box.
Every number in the options is derived from the parameters, so the key cannot drift from the model.
"""

from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction
from typing import Any

from app.factory.lanes.reference import QuadraticFormula, RationalRootScan
from app.factory.registry import ItemContext, register_lane

TEMPLATE: dict[str, Any] = {
    "id": "TPL2.MATHS.QUAD.INT_ROOTS",
    "schema": "factory-template/1",
    "lane": "maths",
    "skill_id": "MATH.ALG.QUAD.FACTORISE",
    "box": {
        "a": {"choices": [1, 2, 3]},
        "r1": {"min": -9, "max": 9},
        "r2": {"min": -9, "max": 9},
    },
    "syllabus": {
        "grade": 10,
        "chapter_ref": "cbse.10.maths.quadratic",
        "skill_id": "MATH.ALG.QUAD.FACTORISE",
        "allowed_methods": ["factorise_quadratic", "quadratic_formula"],
        "forbidden_content": ["calculus", "complex_numbers"],
        "number_domain": "integers",
    },
}


def _term(coeff: int, power: str, first: bool) -> str:
    if coeff == 0:
        return ""
    sign = "-" if coeff < 0 else ("" if first else "+")
    mag = abs(coeff)
    body = (str(mag) if (mag != 1 or not power) else "") + power
    return f"{sign}{body}" if first else f" {sign} {body}"


def _answer(roots: list[int | Fraction]) -> dict[str, Any]:
    ordered = sorted({Fraction(r) for r in roots})
    return {"roots": [str(r) for r in ordered], "count": len(ordered)}


def _text(answer: dict[str, Any]) -> str:
    return " or ".join(f"x = {r}" for r in answer["roots"])


class MathsQuadraticLane:
    name = "maths"
    domain = "algebra"

    def box(self, template: Mapping[str, Any]) -> Mapping[str, Mapping[str, Any]]:
        return template["box"]  # type: ignore[no-any-return]

    def _parts(self, p: Mapping[str, Any]) -> tuple[list[int], dict[str, Any], dict[str, dict]]:
        a, r1, r2 = p["a"], p["r1"], p["r2"]
        coeffs = [a * r1 * r2, -a * (r1 + r2), a]
        key = _answer([r1, r2])
        wrong: dict[str, dict] = {
            "sign_error": _answer([-r1, -r2]),
            "one_root_only": _answer([r1]),
            "sum_product_confusion": _answer([r1 + r2, r1 * r2]),
        }
        return coeffs, key, wrong

    def well_posed(self, template: Mapping[str, Any], params: Mapping[str, Any]) -> str | None:
        if params["r1"] >= params["r2"]:
            return "needs_two_distinct_roots_in_order"
        if 0 in (params["r1"], params["r2"]):
            return "zero_root_is_a_different_skill"
        _, key, wrong = self._parts(params)
        values = [str(v) for v in wrong.values()]
        if len(set(values)) != 3 or str(key) in values:
            return "distractor_collision"
        return None

    def render(self, template: Mapping[str, Any], params: Mapping[str, Any]) -> ItemContext:
        coeffs, key, wrong = self._parts(params)
        c, b, a = coeffs
        equation = _term(a, "x^2", True) + _term(b, "x", False) + _term(c, "", False)
        options = [{"id": "key", "value": key, "text": _text(key), "procedure": "correct"}]
        options += [
            {"id": f"d{i}", "value": v, "text": _text(v), "procedure": name}
            for i, (name, v) in enumerate(wrong.items(), start=1)
        ]
        return ItemContext(
            item_id=f"{template['id']}.a{params['a']}.r{params['r1']}.{params['r2']}".replace(
                "-", "m"
            ),
            lane="maths",
            spec={"domain": "algebra", "kind": "polynomial", "lhs": coeffs, "rhs": []},
            answer=key,
            witness={
                "split": {
                    "lead": params["a"],
                    "roots": [[params["r1"], 1], [params["r2"], 1]],
                }
            },
            stem=f"Solve the equation {equation} = 0.",
            hints=[
                "Try to split the expression into two brackets that multiply together.",
                "A product is zero only when one of its brackets is zero.",
                "Put each value of x back into the equation to check it.",
            ],
            skill_ids=[template["skill_id"]],
            difficulty=0.55,
            role="procedure",
            steps=[
                "Write the left side as two brackets that multiply together.",
                "A product is zero only when one bracket is zero, so set each bracket to zero.",
                f"This gives {_text(key)}.",
            ],
            prediction="How many different values of x do you expect?",
            options=options,
            key_option="key",
            answer_tokens=list(key["roots"]),
            provenance={"original": True},
            syllabus=dict(template["syllabus"]),
            methods=[QuadraticFormula(), RationalRootScan()],
        )

    def check_student_answer(self, item: ItemContext, response: str) -> bool:
        try:
            given = {
                Fraction(part.strip().removeprefix("x=").strip()) for part in response.split(",")
            }
        except (ValueError, ZeroDivisionError):
            return False
        return given == {Fraction(r) for r in item.answer["roots"]}


LANE = register_lane(MathsQuadraticLane())
