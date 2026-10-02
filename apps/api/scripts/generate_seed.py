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


def loc(en: str) -> dict[str, str]:
    return {"en": en, "ne": NE, "as": AS}


def dump(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def hints_undo(op_word: str, value: int) -> list[dict]:
    return [
        {"level": 1, **loc("What is being done to x? How can you undo that operation?")},
        {"level": 2, **loc("Do the same thing to both sides so the equation stays balanced.")},
        {"level": 3, **loc(f"{op_word} {value} on both sides, then simplify.")},
    ]


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
) -> dict:
    data = {
        "id": item_id,
        "skill_ids": [skill],
        "difficulty": difficulty,
        "type": type_,
        "pool": pool,
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
    return item(
        item_id,
        "MATH.ARITH.INTEGERS.OPERATIONS",
        difficulty,
        pool,
        f"Compute {left} - {right}.",
        str(answer),
        [f"{left} minus {right} is {answer}.", f"x = {answer}"],
        [
            {"level": 1, **loc("Which number is larger? Are we taking away or adding?")},
            {"level": 2, **loc("Start at the first number and move left on the number line.")},
            {"level": 3, **loc(f"Take {right} away from {left}.")},
        ],
        "Will the result be smaller than the first number?",
    )


def inverse(spec: tuple, pool: str, item_id: str, difficulty: float) -> dict:
    kind, value = spec
    if kind == "add":
        stem = f"What number do you add to x - {value} to get x again?"
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
    return item(
        item_id,
        "MATH.ALG.INVERSE_OPERATIONS",
        difficulty,
        pool,
        stem,
        str(value),
        steps,
        [
            {"level": 1, **loc("What operation is being undone?")},
            {"level": 2, **loc("Addition and subtraction undo each other.")},
            {"level": 3, **loc(hint3)},
        ],
        "Is the inverse larger than 1?",
        verify=verify,
    )


def translate(spec: tuple, pool: str, item_id: str, difficulty: float) -> dict:
    addend, target = spec
    answer = target - addend
    return item(
        item_id,
        "MATH.ALG.LIN1.TRANSLATE",
        difficulty,
        pool,
        f"A number plus {addend} equals {target}. What is the number?",
        str(answer),
        [f"The equation is x + {addend} = {target}.", f"x = {answer}"],
        hints_undo("Subtract", addend),
        f"Is the number smaller than {target}?",
        verify=f"x + {addend} = {target}",
    )


def one_step(spec: tuple, pool: str, item_id: str, difficulty: float) -> dict:
    addend, answer = spec
    total = answer + addend
    return item(
        item_id,
        "MATH.ALG.LIN1.SOLVE_ONE_STEP",
        difficulty,
        pool,
        f"Solve for x: x + {addend} = {total}",
        str(answer),
        [
            f"We want x alone. Subtract {addend} from both sides.",
            f"x + {addend} - {addend} = {total} - {addend}",
            f"x = {answer}",
        ],
        hints_undo("Subtract", addend),
        f"Before solving: will x be smaller than {total}? Why?",
        rules=[
            {
                "id": "MC.ALG.INVERSE_OP_WRONG_SIDE",
                "when_answer_equals": [str(total + addend)],
            }
        ],
    )


def two_step(spec: tuple, pool: str, item_id: str, difficulty: float) -> dict:
    coeff, added, answer = spec
    rhs = coeff * answer + added
    return item(
        item_id,
        "MATH.ALG.LIN1.SOLVE_TWO_STEP",
        difficulty,
        pool,
        f"Solve for x: {coeff}x + {added} = {rhs}",
        str(answer),
        [
            f"Subtract {added} from both sides.",
            f"{coeff}x = {rhs - added}",
            f"Divide both sides by {coeff}.",
            f"x = {answer}",
        ],
        hints_undo("First subtract", added),
        "Will x be a whole number? Why do you think that?",
    )


def multi(spec: tuple, pool: str, item_id: str, difficulty: float) -> dict:
    a, b, c, answer = spec
    # a x + b + c x = rhs
    rhs = (a + c) * answer + b
    sign = "+" if b >= 0 else "-"
    b_abs = abs(b)
    return item(
        item_id,
        "MATH.ALG.LIN1.SOLVE_MULTI",
        difficulty,
        pool,
        f"Solve for x: {a}x {sign} {b_abs} + {c}x = {rhs}",
        str(answer),
        [
            f"Combine like terms: {a + c}x {sign} {b_abs} = {rhs}.",
            f"Move the constant, then divide by {a + c}.",
            f"x = {answer}",
        ],
        hints_undo("Combine like terms, then undo", b_abs),
        "Are there like terms you can gather first?",
    )


def both_sides(spec: tuple, pool: str, item_id: str, difficulty: float) -> dict:
    left_c, right_c, left_b, answer = spec
    right_b = (left_c - right_c) * answer + left_b
    return item(
        item_id,
        "MATH.ALG.LIN1.VARIABLES_BOTH_SIDES",
        difficulty,
        pool,
        f"Solve for x: {left_c}x + {left_b} = {right_c}x + {right_b}",
        str(answer),
        [
            f"Subtract {right_c}x from both sides.",
            f"{left_c - right_c}x + {left_b} = {right_b}",
            f"Subtract {left_b} from both sides.",
            f"x = {answer}",
        ],
        hints_undo("Collect like terms, then subtract", left_b),
        "Is x larger than 1? How can you tell before finishing?",
    )


def brackets(spec: tuple, pool: str, item_id: str, difficulty: float) -> dict:
    a, inside, answer, plus = spec
    if plus:
        rhs = a * (answer + inside)
        stem = f"Solve for x: {a}(x + {inside}) = {rhs}"
        steps = [
            f"Expand: {a}x + {a * inside} = {rhs}",
            f"{a}x = {rhs - a * inside}",
            f"x = {answer}",
        ]
        pred = "Will x be positive? Why?"
    else:
        rhs = a * (answer - inside)
        stem = f"Solve for x: {a}(x - {inside}) = {rhs}"
        steps = [
            f"Divide both sides by {a} (or expand the brackets first).",
            f"x - {inside} = {rhs // a}",
            f"x = {answer}",
        ]
        pred = "Will x be greater than the number inside the brackets?"
    return item(
        item_id,
        "MATH.ALG.LIN1.BRACKETS",
        difficulty,
        pool,
        stem,
        str(answer),
        steps,
        hints_undo("Expand or divide, then undo", inside),
        pred,
    )


def fraction(spec: tuple, pool: str, item_id: str, difficulty: float) -> dict:
    denom, added, answer = spec
    rhs = answer // denom + added
    return item(
        item_id,
        "MATH.ALG.LIN1.FRACTION_COEFF",
        difficulty,
        pool,
        f"Solve for x: x/{denom} + {added} = {rhs}",
        str(answer),
        [
            f"Subtract {added} from both sides: x/{denom} = {rhs - added}.",
            f"Multiply both sides by {denom}.",
            f"x = {answer}",
        ],
        hints_undo("Subtract", added),
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
    elif kind == "price":
        extra, total = spec[1], spec[2]
        answer = (total - extra) // 2
        item_a, item_b = spec[3], spec[4]
        stem = (
            f"A {item_b} costs {extra} rupees more than a {item_a}. "
            f"Together they cost {total} rupees. How many rupees is the {item_a}?"
        )
        verify = f"x + (x + {extra}) = {total}"
        steps = [
            f"Let the {item_a} cost x rupees. Then the {item_b} costs x + {extra}.",
            f"x + (x + {extra}) = {total}.",
            f"x = {answer}",
        ]
        pred = f"Is the {item_a} cheaper than the {item_b}?"
    else:
        extra, total = spec[1], spec[2]
        answer = total - extra
        first, second = spec[3], spec[4]
        stem = (
            f"A walker covers {first} for x km and then {second} for {extra} km. "
            f"The whole trip is {total} km. How many kilometres was the first part?"
        )
        verify = f"x + {extra} = {total}"
        steps = [
            f"The two parts add to {total} km.",
            f"x + {extra} = {total}.",
            f"x = {answer}",
        ]
        pred = "Is the first part shorter than the whole trip?"
    return item(
        item_id,
        "MATH.ALG.LIN1.WORD_PROBLEMS",
        difficulty,
        pool,
        stem,
        str(answer),
        steps,
        hints_undo("Write an equation, then undo", spec[1]),
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
        f"Does x = {value} solve {equation}?",
        answer,
        [
            f"Substitute x = {value} into {equation}.",
            f"The correct option is {answer}.",
        ],
        [
            {"level": 1, **loc("Substitute the given value into the left side.")},
            {"level": 2, **loc("Compare the value you get with the right side.")},
            {
                "level": 3,
                **loc(
                    f"After substituting {value}, the sides "
                    f"{'match' if holds else 'do not match'}."
                ),
            },
        ],
        "Do you expect the two sides to match?",
        type_="mcq",
        options=YES_NO,
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
        f"How many solutions does {equation} have?",
        answer,
        [
            f"Simplify both sides of {equation}.",
            f"The correct option is {answer}.",
        ],
        [
            {"level": 1, **loc("Expand or collect terms. Do the two sides look the same?")},
            {
                "level": 2,
                **loc(
                    "If both sides simplify to the same expression, it is an identity. "
                    "If they cannot match, it is a contradiction. "
                    "Otherwise there is a unique value."
                ),
            },
            {"level": 3, **loc(f"This equation is classified as {answer}.")},
        ],
        "Before simplifying: do you expect a unique value, an identity, or a contradiction?",
        type_="mcq",
        options=COUNT_OPTS,
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
        ("add", 3),
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
        (8, 16),
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
        (4, 5, 4),
        (3, 6, 3),
    ],
    "MATH.ALG.LIN1.SOLVE_MULTI": [
        (2, -3, 1, 4),
        (3, 2, 1, 5),
        (4, -1, 2, 3),
        (2, 5, 2, 2),
        (5, -4, 1, 6),
        (3, 1, 2, 4),
        (2, -2, 3, 5),
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
        (5, 2, 5, 2),
    ],
    "MATH.ALG.LIN1.BRACKETS": [
        (2, 1, 6, False),
        (3, 2, 3, True),
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

# Slot difficulties so matched A/B pairs share a tier.
SLOT_DIFFICULTY = {
    "MATH.ARITH.INTEGERS.OPERATIONS": [0.15] * 12,
    "MATH.ALG.INVERSE_OPERATIONS": [0.25] * 12,
    "MATH.ALG.LIN1.TRANSLATE": [0.42] * 12,
    "MATH.ALG.LIN1.SOLVE_ONE_STEP": [0.28] * 12,
    "MATH.ALG.LIN1.SOLVE_TWO_STEP": [0.48] * 12,
    "MATH.ALG.LIN1.SOLVE_MULTI": [0.62] * 12,
    "MATH.ALG.LIN1.VARIABLES_BOTH_SIDES": [0.55] * 12,
    "MATH.ALG.LIN1.BRACKETS": [0.6] * 12,
    "MATH.ALG.LIN1.FRACTION_COEFF": [0.7] * 12,
    "MATH.ALG.LIN1.WORD_PROBLEMS": [0.5] * 12,
    "MATH.ALG.LIN1.CHECK_SOLUTION": [0.32] * 12,
    "MATH.ALG.LIN1.IDENTITIES": [0.85] * 12,
}


def _clear_items() -> None:
    items_root = ROOT / "items"
    if not items_root.exists():
        return
    for path in items_root.rglob("*.yaml"):
        path.unlink()


def _build(skill: str, slot: int, pool: str, item_id: str) -> dict:
    builder = BUILDERS[skill]
    spec = CATALOGS[skill][slot]
    difficulty = SLOT_DIFFICULTY[skill][slot]
    data = builder(spec, pool, item_id, difficulty)
    data["skill_ids"] = [skill]
    return data


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
    for oid, board in (("bhutan_class9", "bhutan"), ("seba_class9", "seba")):
        dump(
            ROOT / "overlays" / f"{oid}.yaml",
            {
                "id": oid,
                "board": board,
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
