"""Author the G1 role items: one explain, one apply and one transfer item per seed skill.

Run once from apps/api: `python scripts/write_g1_role_items.py`. Output goes to
content/items/math/practice/roles/ as draft items (placeholders for ne/as). Every numeric answer
is checked with SymPy here, and the content validator re-checks stems and `verify` specs.
"""

from __future__ import annotations

from pathlib import Path

import sympy
import yaml
from sympy.parsing.sympy_parser import (
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

ROOT = Path(__file__).resolve().parents[3] / "content"
OUT = ROOT / "items" / "math" / "practice" / "roles"
NE = "<Nepali — to be filled by reviewer>"
AS = "<Assamese — to be filled by reviewer>"

SKILL = {
    1: "MATH.ARITH.INTEGERS.OPERATIONS",
    2: "MATH.ALG.INVERSE_OPERATIONS",
    3: "MATH.ALG.LIN1.TRANSLATE",
    4: "MATH.ALG.LIN1.SOLVE_ONE_STEP",
    5: "MATH.ALG.LIN1.SOLVE_TWO_STEP",
    6: "MATH.ALG.LIN1.SOLVE_MULTI",
    7: "MATH.ALG.LIN1.VARIABLES_BOTH_SIDES",
    8: "MATH.ALG.LIN1.BRACKETS",
    9: "MATH.ALG.LIN1.FRACTION_COEFF",
    10: "MATH.ALG.LIN1.WORD_PROBLEMS",
    11: "MATH.ALG.LIN1.CHECK_SOLUTION",
    12: "MATH.ALG.LIN1.IDENTITIES",
}
TRANSFORMS = standard_transformations + (implicit_multiplication_application,)


def _expr(text: str):
    return parse_expr(text.strip(), transformations=TRANSFORMS)


DIFFICULTY = {"explain": 0.45, "apply": 0.6, "transfer": 0.85}


def loc(en: str) -> dict[str, str]:
    return {"en": en, "ne": NE, "as": AS}


def hints(h1: str, h2: str, h3: str) -> list[dict]:
    return [{"level": 1, **loc(h1)}, {"level": 2, **loc(h2)}, {"level": 3, **loc(h3)}]


def numeric(skill, role, stem, answer, equation, steps, hint_rows, prediction):
    """Expression item solved from `equation` (verified with SymPy here)."""
    expr = (
        _expr(equation.split("=")[0]) - _expr(equation.split("=")[1])
        if "=" in equation
        else _expr(equation)
    )
    if "=" in equation:
        solved = sympy.solve(expr, sympy.Symbol("x"))
        assert solved == [sympy.Integer(answer)], (stem, solved, answer)
    else:
        assert expr == sympy.Integer(answer), (stem, expr, answer)
    return {
        "skill": skill,
        "role": role,
        "type": "expression",
        "stem": stem,
        "answer": str(answer),
        "accept": [str(answer), f"x={answer}"],
        "verify": equation,
        "steps": [*steps, f"x = {answer}"],
        "hints": hint_rows,
        "prediction": prediction,
    }


def mcq(skill, role, stem, options, answer, steps, hint_rows, prediction, verify=None):
    return {
        "skill": skill,
        "role": role,
        "type": "mcq",
        "stem": stem,
        "answer": answer,
        "accept": [answer],
        "options": options,
        "verify": verify,
        "steps": [*steps, f"The correct option is {answer}."],
        "hints": hint_rows,
        "prediction": prediction,
    }


def opts(*rows: tuple[str, str]) -> list[dict]:
    return [{"id": oid, "en": text, "ne": NE, "as": AS} for oid, text in rows]


def claim(skill, claimed, equation, stem_name, hint_rows, prediction, reason_yes, reason_no):
    """Explain item: is the claimed value a solution? Verified by substitution."""
    left, right = equation.split("=")
    value = _expr(left).subs("x", claimed)
    holds = value == _expr(right)
    answer = "yes" if holds else "no"
    return mcq(
        skill,
        "explain",
        f"{stem_name} says that x = {claimed} solves {equation}. Is the student right?",
        opts(("yes", reason_yes), ("no", reason_no)),
        answer,
        [
            f"Put x = {claimed} into {left.strip()}.",
            f"{left.strip()} gives {value}, and the right side is {right.strip()}.",
        ],
        hint_rows,
        prediction,
        verify={"kind": "substitution", "equation": equation, "value": str(claimed)},
    )


def build() -> list[dict]:
    items: list[dict] = []
    s = SKILL
    # 1 Integers
    items += [
        mcq(
            s[1],
            "explain",
            "A student works out -6 + 15 and writes -9. Which sentence best explains the mistake?",
            opts(
                ("o1", "The minus sign was put on the 15 instead of the 6."),
                ("o2", "The two numbers were added without their signs."),
                ("o3", "The two numbers were multiplied."),
                ("o4", "Nothing is wrong with the answer."),
            ),
            "o1",
            [
                "Moving 15 steps to the right from -6 lands on 9.",
                "-9 is what -15 + 6 gives, so the sign sits on the wrong number.",
            ],
            hints(
                "Work out -6 + 15 yourself before reading the options.",
                "Compare your result with -9: which number carries the minus sign in their working?",
                "Moving right from -6 gives 9, while -15 + 6 gives -9.",
            ),
            "Will the true result be positive or negative?",
        ),
        numeric(
            s[1],
            "apply",
            "The temperature in a hill town was -4 degrees at dawn and rose by 11 degrees by noon. What was the temperature at noon, in degrees?",
            7,
            "-4 + 11",
            ["Start at -4 and add the rise of 11.", "-4 + 11 = 7"],
            hints(
                "Start from the dawn temperature and decide whether the rise moves you up or down.",
                "Add the rise to the starting temperature, keeping the sign of the start.",
                "Work out -4 + 11.",
            ),
            "Will the noon temperature be above zero?",
        ),
        numeric(
            s[1],
            "transfer",
            "A lift starts on floor 2, goes down 3 floors, then down 5 floors, then up 12 floors. Which floor is it on now?",
            6,
            "2 - 3 - 5 + 12",
            ["Write each move as adding a positive or negative number.", "2 - 3 - 5 + 12 = 6"],
            hints(
                "Think of each move as adding a positive or negative number to the starting floor.",
                "Combine the moves from left to right, starting from the first floor.",
                "Work out 2 - 3 - 5 + 12.",
            ),
            "Will the lift end above its starting floor?",
        ),
    ]
    # 2 Inverse operations
    items += [
        mcq(
            s[2],
            "explain",
            "To get x alone in x + 9 = 20, a student takes 9 away from the left side only. Why is that not allowed?",
            opts(
                (
                    "o1",
                    "Whatever is done to one side of an equation must be done to the other side too, to keep it balanced.",
                ),
                ("o2", "Subtraction can never be used with a plus sign."),
                ("o3", "Only the number 9 may be moved."),
                ("o4", "It is allowed because the sides need not match."),
            ),
            "o1",
            [
                "An equation is a balance: both sides must stay equal.",
                "Taking 9 from one side only breaks the balance.",
            ],
            hints(
                "Picture the equation as a balanced scale.",
                "If you take 9 off one pan only, what happens to the scale?",
                "Take 9 off both sides so the scale stays level.",
            ),
            "Does the scale stay level if only one side changes?",
        ),
        numeric(
            s[2],
            "apply",
            "A tank holds some water. After 18 litres are poured in it holds 50 litres. How many litres were in the tank before?",
            32,
            "x + 18 = 50",
            ["Pouring in 18 litres added 18 to the start.", "x + 18 = 50"],
            hints(
                "Which operation undoes pouring water in?",
                "Take the poured amount away from the final amount.",
                "Work out 50 - 18.",
            ),
            "Was there more or less than 50 litres at the start?",
        ),
        numeric(
            s[2],
            "transfer",
            "A machine multiplies a number by 3 and then subtracts 4. The output is 20. Run the machine backwards to find the input.",
            8,
            "3x - 4 = 20",
            ["The machine did x times 3, then minus 4, and ended at 20.", "3x - 4 = 20"],
            hints(
                "Undo the steps in the reverse order from the machine.",
                "The last thing the machine did must be undone first.",
                "Add 4 to the output, then divide by 3.",
            ),
            "Will the input be larger than the output?",
        ),
    ]
    # 3 Translate
    items += [
        mcq(
            s[3],
            "explain",
            "A student writes 5x = 20 for 'five more than a number is twenty'. Which sentence explains the mistake?",
            opts(
                ("o1", "'More than' means adding, so it should be x + 5 = 20, not 5 times x."),
                ("o2", "The 20 should be written on the left."),
                ("o3", "A letter cannot stand for a number."),
                ("o4", "Nothing is wrong with it."),
            ),
            "o1",
            [
                "'Five more than a number' means the number plus 5.",
                "So the sentence becomes x + 5 = 20.",
            ],
            hints(
                "Look at the words 'more than': is that adding or multiplying?",
                "Write 'five more than a number' using x and a plus sign.",
                "Five more than x is x + 5.",
            ),
            "Is the number bigger or smaller than 20?",
        ),
        numeric(
            s[3],
            "apply",
            "Dorji has 6 more marbles than Tashi. Dorji has 15 marbles. How many marbles does Tashi have?",
            9,
            "x + 6 = 15",
            ["Let x be Tashi's marbles, so Dorji has x + 6.", "x + 6 = 15"],
            hints(
                "Write Tashi's marbles as x, then write Dorji's marbles using x.",
                "Dorji's count is x plus 6, and Dorji has 15.",
                "Take 6 away from 15.",
            ),
            "Does Tashi have fewer marbles than Dorji?",
        ),
        numeric(
            s[3],
            "transfer",
            "Three times a number, decreased by 5, is 16. What is the number?",
            7,
            "3x - 5 = 16",
            ["'Three times a number, decreased by 5' is 3x - 5.", "3x - 5 = 16"],
            hints(
                "Write 'three times a number' first, then apply the decrease.",
                "Decreased by 5 means take 5 away from three times the number.",
                "Add 5 to 16, then divide by 3.",
            ),
            "Will the number be larger than 5?",
        ),
    ]
    # 4 One step
    items += [
        claim(
            s[4],
            6,
            "x + 9 = 15",
            "A student",
            hints(
                "Replace x with the claimed value on the left side.",
                "Compare what you get on the left with the right side.",
                "Work out 6 + 9 and compare it with 15.",
            ),
            "Will both sides match?",
            "Yes: when x is 6 the left side is 15, the same as the right side.",
            "No: when x is 6 the left side is not 15.",
        ),
        numeric(
            s[4],
            "apply",
            "A bus has some passengers. After 9 more get on, it carries 31 people. How many were on the bus at first?",
            22,
            "x + 9 = 31",
            ["The 9 who got on were added to the start.", "x + 9 = 31"],
            hints(
                "Which operation undoes people getting on the bus?",
                "Take the people who got on away from the final number.",
                "Work out 31 - 9.",
            ),
            "Were there more than 31 people at first?",
        ),
        numeric(
            s[4],
            "transfer",
            "A packet of beads is shared equally among 7 friends and each friend gets 4 beads. How many beads were in the packet?",
            28,
            "x/7 = 4",
            ["Sharing equally among 7 means dividing the packet by 7.", "x/7 = 4"],
            hints(
                "Sharing equally is dividing. Which operation undoes dividing?",
                "Do the opposite of dividing to the amount each friend gets.",
                "Multiply 4 by 7.",
            ),
            "Will the packet hold more beads than one share?",
        ),
    ]
    # 5 Two step
    items += [
        claim(
            s[5],
            6,
            "4x - 3 = 17",
            "A student",
            hints(
                "Replace x with the claimed value, multiply first, then subtract.",
                "Compare the result with the right side.",
                "Work out 4 times 6, then take away 3.",
            ),
            "Will the left side reach 17?",
            "Yes: with x = 6 the left side is 17, matching the right side.",
            "No: with x = 6 the left side is not 17.",
        ),
        numeric(
            s[5],
            "apply",
            "A taxi charges 20 rupees to start plus 12 rupees for each kilometre. A ride costs 68 rupees. What was the length of the ride, in kilometres?",
            4,
            "12x + 20 = 68",
            ["The fare is 20 plus 12 for each kilometre.", "12x + 20 = 68"],
            hints(
                "Split the fare into the fixed start charge and the per-kilometre part.",
                "Take the start charge off the total first, then deal with the rate.",
                "Work out 68 - 20, then divide by 12.",
            ),
            "Will the ride be longer than 10 kilometres?",
        ),
        numeric(
            s[5],
            "transfer",
            "A rope is cut into two equal pieces, then 3 metres are trimmed from one piece, leaving it 11 metres long. How long was the rope in metres?",
            28,
            "x/2 - 3 = 11",
            ["One piece is x/2, and trimming 3 leaves x/2 - 3.", "x/2 - 3 = 11"],
            hints(
                "Describe the length of one piece before trimming, then after trimming.",
                "Undo the trimming first, then undo the cutting in two.",
                "Add 3 to 11, then multiply by 2.",
            ),
            "Is the whole rope longer than 22 metres?",
        ),
    ]
    # 6 Multi
    items += [
        claim(
            s[6],
            3,
            "5x + 2x - 4 = 17",
            "A student",
            hints(
                "Replace every x with the claimed value before combining anything.",
                "Work out both x terms, add them, then take away the number.",
                "Work out 5 times 3 plus 2 times 3, then subtract 4.",
            ),
            "Will the left side reach 17?",
            "Yes: with x = 3 the left side is 17, matching the right side.",
            "No: with x = 3 the left side is not 17.",
        ),
        numeric(
            s[6],
            "apply",
            "A boy buys 3 notebooks, then 2 more of the same notebook, and pays 10 rupees for a pen. He spends 85 rupees in all. What does one notebook cost, in rupees?",
            15,
            "3x + 2x + 10 = 85",
            ["All notebooks cost x each: 3x + 2x.", "3x + 2x + 10 = 85"],
            hints(
                "Count how many notebooks he buys in total before using the price.",
                "Collect the notebook terms, then take the pen away from the total.",
                "Work out 85 - 10, then divide by 5.",
            ),
            "Is one notebook cheaper than the pen?",
        ),
        numeric(
            s[6],
            "transfer",
            "A rectangular plot has one side x metres and the next side 6 metres longer. Its perimeter is 60 metres. Find x.",
            12,
            "2x + 2*(x + 6) = 60",
            ["The perimeter is 2 times x plus 2 times (x + 6).", "2x + 2(x + 6) = 60"],
            hints(
                "Add up all four sides of the plot and call the total 60.",
                "Collect the x terms and the plain numbers separately.",
                "Expand to 4x + 12 = 60, then solve.",
            ),
            "Is x longer than 6 metres?",
        ),
    ]
    # 7 Both sides
    items += [
        claim(
            s[7],
            1,
            "5x - 4 = 2x + 3",
            "A student",
            hints(
                "Replace x with the claimed value on both sides and compare.",
                "Work out each side separately before comparing.",
                "Left is 5 times 1 minus 4; right is 2 times 1 plus 3.",
            ),
            "Will the two sides match?",
            "Yes: with x = 1 both sides are equal.",
            "No: with x = 1 the two sides are not equal.",
        ),
        numeric(
            s[7],
            "apply",
            "Taxi A charges 10 rupees plus 5 rupees per kilometre, and taxi B charges 40 rupees plus 2 rupees per kilometre. After what distance, in kilometres, do both cost the same?",
            10,
            "5x + 10 = 2x + 40",
            ["Taxi A costs 5x + 10 and taxi B costs 2x + 40.", "5x + 10 = 2x + 40"],
            hints(
                "Write each taxi's cost using the number of kilometres.",
                "Put the two costs equal, then gather the x terms on one side.",
                "Take 2x from both costs, then solve 3x + 10 = 40.",
            ),
            "Is taxi A cheaper at the start?",
        ),
        numeric(
            s[7],
            "transfer",
            "Dolma has 40 rupees and saves 15 more each week. Karma has 10 rupees and saves 25 more each week. After how many weeks do they have the same amount?",
            3,
            "15x + 40 = 25x + 10",
            ["Dolma has 15x + 40 and Karma has 25x + 10 after x weeks.", "15x + 40 = 25x + 10"],
            hints(
                "Write each girl's savings after a number of weeks.",
                "Make the two amounts equal and collect the week terms on one side.",
                "Move 15x across, then solve 40 = 10x + 10.",
            ),
            "Does Karma catch up quickly?",
        ),
    ]
    # 8 Brackets
    items += [
        claim(
            s[8],
            3,
            "2(x + 4) = 14",
            "A student",
            hints(
                "Replace x with the claimed value inside the bracket.",
                "Work out the bracket first, then multiply.",
                "Work out 3 + 4, then double it.",
            ),
            "Will the bracket give a value that doubles to 14?",
            "Yes: with x = 3 the left side is 14, matching the right side.",
            "No: with x = 3 the left side is not 14.",
        ),
        numeric(
            s[8],
            "apply",
            "Each of 3 friends buys a snack costing x rupees and a drink costing 4 rupees. Together they pay 39 rupees. What does one snack cost, in rupees?",
            9,
            "3*(x + 4) = 39",
            ["Each friend pays x + 4, so three friends pay 3(x + 4).", "3(x + 4) = 39"],
            hints(
                "Write what one friend pays, then what three friends pay.",
                "Multiply the bracket by the number of friends, or divide the total by it first.",
                "Divide 39 by 3, then take away 4.",
            ),
            "Is a snack cheaper than 13 rupees?",
        ),
        numeric(
            s[8],
            "transfer",
            "A rectangle is 5 metres wide and x + 3 metres long. Its area is 40 square metres. Find x.",
            5,
            "5*(x + 3) = 40",
            ["Area is width times length, so 5 times (x + 3).", "5(x + 3) = 40"],
            hints(
                "Area is width times length. Write the length as a bracket.",
                "Undo the multiplication by the width before the plus.",
                "Divide 40 by 5, then take away 3.",
            ),
            "Is the length more than 3 metres?",
        ),
    ]
    # 9 Fraction coefficients
    items += [
        claim(
            s[9],
            5,
            "x/3 + 1 = 4",
            "A student",
            hints(
                "Replace x with the claimed value and divide first.",
                "Add the 1 to what you got, then compare with the right side.",
                "Work out 5 divided by 3, then add 1.",
            ),
            "Does dividing by 3 give a whole number here?",
            "Yes: with x = 5 the left side is 4, matching the right side.",
            "No: with x = 5 the left side is not 4.",
        ),
        numeric(
            s[9],
            "apply",
            "One third of a number, plus 2, is 9. Find the number.",
            21,
            "x/3 + 2 = 9",
            ["One third of the number is x/3, plus 2.", "x/3 + 2 = 9"],
            hints(
                "Write 'one third of a number' using x.",
                "Undo the plus 2 first, then undo the dividing by 3.",
                "Take 2 from 9, then multiply by 3.",
            ),
            "Is the number more than 9?",
        ),
        numeric(
            s[9],
            "transfer",
            "A farmer sells two fifths of her oranges and has 9 oranges left. How many oranges did she have at first?",
            15,
            "x - 2*x/5 = 9",
            ["She keeps x minus two fifths of x.", "x - 2x/5 = 9"],
            hints(
                "The oranges left are the whole minus the part sold.",
                "Combine x and two fifths of x into one fraction of x.",
                "Three fifths of the oranges is 9, so divide 9 by 3 and multiply by 5.",
            ),
            "Did she sell more than she kept?",
        ),
    ]
    # 10 Word problems
    items += [
        claim(
            s[10],
            12,
            "x + x + 7 = 31",
            "A student",
            hints(
                "Let x be the smaller number and put 12 in its place on both x terms.",
                "Add the two numbers and the extra 7, then compare with the total.",
                "Work out 12 + 12 + 7.",
            ),
            "Do the two numbers and the extra 7 reach the total?",
            "Yes: two numbers where one is 7 more, with x = 12, add to 31.",
            "No: with x = 12 the two numbers do not add to 31.",
        ),
        numeric(
            s[10],
            "apply",
            "A shopkeeper packs 5 boxes with the same number of eggs in each and has 6 loose eggs. In all there are 56 eggs. How many eggs are in one box?",
            10,
            "5x + 6 = 56",
            ["Let x be the eggs in one box: 5x + 6 = 56.", "5x + 6 = 56"],
            hints(
                "Let x be the number of eggs in one box.",
                "Take the loose eggs away from the total before dividing among the boxes.",
                "Work out 56 - 6, then divide by 5.",
            ),
            "Is a box holding more than 10 eggs?",
        ),
        numeric(
            s[10],
            "transfer",
            "A train leaves with some passengers. At the first stop 12 get off, at the second stop 30 get on, and then there are 70 passengers. How many passengers were on the train when it left?",
            52,
            "x - 12 + 30 = 70",
            ["Let x be the passengers at the start: x - 12 + 30 = 70.", "x - 12 + 30 = 70"],
            hints(
                "Let x be the number of passengers when the train left.",
                "Add the people getting off and on into one change, then undo it.",
                "Combine -12 and +30 into one change, then undo it from 70.",
            ),
            "Did the train leave with more than 70 passengers?",
        ),
    ]
    # 11 Check solution
    items += [
        mcq(
            s[11],
            "explain",
            "Priya solves 3x + 4 = 19 and gets x = 4. Which is the best way for her to find out whether she is right?",
            opts(
                ("o1", "Put 4 in place of x and see whether both sides are equal."),
                ("o2", "Check that 4 is a whole number."),
                ("o3", "Solve the equation again in exactly the same way."),
                ("o4", "No check is needed."),
            ),
            "o1",
            [
                "A solution must make both sides equal.",
                "Substituting the value into the equation tests that directly.",
            ],
            hints(
                "A real solution makes the equation true. How could you test that?",
                "Replace the letter by the value and look at both sides.",
                "Substitute her value into 3x + 4 and compare with 19.",
            ),
            "Will substituting give 19 on the left?",
        ),
        mcq(
            s[11],
            "apply",
            "A tailor says a cloth is 12 metres long if twice its length plus 5 gives 29. Using substitution, is the tailor right?",
            opts(
                ("yes", "Yes: 2 times 12 plus 5 makes 29."),
                ("no", "No: 2 times 12 plus 5 does not make 29."),
            ),
            "yes",
            ["Put 12 in place of the length: 2 times 12 plus 5.", "2*12 + 5 = 29"],
            hints(
                "Replace the length by the tailor's value in 'twice the length plus 5'.",
                "Work out the result and compare it with the number the tailor gave.",
                "Work out 2 times 12, then add 5.",
            ),
            "Will the sentence give 29?",
            verify={"kind": "substitution", "equation": "2x + 5 = 29", "value": "12"},
        ),
        mcq(
            s[11],
            "transfer",
            "A student expands 4(x - 2) = 20 and reports x = 3. Using substitution in the original equation, is x = 3 correct?",
            opts(
                ("yes", "Yes: with x = 3 the left side is 20."),
                ("no", "No: with x = 3 the left side is not 20."),
            ),
            "no",
            [
                "Put 3 in place of x in the original equation 4(x - 2) = 20.",
                "4(3 - 2) = 4, which is not 20.",
            ],
            hints(
                "Substitute the value into the original equation, not the expanded one.",
                "Work out the bracket first, then multiply, and compare with the right side.",
                "Work out 3 - 2, then multiply by 4.",
            ),
            "Will the left side come to 20?",
            verify={"kind": "substitution", "equation": "4(x - 2) = 20", "value": "3"},
        ),
    ]
    # 12 Identities
    items += [
        mcq(
            s[12],
            "explain",
            "A student expands 3(x + 2) = 3x + 6 and finds both sides are the same. What does that tell us about the solutions?",
            opts(
                ("every", "Every value of x is a solution."),
                ("one", "Exactly one value of x is a solution."),
                ("none", "No value of x is a solution."),
            ),
            "every",
            [
                "Both sides simplify to the same expression.",
                "So the statement is true whatever x is.",
            ],
            hints(
                "Expand the bracket and compare the two sides.",
                "If the sides turn out identical, ask whether the value of x matters.",
                "Identical sides stay equal for any number you put in.",
            ),
            "Will the two sides ever differ?",
            verify={"kind": "solution_count", "equation": "3(x + 2) = 3x + 6"},
        ),
        mcq(
            s[12],
            "apply",
            "Two shops write the same bill as 2(x + 3) and 2x + 9, where x is the price of a notebook in rupees. How many prices make the two bills equal?",
            opts(
                ("every", "Every price makes them equal."),
                ("one", "Exactly one price makes them equal."),
                ("none", "No price makes them equal."),
            ),
            "none",
            ["Expand 2(x + 3) to get 2x + 6.", "2x + 6 can never equal 2x + 9."],
            hints(
                "Expand the bracket on the first bill.",
                "Compare the plain numbers once the x terms are the same.",
                "The bills differ by a fixed amount for every price.",
            ),
            "Do the bills differ by a fixed amount?",
            verify={"kind": "solution_count", "equation": "2(x + 3) = 2x + 9"},
        ),
        mcq(
            s[12],
            "transfer",
            "Pema writes 2(x + 1) = x + 6 for a puzzle about two bags of sweets. How many values of x solve it?",
            opts(
                ("every", "Every value of x solves it."),
                ("one", "Exactly one value of x solves it."),
                ("none", "No value of x solves it."),
            ),
            "one",
            ["Expand 2(x + 1) to get 2x + 2.", "2x + 2 = x + 6 gives x = 4, a single solution."],
            hints(
                "Expand the bracket, then gather the x terms together.",
                "After gathering, check whether any x terms are left.",
                "Moving x across leaves a plain equation with a single answer.",
            ),
            "After collecting, will x still appear?",
            verify={"kind": "solution_count", "equation": "2(x + 1) = x + 6"},
        ),
    ]
    return items


def to_yaml(index: int, row: dict) -> dict:
    data = {
        "id": f"ITEM.LIN1.R.{index:04d}",
        "skill_ids": [row["skill"]],
        "difficulty": DIFFICULTY[row["role"]],
        "type": row["type"],
        "pool": "practice",
        "role": row["role"],
        "stem": loc(row["stem"]),
        "answer": {"sympy": row["answer"], "accept": row["accept"]},
        "solution_steps": [loc(step) for step in row["steps"]],
        "hints": row["hints"],
        "prediction_prompt": loc(row["prediction"]),
        "misconception_rules": [],
        "reviewed_by": None,
        "status": "draft",
    }
    if row.get("options"):
        data["options"] = row["options"]
    if row.get("verify") is not None:
        data["verify"] = row["verify"]
    return data


def main() -> None:
    items = build()
    assert len(items) == 36, len(items)
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.yaml"):
        old.unlink()
    for index, row in enumerate(items, start=1):
        data = to_yaml(index, row)
        path = OUT / f"{data['id']}.yaml"
        path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"Wrote {len(items)} items to {OUT}")


if __name__ == "__main__":
    main()
