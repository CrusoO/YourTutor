"""Author the four S1a draft lessons into content/lessons/.

Run from apps/api: `PYTHONPATH=. python scripts/write_s1a_lessons.py`. English only, authored text:
no machine translation, status draft. The first lesson is ported from the approved prototype
(docs/prototypes/balancing-equations-lesson.html). Every scene carries skill_id and source_ref.
"""

from __future__ import annotations

from typing import Any

import yaml

from app.lessons.schema import validate_lesson_dict
from app.registries.paths import repo_root

OUT = repo_root() / "content" / "lessons"


def en(text: str) -> dict[str, str]:
    return {"en": text}


def text(x: float, y: float, size: float, label: str, color: str | None = None) -> dict[str, Any]:
    action: dict[str, Any] = {"kind": "write_text", "x": x, "y": y, "size": size, "text": label}
    if color:
        action["color"] = color
    return action


def option(label: str, correct: bool, feedback: str | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {"text": en(label), "correct": correct}
    if feedback:
        row["feedback"] = en(feedback)
    return row


def ask(question: str, options: list[dict[str, Any]]) -> dict[str, Any]:
    return {"kind": "pause_and_ask", "question": en(question), "options": options}


def step(caption: str, *actions: dict[str, Any]) -> dict[str, Any]:
    return {"caption": en(caption), "actions": list(actions)}


def balance(
    left_boxes: int, left_weights: int, right_weights: int, box_weight: int
) -> dict[str, int]:
    return {
        "left_boxes": left_boxes,
        "left_weights": left_weights,
        "right_boxes": 0,
        "right_weights": right_weights,
        "box_weight": box_weight,
    }


def lesson(
    lesson_id: str,
    skill_id: str,
    title: str,
    source_ref: str,
    alt: str,
    beats: list[dict[str, Any]],
) -> dict[str, Any]:
    for beat in beats:
        if beat["kind"] == "explain_scene":
            scene = beat["scene"]
            scene["id"] = f"SCENE.{lesson_id.split('.', 1)[1]}.EXPLAIN"
            scene["skill_id"] = skill_id
            scene["source_ref"] = source_ref
            scene["alt"] = en(alt)
    return {
        "id": lesson_id,
        "skill_id": skill_id,
        "title": en(title),
        "source_ref": source_ref,
        "status": "draft",
        "beats": beats,
    }


def build() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}

    # ---- 1. two-step equations (ported from the prototype) ------------------------------------
    out["two_step_balancing"] = lesson(
        "LESSON.TWO_STEP",
        "MATH.ALG.LIN1.SOLVE_TWO_STEP",
        "Balancing equations",
        "NOTE.LIN1.TWO_STEP",
        "Whiteboard showing 2x + 3 = 11 solved step by step",
        [
            {
                "kind": "predict",
                "prompt": en("How heavy is one box?"),
                "figure": balance(2, 3, 11, 4),
                "choices": [
                    {"value": "3", "text": en("3 kg")},
                    {"value": "4", "text": en("4 kg")},
                    {"value": "5", "text": en("5 kg")},
                    {"value": "7", "text": en("7 kg")},
                ],
                "reveal": en("Hold on to that guess. Next, you will see how to check it."),
            },
            {
                "kind": "explore",
                "title": en("Try it on the balance"),
                "intro": en(
                    "The balance is level. Each blue weight is 1 kg. Both yellow boxes weigh the same."
                ),
                "widget": {
                    "type": "balance_scale",
                    "widget_id": "W.TWO_STEP.BALANCE",
                    "prompt": en(
                        "Tap weights to take them off. Keep it level. Goal: one box alone on the left."
                    ),
                    "success": en(
                        "One box balances 4 weights, so one box weighs 4 kg. Same answer as the whiteboard: x = 4."
                    ),
                    "hint": en(
                        "Take the same number off both sides, then split both sides in half."
                    ),
                    "params": balance(2, 3, 11, 4),
                },
            },
            {
                "kind": "explain_scene",
                "title": en("Watch it worked out"),
                "scene": {
                    "canvas": {"width": 340, "height": 290},
                    "steps": [
                        step(
                            "The balance is level. Left: 2 boxes and 3 one-kilo weights. Right: 11 weights. In maths we write it as 2x + 3 = 11.",
                            text(170, 52, 36, "2x + 3 = 11"),
                            text(170, 80, 15, "x = weight of one box", "muted"),
                        ),
                        step(
                            "Take 3 weights off both sides. Same amount from each side, so it stays level.",
                            text(152, 112, 22, "− 3", "red"),
                            text(244, 112, 22, "− 3", "red"),
                        ),
                        step(
                            "Yes. 2 boxes now balance 8 weights: 2x = 8.",
                            ask(
                                "Your turn. After taking 3 off both sides, what is left?",
                                [
                                    option("2x = 8", True),
                                    option(
                                        "2x = 14", False, "We took 3 away, so 11 − 3 = 8, not 14."
                                    ),
                                    option(
                                        "x = 8",
                                        False,
                                        "The 2 boxes are still on the left, so it is 2x, not x.",
                                    ),
                                ],
                            ),
                            text(170, 152, 32, "2x = 8"),
                        ),
                        step(
                            "Two boxes weigh 8. Split both sides into 2 equal parts. One box weighs 4.",
                            text(141, 186, 22, "÷ 2", "blue"),
                            text(206, 186, 22, "÷ 2", "blue"),
                            {"kind": "highlight", "x": 116, "y": 202, "w": 108, "h": 44},
                            text(170, 236, 36, "x = 4"),
                        ),
                        step(
                            "Always check. Put 4 back in: 2 × 4 + 3 = 11. It balances, so x = 4 is right.",
                            text(170, 274, 17, "check: 2 × 4 + 3 = 11 ✓", "green"),
                        ),
                    ],
                },
                "final_caption": en(
                    "That is the whole method: do the same to both sides until the box is alone. Now try it yourself."
                ),
            },
            {
                "kind": "worked_example",
                "title": en("Another one, step by step"),
                "problem": en("Solve 5x − 4 = 21."),
                "steps": [
                    en("Add 4 to both sides to undo the − 4: 5x = 25."),
                    en("Split both sides into 5 equal parts: x = 5."),
                    en("Check: 5 × 5 − 4 = 21. It balances."),
                ],
            },
            {
                "kind": "explore",
                "title": en("See it on a graph"),
                "widget": {
                    "type": "function_graph",
                    "widget_id": "W.TWO_STEP.GRAPH",
                    "prompt": en(
                        "The line shows how heavy the left side is for any box weight x. Drag the dot until the left side reaches 11."
                    ),
                    "success": en(
                        "The line reaches 11 exactly at x = 4. The balance, the whiteboard and the graph all give the same answer."
                    ),
                    "hint": en("If the left side is lighter than 11, slide to the right."),
                    "params": {
                        "slope": 2,
                        "intercept": 3,
                        "target_y": 11,
                        "x_min": 0,
                        "x_max": 8,
                        "step": 0.1,
                        "label": "y = 2x + 3",
                        "x_label": en("box weight x"),
                        "target_label": en("right side = 11"),
                    },
                },
            },
            {"kind": "check", "prompt": en("Now solve one yourself.")},
        ],
    )

    # ---- 2. one-step equations ----------------------------------------------------------------
    out["one_step_balance"] = lesson(
        "LESSON.ONE_STEP",
        "MATH.ALG.LIN1.SOLVE_ONE_STEP",
        "One step to find x",
        "NOTE.LIN1.ONE_STEP",
        "Whiteboard showing x + 5 = 9 solved in one step",
        [
            {
                "kind": "predict",
                "prompt": en("The balance is level. How heavy is one box?"),
                "figure": balance(1, 5, 9, 4),
                "choices": [
                    {"value": "3", "text": en("3 kg")},
                    {"value": "4", "text": en("4 kg")},
                    {"value": "5", "text": en("5 kg")},
                    {"value": "9", "text": en("9 kg")},
                ],
                "reveal": en("Keep that guess in mind. Now you will check it."),
            },
            {
                "kind": "explore",
                "title": en("Try it on the balance"),
                "widget": {
                    "type": "balance_scale",
                    "widget_id": "W.ONE_STEP.BALANCE",
                    "prompt": en(
                        "Tap weights to take them off. Keep it level. Goal: the box alone on the left."
                    ),
                    "success": en("The box balances 4 weights, so x = 4."),
                    "hint": en("Take the same number of weights off both sides."),
                    "params": balance(1, 5, 9, 4),
                },
            },
            {
                "kind": "explain_scene",
                "title": en("Watch it worked out"),
                "scene": {
                    "canvas": {"width": 340, "height": 290},
                    "steps": [
                        step(
                            "One box and 5 weights balance 9 weights. In maths: x + 5 = 9.",
                            text(170, 52, 36, "x + 5 = 9"),
                        ),
                        step(
                            "Take 5 weights off both sides, so it stays level.",
                            text(152, 112, 22, "− 5", "red"),
                            text(244, 112, 22, "− 5", "red"),
                        ),
                        step(
                            "Yes. The box balances 4 weights.",
                            ask(
                                "After taking 5 off both sides, what is left on the right?",
                                [
                                    option("4", True),
                                    option("14", False, "We took 5 away, so we subtract: 9 − 5."),
                                    option(
                                        "5", False, "That is what we took off, not what is left."
                                    ),
                                ],
                            ),
                            text(170, 170, 36, "x = 4"),
                            {"kind": "highlight", "x": 116, "y": 136, "w": 108, "h": 44},
                        ),
                        step(
                            "Check: put 4 back in. 4 + 5 = 9. It balances.",
                            text(170, 250, 17, "check: 4 + 5 = 9 ✓", "green"),
                        ),
                    ],
                },
                "final_caption": en("One step: undo the + 5 by taking 5 off both sides."),
            },
            {
                "kind": "worked_example",
                "title": en("Another one"),
                "problem": en("Solve x − 7 = 3."),
                "steps": [
                    en("Add 7 to both sides to undo the − 7: x = 10."),
                    en("Check: 10 − 7 = 3. It balances."),
                ],
            },
            {"kind": "check", "prompt": en("Now solve one yourself.")},
        ],
    )

    # ---- 3. inverse operations ----------------------------------------------------------------
    out["inverse_operations"] = lesson(
        "LESSON.INVERSE",
        "MATH.ALG.INVERSE_OPERATIONS",
        "Undoing an operation",
        "NOTE.ALG.INVERSE",
        "Whiteboard showing how subtracting 9 undoes adding 9 in x + 9 = 20",
        [
            {
                "kind": "predict",
                "prompt": en("A box and 9 weights balance 20 weights. How heavy is one box?"),
                "figure": balance(1, 9, 20, 11),
                "choices": [
                    {"value": "9", "text": en("9 kg")},
                    {"value": "11", "text": en("11 kg")},
                    {"value": "20", "text": en("20 kg")},
                    {"value": "29", "text": en("29 kg")},
                ],
                "reveal": en("Hold on to that guess. Now see how to undo the + 9."),
            },
            {
                "kind": "explore",
                "title": en("Undo it on the balance"),
                "widget": {
                    "type": "balance_scale",
                    "widget_id": "W.INVERSE.BALANCE",
                    "prompt": en(
                        "Tap weights to take them off. Keep it level. Goal: the box alone on the left."
                    ),
                    "success": en(
                        "The box balances 11 weights. Taking 9 off both sides undid the + 9."
                    ),
                    "hint": en("Take the same number of weights off both sides."),
                    "params": balance(1, 9, 20, 11),
                },
            },
            {
                "kind": "explain_scene",
                "title": en("Watch the undo"),
                "scene": {
                    "canvas": {"width": 340, "height": 290},
                    "steps": [
                        step(
                            "x + 9 = 20. Someone added 9 to the box. We want the box alone.",
                            text(170, 52, 36, "x + 9 = 20"),
                        ),
                        step(
                            "Do the opposite of adding 9, to both sides.",
                            ask(
                                "Which operation undoes adding 9?",
                                [
                                    option("subtract 9", True),
                                    option(
                                        "add 9",
                                        False,
                                        "Adding again makes it bigger. It does not undo anything.",
                                    ),
                                    option(
                                        "multiply by 9",
                                        False,
                                        "Multiplying is not the opposite of adding.",
                                    ),
                                ],
                            ),
                            text(152, 112, 22, "− 9", "red"),
                            text(244, 112, 22, "− 9", "red"),
                        ),
                        step(
                            "The box is alone: x = 11.",
                            text(170, 170, 36, "x = 11"),
                            {"kind": "highlight", "x": 106, "y": 136, "w": 128, "h": 44},
                        ),
                        step(
                            "Check: 11 + 9 = 20. It balances.",
                            text(170, 250, 17, "check: 11 + 9 = 20 ✓", "green"),
                        ),
                    ],
                },
                "final_caption": en(
                    "Every operation has an opposite. Use it on both sides to get x alone."
                ),
            },
            {
                "kind": "worked_example",
                "title": en("Another one"),
                "problem": en("Solve x − 8 = 12."),
                "steps": [
                    en("The opposite of subtracting 8 is adding 8. Add 8 to both sides: x = 20."),
                    en("Check: 20 − 8 = 12. It balances."),
                ],
            },
            {"kind": "check", "prompt": en("Now solve one yourself.")},
        ],
    )

    # ---- 4. fractions on x --------------------------------------------------------------------
    out["fraction_coefficient"] = lesson(
        "LESSON.FRACTION",
        "MATH.ALG.LIN1.FRACTION_COEFF",
        "Equations with a fraction of x",
        "NOTE.LIN1.FRACTION",
        "Whiteboard showing x/3 + 2 = 9 solved step by step",
        [
            {
                "kind": "predict",
                "prompt": en(
                    "A number divided by 3, plus 2, makes 9. What do you think the number is?"
                ),
                "choices": [
                    {"value": "15", "text": en("15")},
                    {"value": "18", "text": en("18")},
                    {"value": "21", "text": en("21")},
                    {"value": "27", "text": en("27")},
                ],
                "reveal": en("Keep that guess. Now you will test it on a graph."),
            },
            {
                "kind": "explore",
                "title": en("Find it on a graph"),
                "widget": {
                    "type": "function_graph",
                    "widget_id": "W.FRACTION.GRAPH",
                    "prompt": en(
                        "The line shows x divided by 3, plus 2. Drag the dot until it reaches 9."
                    ),
                    "success": en("The line reaches 9 exactly at x = 21."),
                    "hint": en("If the line is lower than 9, slide to the right."),
                    "params": {
                        "slope": 0.3333333333333333,
                        "intercept": 2,
                        "target_y": 9,
                        "x_min": 0,
                        "x_max": 30,
                        "step": 1,
                        "label": "y = x/3 + 2",
                        "x_label": en("the number x"),
                        "target_label": en("target = 9"),
                    },
                },
            },
            {
                "kind": "explain_scene",
                "title": en("Watch it worked out"),
                "scene": {
                    "canvas": {"width": 340, "height": 290},
                    "steps": [
                        step(
                            "x divided by 3, plus 2, equals 9. In maths: x/3 + 2 = 9.",
                            text(170, 52, 34, "x/3 + 2 = 9"),
                        ),
                        step(
                            "First take 2 off both sides: x/3 = 7.",
                            text(152, 112, 22, "− 2", "red"),
                            text(244, 112, 22, "− 2", "red"),
                            text(170, 148, 32, "x/3 = 7"),
                        ),
                        step(
                            "Multiplying by 3 undoes dividing by 3.",
                            ask(
                                "To undo ÷ 3, what do we do to both sides?",
                                [
                                    option("multiply by 3", True),
                                    option(
                                        "divide by 3",
                                        False,
                                        "Dividing again would make x even smaller.",
                                    ),
                                    option("add 3", False, "Adding does not undo dividing."),
                                ],
                            ),
                            text(152, 186, 22, "× 3", "blue"),
                            text(244, 186, 22, "× 3", "blue"),
                        ),
                        step(
                            "So x = 21.",
                            text(170, 236, 36, "x = 21"),
                            {"kind": "highlight", "x": 106, "y": 202, "w": 128, "h": 44},
                        ),
                        step(
                            "Check: 21 ÷ 3 + 2 = 7 + 2 = 9. It works.",
                            text(170, 274, 17, "check: 21 ÷ 3 + 2 = 9 ✓", "green"),
                        ),
                    ],
                },
                "final_caption": en("Undo the plus first, then undo the divide by multiplying."),
            },
            {
                "kind": "worked_example",
                "title": en("Another one"),
                "problem": en("Solve x/4 − 1 = 2."),
                "steps": [
                    en("Add 1 to both sides: x/4 = 3."),
                    en("Multiply both sides by 4: x = 12."),
                    en("Check: 12 ÷ 4 − 1 = 2. It works."),
                ],
            },
            {"kind": "check", "prompt": en("Now solve one yourself.")},
        ],
    )
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.yaml"):
        old.unlink()
    for name, data in build().items():
        errors = validate_lesson_dict(data)
        assert not errors, (name, errors)
        path = OUT / f"{name}.yaml"
        path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
