"""Write the Class 9 linear-equations seed chapter as YAML (English + reviewer placeholders)."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3] / "content"
NE = "<Nepali — to be filled by reviewer>"
AS = "<Assamese — to be filled by reviewer>"
BKT = {"p_init": 0.2, "p_learn": 0.15, "p_slip": 0.1, "p_guess": 0.2}

SKILLS = [
    ("MATH.ARITH.INTEGERS.OPERATIONS", "Operate with integers", [], []),
    (
        "MATH.ALG.INVERSE_OPERATIONS",
        "Use inverse operations",
        ["MATH.ARITH.INTEGERS.OPERATIONS"],
        ["MC.ALG.INVERSE_OP_WRONG_SIDE"],
    ),
    (
        "MATH.ALG.LIN1.TRANSLATE",
        "Translate words into a linear equation",
        ["MATH.ALG.INVERSE_OPERATIONS"],
        [],
    ),
    (
        "MATH.ALG.LIN1.SOLVE_ONE_STEP",
        "Solve one-step linear equations",
        ["MATH.ALG.INVERSE_OPERATIONS"],
        ["MC.ALG.INVERSE_OP_WRONG_SIDE", "MC.ALG.ADD_INSTEAD_SUBTRACT"],
    ),
    (
        "MATH.ALG.LIN1.SOLVE_TWO_STEP",
        "Solve two-step linear equations",
        ["MATH.ALG.LIN1.SOLVE_ONE_STEP"],
        ["MC.ALG.FORGET_BOTH_SIDES"],
    ),
    (
        "MATH.ALG.LIN1.SOLVE_MULTI",
        "Solve multi-step linear equations",
        ["MATH.ALG.LIN1.SOLVE_TWO_STEP"],
        ["MC.ALG.SIGN_ERROR"],
    ),
    (
        "MATH.ALG.LIN1.VARIABLES_BOTH_SIDES",
        "Solve equations with variables on both sides",
        ["MATH.ALG.LIN1.SOLVE_TWO_STEP"],
        ["MC.ALG.MOVE_TERM_WITHOUT_SIGN"],
    ),
    (
        "MATH.ALG.LIN1.BRACKETS",
        "Solve linear equations with brackets",
        ["MATH.ALG.LIN1.SOLVE_MULTI"],
        ["MC.ALG.DISTRIBUTE_WRONG"],
    ),
    (
        "MATH.ALG.LIN1.FRACTION_COEFF",
        "Solve linear equations with a fractional coefficient",
        ["MATH.ALG.LIN1.SOLVE_TWO_STEP"],
        ["MC.ALG.DIVIDE_ONE_TERM"],
    ),
    (
        "MATH.ALG.LIN1.WORD_PROBLEMS",
        "Solve linear word problems",
        ["MATH.ALG.LIN1.TRANSLATE", "MATH.ALG.LIN1.SOLVE_TWO_STEP"],
        [],
    ),
    (
        "MATH.ALG.LIN1.CHECK_SOLUTION",
        "Check whether a number solves an equation",
        ["MATH.ALG.LIN1.SOLVE_ONE_STEP"],
        [],
    ),
    (
        "MATH.ALG.LIN1.IDENTITIES",
        "Recognise identities and contradictions",
        ["MATH.ALG.LIN1.VARIABLES_BOTH_SIDES"],
        ["MC.ALG.SWAP_EQUALS"],
    ),
]

MISCONCEPTIONS = [
    (
        "MC.ALG.INVERSE_OP_WRONG_SIDE",
        "Applies the operation instead of its inverse",
        "To undo +a we subtract a; adding a again moves away from x.",
        "MATH.ALG.INVERSE_OPERATIONS",
    ),
    (
        "MC.ALG.ADD_INSTEAD_SUBTRACT",
        "Adds when subtraction is required",
        "The inverse of subtraction is addition, and the inverse of addition is subtraction.",
        "MATH.ALG.INVERSE_OPERATIONS",
    ),
    (
        "MC.ALG.FORGET_BOTH_SIDES",
        "Changes only one side of the equation",
        "An equation stays balanced only when the same operation is done to both sides.",
        "MATH.ALG.LIN1.SOLVE_ONE_STEP",
    ),
    (
        "MC.ALG.SIGN_ERROR",
        "Drops or flips a sign when rearranging",
        "When a term moves across the equals sign, its sign changes.",
        "MATH.ALG.LIN1.SOLVE_MULTI",
    ),
    (
        "MC.ALG.DISTRIBUTE_WRONG",
        "Distributes to only one term inside the brackets",
        "a(b + c) = ab + ac; both terms inside must be multiplied.",
        "MATH.ALG.LIN1.BRACKETS",
    ),
    (
        "MC.ALG.MOVE_TERM_WITHOUT_SIGN",
        "Moves a term across the equals sign without changing its sign",
        "x + 3 = 10 becomes x = 10 - 3, not x = 10 + 3.",
        "MATH.ALG.LIN1.VARIABLES_BOTH_SIDES",
    ),
    (
        "MC.ALG.DIVIDE_ONE_TERM",
        "Divides only one term instead of both sides",
        "To undo multiplication of the whole side, divide every term on both sides.",
        "MATH.ALG.LIN1.FRACTION_COEFF",
    ),
    (
        "MC.ALG.SWAP_EQUALS",
        "Treats both sides as interchangeable without checking identity",
        "If both sides simplify to the same expression, every x works; if they cannot, none do.",
        "MATH.ALG.LIN1.IDENTITIES",
    ),
]

YES_NO = [
    {"id": "yes", "en": "Yes", "ne": NE, "as": AS},
    {"id": "no", "en": "No", "ne": NE, "as": AS},
]
COUNT_OPTS = [
    {"id": "none", "en": "No solution", "ne": NE, "as": AS},
    {"id": "one", "en": "One solution", "ne": NE, "as": AS},
    {"id": "every", "en": "Every x works", "ne": NE, "as": AS},
]
IDK_OPT = {"id": "idk", "en": "I don't know", "ne": NE, "as": AS}


def with_idk(options: list[dict], pool: str) -> list[dict]:
    if pool != "diagnostic":
        return options
    if any(row["id"] == "idk" for row in options):
        return options
    return [*options, IDK_OPT]


def loc(en: str) -> dict[str, str]:
    return {"en": en, "ne": NE, "as": AS}


def dump(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def fmt_x(coeff: int) -> str:
    if coeff == 1:
        return "x"
    if coeff == -1:
        return "-x"
    return f"{coeff}x"


def hints(h1: str, h2: str, h3: str) -> list[dict]:
    return [
        {"level": 1, **loc(h1)},
        {"level": 2, **loc(h2)},
        {"level": 3, **loc(h3)},
    ]


def hints_undo(op_word: str, value: int) -> list[dict]:
    return hints(
        f"What is being done to x besides the {value}? How can you undo that?",
        f"Undo the {value} on both sides so the equation stays balanced.",
        f"{op_word} {value} on both sides, then simplify.",
    )


def item(
    item_id: str,
    skill: str,
    difficulty: float,
    pool: str,
    stem: str,
    answer: str,
    steps: list[str],
    hint_rows: list[dict],
    prediction: str,
    *,
    accept: list[str] | None = None,
    rules: list[dict] | None = None,
    verify: str | dict | None = None,
    type_: str = "expression",
    options: list[dict] | None = None,
    role: str = "procedure",
) -> dict:
    data = {
        "id": item_id,
        "skill_ids": [skill],
        "difficulty": difficulty,
        "type": type_,
        "pool": pool,
        "role": role,
        "stem": loc(stem),
        "answer": {"sympy": str(answer), "accept": accept or [str(answer), f"x={answer}"]},
        "solution_steps": [loc(s) for s in steps],
        "hints": hint_rows,
        "prediction_prompt": loc(prediction),
        "misconception_rules": rules or [],
        "reviewed_by": None,
        "status": "draft",
    }
    if verify is not None:
        data["verify"] = verify
    if options:
        data["options"] = options
    return data


def write_skills() -> list[str]:
    ids = []
    for sid, title, prereqs, mcs in SKILLS:
        ids.append(sid)
        dump(
            ROOT / "skills" / "math" / f"{sid.split('.')[-1].lower()}.yaml",
            {
                "id": sid,
                "title": loc(title),
                "grade_band": [8, 9],
                "subject": "math",
                "prerequisites": prereqs,
                "related": [],
                "misconceptions": mcs,
                "bkt": BKT,
                "status": "draft",
            },
        )
    return ids


def write_misconceptions() -> None:
    for mid, title, expl, remedial in MISCONCEPTIONS:
        dump(
            ROOT / "misconceptions" / "math" / f"{mid.split('.')[-1].lower()}.yaml",
            {
                "id": mid,
                "title": loc(title),
                "explanation": loc(expl),
                "remedial_skill": remedial,
                "status": "draft",
            },
        )


def integers(spec: tuple, pool: str, item_id: str, difficulty: float) -> dict:
    left, right = spec
    answer = left - right
    style = (left + right) % 3
    if style == 0:
        stem = f"Compute {left} - {right}."
        h1 = f"Is {left} larger than {right}? Are we taking away or adding?"
        h2 = f"Start at {left} and move {right} steps left on the number line."
    elif style == 1:
        stem = f"Compute {left} + (-{right})."
        h1 = f"Adding -{right} to {left} is the same as which subtraction?"
        h2 = f"Rewrite {left} + (-{right}) as a single subtraction, then evaluate."
    else:
        stem = f"Compute -{right} + {left}."
        h1 = f"You start at -{right}. Which way do you move to add {left}?"
        h2 = f"Adding {left} to -{right} lands where on the number line?"
    return item(
        item_id,
        "MATH.ARITH.INTEGERS.OPERATIONS",
        difficulty,
        pool,
        stem,
        str(answer),
        [f"{left} minus {right} is {answer}.", f"x = {answer}"],
        hints(h1, h2, f"Take {right} away from {left}."),
        "Will the result be smaller than the first number?",
    )


INVERSE_HINTS = [
    (
        "Which operation puts x back together after it was changed?",
        "Think of the inverse pair: add versus subtract.",
    ),
    (
        "x was shifted. What undoes a shift on x?",
        "The inverse operation is the opposite direction on the number line.",
    ),
    (
        "Ask: what cancels the change that was applied to x?",
        "Write the inverse operation without evaluating a value yet.",
    ),
    ("Is the change on x an add or a subtract?", "Name the inverse family before you pick a size."),
    (
        "x should reappear alone. What kind of move does that?",
        "Addition undoes subtraction; subtraction undoes addition.",
    ),
    (
        "Cover the constant and look only at the operation on x.",
        "The inverse is the other member of that add/subtract pair.",
    ),
    (
        "What happened to x? What single change brings it back to x?",
        "Name the opposite of the change you see, then apply that opposite.",
    ),
    (
        "The goal is to recover x, not to compute a new expression.",
        "Choose the inverse operation first, then the matching amount.",
    ),
    ("Did someone add to x or take away from x?", "Undo that family of operations."),
    (
        "Imagine x wrapped in one operation. How do you unwrap it?",
        "Unwrap with the inverse, not the same operation again.",
    ),
    (
        "Which button on a calculator would cancel this step on x?",
        "Plus and minus cancel; they do not repeat.",
    ),
    (
        "x is almost isolated. What last inverse do you need?",
        "State the inverse operation in words before you apply it.",
    ),
]


def inverse(spec: tuple, pool: str, item_id: str, difficulty: float) -> dict:
    kind, value = spec
    if kind == "add":
        stem = (
            f"Adding what to x - {value} returns x?"
            if value % 2 == 0
            else f"What number do you add to x - {value} to get x again?"
        )
        steps = [
            f"The inverse of subtracting {value} is adding {value}.",
            f"x = {value}",
        ]
        verify = {"kind": "equation", "expr": f"x - {value} + y = x", "unknown": "y"}
        hint3 = f"Add {value} to cancel subtracting {value}."
    else:
        stem = f"What number do you subtract from x + {value} to get x again?"
        steps = [
            f"The inverse of adding {value} is subtracting {value}.",
            f"x = {value}",
        ]
        verify = {"kind": "equation", "expr": f"x + {value} - y = x", "unknown": "y"}
        hint3 = f"Subtract {value} to cancel adding {value}."
    h1, h2 = INVERSE_HINTS[(value - 1) % len(INVERSE_HINTS)]
    return item(
        item_id,
        "MATH.ALG.INVERSE_OPERATIONS",
        difficulty,
        pool,
        stem,
        str(value),
        steps,
        hints(h1, h2, hint3),
        "Is the inverse larger than 1?",
        verify=verify,
    )


def translate(spec: tuple, pool: str, item_id: str, difficulty: float) -> dict:
    addend, target = spec
    answer = target - addend
    style = addend % 3
    if style == 0:
        stem = f"A number plus {addend} equals {target}. What is the number?"
        equation = f"x + {addend} = {target}"
        h1 = f"Write 'a number plus {addend}' as an expression equal to {target}."
        h2 = f"Once you write x + {addend} = {target}, undo the {addend}."
    elif style == 1:
        stem = f"{addend} more than a number is {target}. What is the number?"
        equation = f"x + {addend} = {target}"
        h1 = f"'{addend} more than a number' means you add {addend} to x."
        h2 = f"Set that sum equal to {target}, then isolate the number."
    else:
        stem = f"The sum of a number and {addend} is {target}. Find the number."
        equation = f"x + {addend} = {target}"
        h1 = f"Sum of a number and {addend} is x + {addend} = {target}."
        h2 = f"To undo adding {addend}, do the inverse to {target} as well."
    return item(
        item_id,
        "MATH.ALG.LIN1.TRANSLATE",
        difficulty,
        pool,
        stem,
        str(answer),
        [f"The sentence becomes {equation}.", f"x = {answer}"],
        hints(h1, h2, f"Take {addend} away from {target} to leave the number."),
        f"Is the number smaller than {target}?",
        verify=equation,
    )


def one_step(spec: tuple, pool: str, item_id: str, difficulty: float) -> dict:
    addend, answer = spec
    total = answer + addend
    style = addend % 3
    if style == 0:
        stem = f"Solve for x: x + {addend} = {total}"
        h1 = f"x has {addend} added to it. What undoes that single step?"
        h2 = f"Subtract {addend} from both sides."
        steps = [
            f"We want x alone. Subtract {addend} from both sides.",
            f"x + {addend} - {addend} = {total} - {addend}",
            f"x = {answer}",
        ]
        h3 = f"Rewrite as x = {total} - {addend}, then evaluate."
        wrong = str(total + addend)
    elif style == 1:
        rhs = answer - addend
        stem = f"Solve for x: x - {addend} = {rhs}"
        h1 = f"x has {addend} subtracted from it. What puts x back alone?"
        h2 = f"Add {addend} to both sides."
        steps = [
            f"Add {addend} to both sides.",
            f"x = {answer}",
        ]
        h3 = f"Rewrite as x = {rhs} + {addend}, then evaluate."
        wrong = str(rhs - addend)
    else:
        stem = f"Solve for x: {addend}x = {addend * answer}"
        h1 = f"x is multiplied by {addend}. What single step isolates x?"
        h2 = f"Divide both sides by {addend}."
        steps = [
            f"Divide both sides by {addend}.",
            f"x = {answer}",
        ]
        h3 = f"{addend * answer} divided by {addend} is the value of x."
        wrong = str(addend * answer + addend)
    return item(
        item_id,
        "MATH.ALG.LIN1.SOLVE_ONE_STEP",
        difficulty,
        pool,
        stem,
        str(answer),
        steps,
        hints(h1, h2, h3),
        f"Before solving: will x be smaller than {total}? Why?",
        rules=[{"id": "MC.ALG.INVERSE_OP_WRONG_SIDE", "when_answer_equals": [wrong]}],
    )


def two_step(spec: tuple, pool: str, item_id: str, difficulty: float) -> dict:
    coeff, added, answer = spec
    style = added % 3
    if style == 0:
        rhs = coeff * answer + added
        stem = f"Solve for x: {fmt_x(coeff)} + {added} = {rhs}"
        h1 = f"{fmt_x(coeff)} then plus {added}. Which of those two do you undo first?"
        h2 = f"After undoing the + {added}, you still have to undo the × {coeff}."
        h3 = f"First subtract {added} on both sides, then divide by {coeff}."
        steps = [
            f"Subtract {added} from both sides.",
            f"{fmt_x(coeff)} = {rhs - added}",
            f"Divide both sides by {coeff}.",
            f"x = {answer}",
        ]
    elif style == 1:
        rhs = coeff * answer - added
        stem = f"Solve for x: {fmt_x(coeff)} - {added} = {rhs}"
        h1 = f"{fmt_x(coeff)} then minus {added}. Undo the − {added} first."
        h2 = f"After undoing the − {added}, you still have to undo the × {coeff}."
        h3 = f"First add {added} on both sides, then divide by {coeff}."
        steps = [
            f"Add {added} to both sides.",
            f"{fmt_x(coeff)} = {rhs + added}",
            f"Divide both sides by {coeff}.",
            f"x = {answer}",
        ]
    else:
        rhs = coeff * answer + added
        stem = f"Solve for x: {added} + {fmt_x(coeff)} = {rhs}"
        h1 = f"The + {added} is written first, then {fmt_x(coeff)}. Same two-step undo."
        h2 = f"After undoing the + {added}, you still have to undo the × {coeff}."
        h3 = f"First subtract {added} on both sides, then divide by {coeff}."
        steps = [
            f"Subtract {added} from both sides.",
            f"{fmt_x(coeff)} = {rhs - added}",
            f"Divide both sides by {coeff}.",
            f"x = {answer}",
        ]
    return item(
        item_id,
        "MATH.ALG.LIN1.SOLVE_TWO_STEP",
        difficulty,
        pool,
        stem,
        str(answer),
        steps,
        hints(h1, h2, h3),
        "Will x be a whole number? Why do you think that?",
    )


def multi(spec: tuple, pool: str, item_id: str, difficulty: float) -> dict:
    a, b, c, answer = spec
    rhs = (a + c) * answer + b
    sign = "+" if b >= 0 else "-"
    b_abs = abs(b)
    style = abs(a + c + b) % 3
    if style == 0:
        stem = f"Solve for x: {fmt_x(a)} {sign} {b_abs} + {fmt_x(c)} = {rhs}"
    elif style == 1:
        stem = f"Solve for x: {fmt_x(c)} + {fmt_x(a)} {sign} {b_abs} = {rhs}"
    else:
        stem = f"Solve for x: {fmt_x(a)} + {fmt_x(c)} {sign} {b_abs} = {rhs}"
    return item(
        item_id,
        "MATH.ALG.LIN1.SOLVE_MULTI",
        difficulty,
        pool,
        stem,
        str(answer),
        [
            f"Combine like terms: {fmt_x(a + c)} {sign} {b_abs} = {rhs}.",
            f"Move the constant, then divide by {a + c}.",
            f"x = {answer}",
        ],
        hints(
            f"The left side has {fmt_x(a)} and {fmt_x(c)}. Gather those first.",
            f"After combining, undo the {b_abs} then divide by {a + c}.",
            (
                f"Rewrite as {fmt_x(a + c)} {sign} {b_abs} = {rhs}. Move {b_abs}, then divide by "
                f"{a + c}."
            ),
        ),
        "Are there like terms you can gather first?",
    )


def both_sides(spec: tuple, pool: str, item_id: str, difficulty: float) -> dict:
    left_c, right_c, left_b, answer = spec
    right_b = (left_c - right_c) * answer + left_b
    style = left_b % 3
    if style == 0:
        stem = f"Solve for x: {fmt_x(left_c)} + {left_b} = {fmt_x(right_c)} + {right_b}"
    elif style == 1:
        stem = f"Solve for x: {left_b} + {fmt_x(left_c)} = {right_b} + {fmt_x(right_c)}"
    else:
        stem = (
            f"Solve for x: {fmt_x(left_c)} - {left_b} = {fmt_x(right_c)} + {right_b - 2 * left_b}"
        )
        right_b = right_b - 2 * left_b
    return item(
        item_id,
        "MATH.ALG.LIN1.VARIABLES_BOTH_SIDES",
        difficulty,
        pool,
        stem,
        str(answer),
        [
            f"Subtract {fmt_x(right_c)} from both sides.",
            f"{fmt_x(left_c - right_c)} + {left_b} = {right_b}",
            f"Subtract {left_b} from both sides.",
            f"x = {answer}",
        ],
        hints(
            f"x appears on both sides: {fmt_x(left_c)} and {fmt_x(right_c)}.",
            f"Collect {fmt_x(left_c)} with {fmt_x(right_c)} before you touch the constants.",
            (
                f"After the x terms sit on one side, subtract {left_b} and divide by "
                f"{left_c - right_c}."
            ),
        ),
        "Is x larger than 1? How can you tell before finishing?",
    )


def brackets(spec: tuple, pool: str, item_id: str, difficulty: float) -> dict:
    a, inside, answer, plus = spec
    style = (a + inside + answer) % 3
    if plus:
        rhs = a * (answer + inside)
        inner = rhs // a
        if style == 0:
            stem = f"Solve for x: {a}(x + {inside}) = {rhs}"
        elif style == 1:
            stem = f"Solve for x: {a} × (x + {inside}) = {rhs}"
        else:
            stem = f"What x satisfies {a}(x + {inside}) = {rhs}?"
        steps = [
            f"Divide both sides by {a}: x + {inside} = {inner}.",
            f"Subtract {inside}.",
            f"x = {answer}",
        ]
        pred = "Will x be positive? Why?"
        h1 = f"The {a} multiplies the whole bracket (x + {inside})."
        h2 = f"Divide both sides by {a} first. You get x + {inside} = {inner}."
        h3 = f"Then subtract {inside} to isolate x."
    else:
        rhs = a * (answer - inside)
        inner = rhs // a
        if style == 0:
            stem = f"Solve for x: {a}(x - {inside}) = {rhs}"
        elif style == 1:
            stem = f"Solve for x: {a} × (x - {inside}) = {rhs}"
        else:
            stem = f"What x satisfies {a}(x - {inside}) = {rhs}?"
        steps = [
            f"Divide both sides by {a}: x - {inside} = {inner}.",
            f"Add {inside}.",
            f"x = {answer}",
        ]
        pred = "Will x be greater than the number inside the brackets?"
        h1 = f"The {a} sits outside (x - {inside}). Divide first to unwrap the bracket."
        h2 = f"Divide both sides by {a} first. You get x - {inside} = {inner}."
        h3 = f"Then add {inside} to isolate x."
    return item(
        item_id,
        "MATH.ALG.LIN1.BRACKETS",
        difficulty,
        pool,
        stem,
        str(answer),
        steps,
        hints(h1, h2, h3),
        pred,
    )


def fraction(spec: tuple, pool: str, item_id: str, difficulty: float) -> dict:
    denom, added, answer = spec
    rhs = answer // denom + added
    style = denom % 3
    if style == 0:
        stem = f"Solve for x: x/{denom} + {added} = {rhs}"
        h1 = f"x is divided by {denom}, then {added} is added."
        h2 = f"Undo the {added} first, then multiply by {denom}."
    elif style == 1:
        stem = f"Solve for x: {added} + x/{denom} = {rhs}"
        h1 = f"The {added} is written first, then x is divided by {denom}."
        h2 = f"Move the {added} so that x/{denom} stands alone."
    else:
        stem = f"Solve for x: x/{denom} - {added} = {rhs - 2 * added}"
        rhs_alt = answer // denom - added
        stem = f"Solve for x: x/{denom} - {added} = {rhs_alt}"
        h1 = f"x is divided by {denom}, then {added} is subtracted."
        h2 = f"Add {added} first so you have x/{denom} alone."
        rhs = rhs_alt
    return item(
        item_id,
        "MATH.ALG.LIN1.FRACTION_COEFF",
        difficulty,
        pool,
        stem,
        str(answer),
        [
            f"Isolate x/{denom}, then multiply by {denom}.",
            f"x = {answer}",
        ],
        hints(
            h1,
            h2,
            f"When x/{denom} stands alone, multiply by {denom} to finish.",
        ),
        "Will x be a whole number? Why?",
    )


def word(spec: tuple, pool: str, item_id: str, difficulty: float) -> dict:
    kind = spec[0]
    if kind == "age":
        older, total = spec[1], spec[2]
        answer = (total - older) // 2
        stem = (
            f"A student is {older} years older than her sister. "
            f"Together they are {total} years old. How old is the sister?"
        )
        verify = f"x + (x + {older}) = {total}"
        steps = [
            f"Let the sister be x. Then the student is x + {older}.",
            f"x + (x + {older}) = {total}.",
            f"x = {answer}",
        ]
        pred = "Is the sister younger than the student?"
        h1 = (
            f"Let x be the sister's age. How old is the student, in terms of x, "
            f"if she is {older} years older than her sister?"
        )
        h2 = (
            f"The two ages add to {total} years. Write the student as x plus {older}, "
            f"then add that to x — do not finish the arithmetic yet."
        )
        h3 = (
            f"Let x be the sister. The student is x + {older}. "
            f"Then x + (x + {older}) = {total}. Combine to 2x + {older} = {total}, "
            f"subtract {older}, and divide by 2."
        )
    elif kind == "price":
        extra, total = spec[1], spec[2]
        answer = (total - extra) // 2
        stem = (
            f"A notebook costs {extra} rupees more than a pen. "
            f"Together they cost {total} rupees. How many rupees is the pen?"
        )
        verify = f"x + (x + {extra}) = {total}"
        steps = [
            f"Let the pen cost x rupees. Then the notebook costs x + {extra}.",
            f"x + (x + {extra}) = {total}.",
            f"x = {answer}",
        ]
        pred = "Is the pen cheaper than the notebook?"
        h1 = "Let x be the cost of the pen in rupees. How much is the notebook, in terms of x?"
        h2 = (
            f"The two prices add to {total} rupees. Write the notebook as x plus {extra}, "
            f"then add the two prices — stop before you solve."
        )
        h3 = (
            f"Let x be the pen. Then x + (x + {extra}) = {total}. "
            f"Combine to 2x + {extra} = {total}, subtract {extra}, and divide by 2."
        )
    else:
        extra, total = spec[1], spec[2]
        answer = total - extra
        stem = (
            f"A traveller walks some distance and then cycles {extra} km. "
            f"The whole trip is {total} km. How many kilometres did they walk?"
        )
        verify = f"x + {extra} = {total}"
        steps = [
            f"The two parts add to {total} km.",
            f"x + {extra} = {total}.",
            f"x = {answer}",
        ]
        pred = "Is the walking part shorter than the whole trip?"
        h1 = "Let x be the kilometres walked."
        h2 = (
            f"The whole trip is {total} km and the cycling stretch is {extra} km. "
            f"Write how x and {extra} make {total} — do not evaluate yet."
        )
        h3 = (
            f"Let x be the kilometres walked. Then x + {extra} = {total}. "
            f"Subtract {extra} to isolate x."
        )
    return item(
        item_id,
        "MATH.ALG.LIN1.WORD_PROBLEMS",
        difficulty,
        pool,
        stem,
        str(answer),
        steps,
        hints(h1, h2, h3),
        pred,
        verify=verify,
    )


def check(spec: tuple, pool: str, item_id: str, difficulty: float) -> dict:
    equation, value, holds = spec
    answer = "yes" if holds else "no"
    return item(
        item_id,
        "MATH.ALG.LIN1.CHECK_SOLUTION",
        difficulty,
        pool,
        (
            f"Does x = {value} solve {equation}?"
            if value % 3 == 0
            else (
                f"Is {value} a solution of {equation}?"
                if value % 3 == 1
                else f"Check whether {value} satisfies {equation}."
            )
        ),
        answer,
        [
            f"Substitute x = {value} into {equation}.",
            f"The correct option is {answer}.",
        ],
        hints(
            f"Replace x with {value} on the left of {equation}.",
            f"After substituting {value}, compare the two sides of {equation}.",
            f"Plug in {value}: the left becomes a number. "
            f"Does that number equal the right-hand side? The answer is {answer}.",
        ),
        "Do you expect the two sides to match?",
        type_="mcq",
        options=with_idk(YES_NO, pool),
        accept=[answer],
        verify={"kind": "substitution", "equation": equation, "value": str(value)},
    )


def identity(spec: tuple, pool: str, item_id: str, difficulty: float) -> dict:
    equation, answer = spec
    return item(
        item_id,
        "MATH.ALG.LIN1.IDENTITIES",
        difficulty,
        pool,
        (
            f"How many solutions does {equation} have?"
            if sum(ord(ch) for ch in equation) % 3 == 0
            else (
                f"Classify the solution set of {equation}."
                if sum(ord(ch) for ch in equation) % 3 == 1
                else f"Is {equation} an identity, a contradiction, or a unique value?"
            )
        ),
        answer,
        [
            f"Simplify both sides of {equation}.",
            f"The correct option is {answer}.",
        ],
        hints(
            f"Look at {equation}. Expand any brackets first.",
            f"After simplifying {equation}, do both sides become the same expression?",
            f"After you simplify, this is classified as {answer}.",
        ),
        "Before simplifying: do you expect a unique value, an identity, or a contradiction?",
        type_="mcq",
        options=with_idk(COUNT_OPTS, pool),
        accept=[answer],
        verify={"kind": "solution_count", "equation": equation},
    )


# 12 unique slots per skill: practice 0-4, diagnostic 5-7, A/B 8-9, extra A/B 10-11.
CATALOGS: dict[str, list] = {
    "MATH.ARITH.INTEGERS.OPERATIONS": [
        (15, 3),
        (21, 4),
        (18, 5),
        (30, 8),
        (16, 9),
        (25, 6),
        (14, 2),
        (40, 11),
        (19, 7),
        (28, 9),
        (22, 5),
        (33, 6),
    ],
    "MATH.ALG.INVERSE_OPERATIONS": [
        ("add", 2),
        ("sub", 4),
        ("add", 5),
        ("sub", 6),
        ("add", 7),
        ("sub", 8),
        ("add", 9),
        ("sub", 10),
        ("add", 11),
        ("sub", 12),
        ("add", 13),
        ("sub", 14),
    ],
    # (addend, target) — mostly positive answers; slot 8 is 0; slot 10 is -3.
    "MATH.ALG.LIN1.TRANSLATE": [
        (3, 20),
        (5, 18),
        (7, 15),
        (4, 12),
        (6, 21),
        (8, 17),
        (2, 19),
        (9, 24),
        (10, 10),
        (11, 14),
        (12, 9),
        (5, 25),
    ],
    "MATH.ALG.LIN1.SOLVE_ONE_STEP": [
        (4, 7),
        (5, 8),
        (6, 4),
        (7, 8),
        (8, 4),
        (3, 11),
        (9, 7),
        (2, 15),
        (10, 8),
        (5, 4),
        (4, 15),
        (6, 9),
    ],
    "MATH.ALG.LIN1.SOLVE_TWO_STEP": [
        (2, 3, 5),
        (3, 1, 4),
        (2, 5, 6),
        (4, 2, 3),
        (3, 4, 5),
        (2, 1, 8),
        (4, 3, 2),
        (3, 2, 6),
        (2, 7, 4),
        (5, 1, 3),
        (4, 5, 3),
        (3, 6, 4),
    ],
    "MATH.ALG.LIN1.SOLVE_MULTI": [
        (2, -3, 1, 4),
        (3, 3, 1, 5),
        (4, -1, 2, 3),
        (2, 5, 3, 4),
        (5, -4, 1, 7),
        (3, 1, 2, 4),
        (2, -2, 3, 4),
        (4, 3, 1, 2),
        (3, -5, 2, 7),
        (2, 4, 1, 6),
        (5, -2, 1, 3),
        (3, 6, 1, 2),
    ],
    "MATH.ALG.LIN1.VARIABLES_BOTH_SIDES": [
        (3, 1, 2, 4),
        (4, 2, 1, 5),
        (5, 1, 3, 2),
        (3, 2, 4, 6),
        (4, 1, 5, 3),
        (5, 2, 2, 4),
        (3, 1, 6, 5),
        (4, 3, 2, 7),
        (5, 1, 4, 3),
        (3, 2, 1, 8),
        (4, 1, 3, 6),
        (5, 2, 5, 3),
    ],
    "MATH.ALG.LIN1.BRACKETS": [
        (2, 1, 6, False),
        (3, 2, 4, True),
        (2, 3, 8, False),
        (4, 1, 5, True),
        (3, 4, 7, False),
        (2, 5, 4, True),
        (5, 1, 3, False),
        (3, 1, 6, True),
        (2, 4, 9, False),
        (4, 2, 3, True),
        (3, 5, 8, False),
        (2, 2, 7, True),
    ],
    "MATH.ALG.LIN1.FRACTION_COEFF": [
        (2, 3, 10),
        (3, 1, 12),
        (2, 5, 8),
        (4, 2, 16),
        (2, 1, 14),
        (3, 4, 9),
        (2, 6, 12),
        (5, 1, 20),
        (2, 4, 18),
        (3, 2, 15),
        (4, 1, 12),
        (2, 7, 6),
    ],
    "MATH.ALG.LIN1.WORD_PROBLEMS": [
        ("age", 7, 33),
        ("price", 20, 70, "pen", "notebook"),
        ("dist", 4, 15, "walks", "cycles"),
        ("age", 8, 40),
        ("price", 15, 47, "book", "pen"),
        ("dist", 9, 28, "rides a bus", "walks"),
        ("age", 5, 27),
        ("price", 12, 56, "mango", "bag of oranges"),
        ("dist", 3, 18, "cycles", "walks"),
        ("age", 9, 35),
        ("price", 24, 80, "ticket", "snack"),
        ("dist", 7, 22, "hikes", "rests after"),
    ],
    "MATH.ALG.LIN1.CHECK_SOLUTION": [
        ("2x + 1 = 9", 4, True),
        ("2x + 1 = 9", 3, False),
        ("x + 4 = 9", 5, True),
        ("3x = 12", 5, False),
        ("x - 2 = 6", 8, True),
        ("2x + 3 = 11", 3, False),
        ("4x = 20", 5, True),
        ("x + 7 = 10", 2, False),
        ("3x + 1 = 10", 3, True),
        ("x - 5 = 4", 8, False),
        ("5x = 15", 3, True),
        ("2x - 1 = 7", 5, False),
    ],
    "MATH.ALG.LIN1.IDENTITIES": [
        ("2(x + 3) = 2x + 6", "every"),
        ("2x + 3 = 2x + 7", "none"),
        ("x + 4 = 10", "one"),
        ("3x + 1 = 3x + 1", "every"),
        ("x + 1 = x + 4", "none"),
        ("2x = 8", "one"),
        ("4(x - 1) = 4x - 4", "every"),
        ("5x = 5x + 2", "none"),
        ("3x - 1 = 8", "one"),
        ("x + 5 = x + 5", "every"),
        ("3(x + 1) = 3x", "none"),
        ("x - 5 = 2", "one"),
    ],
}

BUILDERS = {
    "MATH.ARITH.INTEGERS.OPERATIONS": integers,
    "MATH.ALG.INVERSE_OPERATIONS": inverse,
    "MATH.ALG.LIN1.TRANSLATE": translate,
    "MATH.ALG.LIN1.SOLVE_ONE_STEP": one_step,
    "MATH.ALG.LIN1.SOLVE_TWO_STEP": two_step,
    "MATH.ALG.LIN1.SOLVE_MULTI": multi,
    "MATH.ALG.LIN1.BRACKETS": brackets,
    "MATH.ALG.LIN1.VARIABLES_BOTH_SIDES": both_sides,
    "MATH.ALG.LIN1.FRACTION_COEFF": fraction,
    "MATH.ALG.LIN1.WORD_PROBLEMS": word,
    "MATH.ALG.LIN1.CHECK_SOLUTION": check,
    "MATH.ALG.LIN1.IDENTITIES": identity,
}

# Practice slots 0-4 span easy / medium / hard. Matched A/B pairs share a tier.
_SLOT_DIFF = [0.20, 0.32, 0.50, 0.68, 0.86, 0.22, 0.55, 0.86, 0.55, 0.55, 0.86, 0.86]


def slot_difficulty(_skill: str, slot: int) -> float:
    return _SLOT_DIFF[slot]


def _clear_items() -> None:
    items_root = ROOT / "items"
    if not items_root.exists():
        return
    for path in items_root.rglob("*.yaml"):
        if "generated" in path.parts:
            continue
        path.unlink()


def _build(skill: str, slot: int, pool: str, item_id: str) -> dict:
    builder = BUILDERS[skill]
    spec = CATALOGS[skill][slot]
    difficulty = slot_difficulty(skill, slot)
    data = builder(spec, pool, item_id, difficulty)
    data["skill_ids"] = [skill]
    if skill == "MATH.ALG.LIN1.WORD_PROBLEMS":
        data["role"] = "apply"
    return data


def _transfer_items() -> tuple[list[str], list[str], dict[str, str]]:
    """Two hand-authored transfer items per form; structures must not appear in practice."""
    a1 = item(
        "ITEM.LIN1.C.A.0016",
        "MATH.ALG.LIN1.SOLVE_TWO_STEP",
        0.55,
        "checkpoint",
        "Find x given that 11 equals 2x plus 3.",
        "4",
        [
            "Treat 11 as 2x plus 3.",
            "Take 3 from 11, then divide by 2.",
            "x = 4",
        ],
        hints(
            "The constant sits on the left of a two-step undo.",
            "Move the added number first, then undo the coefficient of x.",
            "Take 3 from 11, then divide the result by 2.",
        ),
        "Will x be a whole number?",
        verify="2x + 3 = 11",
    )
    b1 = item(
        "ITEM.LIN1.C.B.0016",
        "MATH.ALG.LIN1.SOLVE_TWO_STEP",
        0.55,
        "checkpoint",
        "Find x given that 15 equals 3x plus 3.",
        "4",
        [
            "Treat 15 as 3x plus 3.",
            "Take 3 from 15, then divide by 3.",
            "x = 4",
        ],
        hints(
            "The constant sits on the left of a two-step undo.",
            "Move the added number first, then undo the coefficient of x.",
            "Take 3 from 15, then divide the result by 3.",
        ),
        "Will x be a whole number?",
        verify="3x + 3 = 15",
    )
    a2 = item(
        "ITEM.LIN1.C.A.0017",
        "MATH.ALG.LIN1.FRACTION_COEFF",
        0.55,
        "checkpoint",
        "Rearrange: 2 equals (x plus 4) over 3. What is x?",
        "2",
        [
            "Unwrap the fraction, then undo the added 4.",
            "x + 4 = 6",
            "x = 2",
        ],
        hints(
            "x sits inside a bracket that is then divided.",
            "Multiply to unwrap the fraction first, then undo the added number.",
            "Multiply 2 by 3 to get x + 4, then take 4 away.",
        ),
        "Will x be smaller than 4?",
        verify="(x + 4)/3 = 2",
    )
    b2 = item(
        "ITEM.LIN1.C.B.0017",
        "MATH.ALG.LIN1.FRACTION_COEFF",
        0.55,
        "checkpoint",
        "Rearrange: 3 equals (x plus 6) over 3. What is x?",
        "3",
        [
            "Unwrap the fraction, then undo the added 6.",
            "x + 6 = 9",
            "x = 3",
        ],
        hints(
            "x sits inside a bracket that is then divided.",
            "Multiply to unwrap the fraction first, then undo the added number.",
            "Multiply 3 by 3 to get x + 6, then take 6 away.",
        ),
        "Will x be smaller than 6?",
        verify="(x + 6)/3 = 3",
    )
    for row in (a1, b1, a2, b2):
        dump(ROOT / "items" / "math" / "checkpoint" / f"{row['id']}.yaml", row)
    return (
        [a1["id"], a2["id"]],
        [b1["id"], b2["id"]],
        {a1["id"]: b1["id"], a2["id"]: b2["id"]},
    )


def write_items(skill_ids: list[str]) -> None:
    _clear_items()
    practice_n = 0
    diag_n = 0
    for skill in skill_ids:
        for slot in range(5):
            practice_n += 1
            data = _build(skill, slot, "practice", f"ITEM.LIN1.P.{practice_n:04d}")
            dump(ROOT / "items" / "math" / "practice" / f"{data['id']}.yaml", data)
        for slot in range(5, 8):
            diag_n += 1
            data = _build(skill, slot, "diagnostic", f"ITEM.LIN1.D.{diag_n:04d}")
            dump(ROOT / "items" / "math" / "diagnostic" / f"{data['id']}.yaml", data)

    form_a: list[str] = []
    form_b: list[str] = []
    cp_index = 0
    pairs = [(skill, 8, 9) for skill in skill_ids]
    for skill in skill_ids[:3]:
        pairs.append((skill, 10, 11))
    for skill, slot_a, slot_b in pairs:
        cp_index += 1
        a = _build(skill, slot_a, "checkpoint", f"ITEM.LIN1.C.A.{cp_index:04d}")
        b = _build(skill, slot_b, "checkpoint", f"ITEM.LIN1.C.B.{cp_index:04d}")
        dump(ROOT / "items" / "math" / "checkpoint" / f"{a['id']}.yaml", a)
        dump(ROOT / "items" / "math" / "checkpoint" / f"{b['id']}.yaml", b)
        form_a.append(a["id"])
        form_b.append(b["id"])

    transfer_a, transfer_b, transfer_map = _transfer_items()
    form_a.extend(transfer_a)
    form_b.extend(transfer_b)

    dump(
        ROOT / "checkpoints" / "lin1_class9.yaml",
        {
            "id": "CP.LIN1.CLASS9.FORMS",
            "checkpoint_id": "CP.LIN1.CLASS9",
            "A": form_a,
            "B": form_b,
            "match_map": dict(zip(form_a, form_b, strict=True)),
        },
    )


def write_overlays(skill_ids: list[str]) -> None:
    for oid, curriculum in (("bhutan_class9", "bhutan"), ("seba_class9", "seba")):
        dump(
            ROOT / "overlays" / f"{oid}.yaml",
            {
                "id": oid,
                "curriculum_id": curriculum,
                "grade": 9,
                "chapter": "linear_equations",
                "skill_ids": skill_ids,
                "live": False,
            },
        )


def write_glossary() -> None:
    terms = {
        "equation": NE,
        "variable": NE,
        "inverse": NE,
        "coefficient": NE,
        "solution": NE,
        "both sides": NE,
        "denominator": NE,
    }
    dump(ROOT / "glossary" / "en-ne.yaml", {"language": "ne", "terms": terms})
    dump(
        ROOT / "glossary" / "en-as.yaml",
        {"language": "as", "terms": {k: AS for k in terms}},
    )


def main() -> None:
    skill_ids = write_skills()
    write_misconceptions()
    write_items(skill_ids)
    write_overlays(skill_ids)
    write_glossary()
    print(f"Wrote seed under {ROOT}")


if __name__ == "__main__":
    main()
