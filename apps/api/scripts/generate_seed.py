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
    accept: list[str] | None = None,
    rules: list[dict] | None = None,
) -> dict:
    return {
        "id": item_id,
        "skill_ids": [skill],
        "difficulty": difficulty,
        "type": "expression",
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


def one_step(n: int, pool: str, prefix: str) -> dict:
    addend = 4 + (n % 6)  # 4..9
    answer = 2 + (n % 5)  # 2..6, never equals addend (>=4 vs <=6 wait 4,5,6 overlap)
    # force inequality
    if answer == addend:
        answer = addend - 3
    total = answer + addend
    skill = "MATH.ALG.LIN1.SOLVE_ONE_STEP"
    return item(
        f"{prefix}{n:04d}",
        skill,
        0.25 + 0.05 * (n % 3),
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


def two_step(n: int, pool: str, prefix: str) -> dict:
    coeff = 2 + (n % 3)  # 2,3,4
    added = 1 + (n % 4)  # 1..4
    answer = 3 + (n % 4)  # 3..6
    if answer in {coeff, added}:
        answer += 2
    rhs = coeff * answer + added
    return item(
        f"{prefix}{n:04d}",
        "MATH.ALG.LIN1.SOLVE_TWO_STEP",
        0.45,
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


def both_sides(n: int, pool: str, prefix: str) -> dict:
    left_c = 3
    right_c = 1
    left_b = 2 + n % 3
    answer = 4 + n % 3
    right_b = (left_c - right_c) * answer + left_b
    return item(
        f"{prefix}{n:04d}",
        "MATH.ALG.LIN1.VARIABLES_BOTH_SIDES",
        0.55,
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


def brackets(n: int, pool: str, prefix: str) -> dict:
    a = 2 + n % 3
    inside = 1 + n % 4
    answer = 3 + n % 3
    if answer == a:
        answer += 1
    rhs = a * (answer - inside) if n % 2 == 0 else a * (answer + inside)
    if n % 2 == 0:
        stem = f"Solve for x: {a}(x - {inside}) = {rhs}"
        steps = [
            f"Divide both sides by {a} (or expand the brackets first).",
            f"x - {inside} = {rhs // a}",
            f"x = {answer}",
        ]
        pred = "Will x be greater than the number inside the brackets?"
    else:
        stem = f"Solve for x: {a}(x + {inside}) = {rhs}"
        steps = [
            f"Expand: {a}x + {a * inside} = {rhs}",
            f"{a}x = {rhs - a * inside}",
            f"x = {answer}",
        ]
        pred = "Will x be positive? Why?"
    return item(
        f"{prefix}{n:04d}",
        "MATH.ALG.LIN1.BRACKETS",
        0.6,
        pool,
        stem,
        str(answer),
        steps,
        hints_undo("Expand or divide, then undo", inside),
        pred,
    )


def integers(n: int, pool: str, prefix: str) -> dict:
    a = 8 + n
    b = 3
    answer = a - b
    return item(
        f"{prefix}{n:04d}",
        "MATH.ARITH.INTEGERS.OPERATIONS",
        0.2,
        pool,
        f"Compute {a} - {b}.",
        str(answer),
        [f"{a} minus {b} is {answer}.", f"x = {answer}"],
        [
            {"level": 1, **loc("Which number is larger? Are we taking away or adding?")},
            {"level": 2, **loc("Start at the first number and move left on the number line.")},
            {"level": 3, **loc(f"Take {b} away from {a}.")},
        ],
        "Will the result be smaller than the first number?",
    )


def inverse(n: int, pool: str, prefix: str) -> dict:
    a = 6 + n % 4
    return item(
        f"{prefix}{n:04d}",
        "MATH.ALG.INVERSE_OPERATIONS",
        0.3,
        pool,
        f"What number do you add to x - {a} to get x again?",
        str(a),
        [f"The inverse of subtracting {a} is adding {a}.", f"x = {a}"],
        [
            {"level": 1, **loc("What operation is being undone?")},
            {"level": 2, **loc("Addition and subtraction undo each other.")},
            {"level": 3, **loc(f"Add {a} to cancel subtract {a}.")},
        ],
        "Is the inverse larger than 1?",
    )


def translate(n: int, pool: str, prefix: str) -> dict:
    k = 5 + n
    return item(
        f"{prefix}{n:04d}",
        "MATH.ALG.LIN1.TRANSLATE",
        0.4,
        pool,
        f"A number plus {k} equals 20. What is the number?",
        str(20 - k),
        [f"The equation is x + {k} = 20.", f"x = {20 - k}"],
        hints_undo("Subtract", k),
        "Is the number smaller than 20?",
    )


def multi(n: int, pool: str, prefix: str) -> dict:
    answer = 2 + n % 4
    return item(
        f"{prefix}{n:04d}",
        "MATH.ALG.LIN1.SOLVE_MULTI",
        0.65,
        pool,
        f"Solve for x: 2x - 3 + x = {3 * answer - 3}",
        str(answer),
        ["Combine like terms: 3x - 3 = RHS.", "Add 3 to both sides.", f"x = {answer}"],
        hints_undo("Combine like terms, then add", 3),
        "Are there like terms you can gather first?",
    )


def fraction(n: int, pool: str, prefix: str) -> dict:
    answer = 4 + n % 5
    if answer == 2:
        answer = 8
    rhs = answer // 2 + 3 if answer % 2 == 0 else None
    # use x/2 + 3 = rhs with even answer
    answer = 2 * (3 + n % 4)  # 6,8,10,12
    rhs = answer // 2 + 3
    return item(
        f"{prefix}{n:04d}",
        "MATH.ALG.LIN1.FRACTION_COEFF",
        0.7,
        pool,
        f"Solve for x: x/2 + 3 = {rhs}",
        str(answer),
        [
            f"Subtract 3 from both sides: x/2 = {rhs - 3}.",
            "Multiply both sides by 2.",
            f"x = {answer}",
        ],
        hints_undo("Subtract", 3),
        "Will x be even? Why?",
    )


def word(n: int, pool: str, prefix: str) -> dict:
    age = 12 + n
    older = 7
    return item(
        f"{prefix}{n:04d}",
        "MATH.ALG.LIN1.WORD_PROBLEMS",
        0.5,
        pool,
        (
            f"A student is {older} years older than her sister. "
            f"Together they are {age + (age - older)} years old. "
            "How old is the sister?"
        ),
        str(age - older),
        [
            f"Let the sister be x. Then the student is x + {older}.",
            f"x + (x + {older}) = {2 * age - older}.",
            f"x = {age - older}",
        ],
        hints_undo("Write an equation, then subtract", older),
        "Is the sister younger than the student?",
    )


def check(n: int, pool: str, prefix: str) -> dict:
    # answer 1 means yes, 0 means no — use 1/0
    xval = 4 + n % 3
    rhs = 2 * xval + 1
    return item(
        f"{prefix}{n:04d}",
        "MATH.ALG.LIN1.CHECK_SOLUTION",
        0.35,
        pool,
        f"Does x = {xval} solve 2x + 1 = {rhs}? Write 1 for yes or 0 for no.",
        "1",
        [f"2*{xval} + 1 = {2 * xval + 1}, which equals {rhs}.", "x = 1"],
        [
            {"level": 1, **loc("Substitute the given x into the left side.")},
            {"level": 2, **loc("Compare the value you get with the right side.")},
            {"level": 3, **loc(f"Compute 2 × {xval} + 1 and compare with {rhs}.")},
        ],
        "Do you expect the two sides to match?",
    )


def identity(n: int, pool: str, prefix: str) -> dict:
    # 1 = infinitely many, 0 = none — use 1 for identity
    return item(
        f"{prefix}{n:04d}",
        "MATH.ALG.LIN1.IDENTITIES",
        0.8,
        pool,
        "How many solutions does 2(x + 3) = 2x + 6 have? Write 1 if every x works, 0 if none work.",
        "1",
        ["Expand: 2x + 6 = 2x + 6.", "The two sides are the same for every x.", "x = 1"],
        [
            {"level": 1, **loc("Expand the brackets. Do the two sides look the same?")},
            {
                "level": 2,
                **loc(
                    "If both sides simplify to the same expression, "
                    "every value works."
                ),
            },
            {"level": 3, **loc("2x + 6 equals 2x + 6, so the equation is an identity.")},
        ],
        "Before expanding: do you expect one solution or many?",
    )


BUILDERS = {
    "MATH.ARITH.INTEGERS.OPERATIONS": integers,
    "MATH.ALG.INVERSE_OPERATIONS": inverse,
    "MATH.ALG.LIN1.TRANSLATE": translate,
    "MATH.ALG.LIN1.SOLVE_ONE_STEP": one_step,
    "MATH.ALG.LIN1.SOLVE_TWO_STEP": two_step,
    "MATH.ALG.LIN1.SOLVE_MULTI": multi,
    "MATH.ALG.LIN1.VARIABLES_BOTH_SIDES": both_sides,
    "MATH.ALG.LIN1.BRACKETS": brackets,
    "MATH.ALG.LIN1.FRACTION_COEFF": fraction,
    "MATH.ALG.LIN1.WORD_PROBLEMS": word,
    "MATH.ALG.LIN1.CHECK_SOLUTION": check,
    "MATH.ALG.LIN1.IDENTITIES": identity,
}


def write_items(skill_ids: list[str]) -> tuple[list[str], list[str]]:
    practice_n = 0
    diag_n = 0
    form_a: list[str] = []
    form_b: list[str] = []

    # 5 practice per skill = 60
    for skill in skill_ids:
        builder = BUILDERS[skill]
        for i in range(5):
            practice_n += 1
            data = builder(practice_n, "practice", "ITEM.LIN1.P.")
            data["skill_ids"] = [skill]
            dump(ROOT / "items" / "math" / "practice" / f"{data['id']}.yaml", data)

    # 30 diagnostic: 3 for first 6 skills, 2 for last 6
    for idx, skill in enumerate(skill_ids):
        count = 3 if idx < 6 else 2
        builder = BUILDERS[skill]
        for _ in range(count):
            diag_n += 1
            data = builder(100 + diag_n, "diagnostic", "ITEM.LIN1.D.")
            data["skill_ids"] = [skill]
            dump(ROOT / "items" / "math" / "diagnostic" / f"{data['id']}.yaml", data)

    # 15 + 15 matched checkpoint
    for i, skill in enumerate(skill_ids[:12]):
        if len(form_a) >= 15:
            break
    # use first 12 skills + repeat 3 core skills = 15
    cp_skills = skill_ids + skill_ids[:3]
    for i, skill in enumerate(cp_skills[:15], start=1):
        builder = BUILDERS[skill]
        a = builder(200 + i, "checkpoint", "ITEM.LIN1.C.A.")
        a["skill_ids"] = [skill]
        b = builder(300 + i, "checkpoint", "ITEM.LIN1.C.B.")
        b["skill_ids"] = [skill]
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
    return form_a, form_b


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
