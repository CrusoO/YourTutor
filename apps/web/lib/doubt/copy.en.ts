import type { RuleId } from "./types";

/**
 * Authored English copy for the doubt solver. Hindi and Nepali are written and reviewed by the owner later; nothing here
 * is machine translated. Wording rule (owner decision): teach "do the same operation to both sides" (inverse
 * operations). Never teach moving a term across the equals sign or flipping its sign.
 */

/** The only label the device may show. The words reserved for kernel-verified results are never used here. */
export const LABEL_DEVICE = "Worked out on your device";
export const LABEL_DEVICE_DETAIL =
  "Each answer was put back into your equation and it works (exact arithmetic). Not checked by Brownie's server.";

export const LABELS = {
  device: LABEL_DEVICE,
  deviceDetail: LABEL_DEVICE_DETAIL,
  unsupported: "This kind of question is not worked out on your device yet.",
} as const;

type Args = Record<string, string>;

export const RULE_COPY: Record<RuleId, (a: Args) => string> = {
  write_equation: () => "Start with the equation as you wrote it.",
  expand_bracket: () => "Multiply out the brackets so every term stands on its own, then tidy each side.",
  collect_like_terms: () => "Tidy each side by adding the like terms together.",
  add_both_sides: (a) => `Add ${a.amount} to both sides. Adding undoes the subtraction and keeps the equation balanced.`,
  subtract_both_sides: (a) =>
    `Subtract ${a.amount} from both sides. Subtracting undoes the addition and keeps the equation balanced.`,
  multiply_both_sides: (a) =>
    a.which
      ? `Multiply both sides of equation ${a.which} by ${a.factor}, so the numbers in front of one letter match.`
      : `Multiply both sides by ${a.factor}. Multiplying undoes the division and keeps the equation balanced.`,
  divide_both_sides: (a) =>
    `Divide both sides by ${a.factor}. Dividing undoes the multiplying and leaves the unknown on its own.`,
  write_standard_form: () => "Do the same thing to both sides so that a whole side is empty and the rest stays on the other.",
  factor_quadratic: () => "Write the expression as a product of brackets.",
  zero_product: () => "When a product is nothing, some factor must be nothing. Set each bracket to nothing.",
  rational_root: (a) => `A whole number or fraction that makes the expression vanish is ${a.root}, so it gives a bracket to take out.`,
  discriminant: () => "Work out the discriminant D = b squared minus 4ac from the numbers in front of the terms.",
  quadratic_formula: () => "Use the quadratic formula: x = (-b plus or minus the square root of D) divided by 2a.",
  simplify_surd: () => "Take the square factors out of the root so it is as small as possible.",
  no_real_roots: () => "D is negative and no real number squared is negative, so there is no real solution.",
  no_solution: () => "The unknown has cancelled and the two sides can never be equal, so there is no solution.",
  identity: () => "Both sides are always equal, so every value works.",
  eval_operation: (a) => (a.op === "√" ? `The square root of ${a.a} is ${a.result}.` : `Work out ${a.a} ${a.op} ${a.b}, which is ${a.result}.`),
  eliminate_unknown: (a) => `${a.op === "add" ? "Add" : "Subtract"} the equations so that ${a.unknown} disappears.`,
  solve_one_unknown: () => "Now only one unknown is left. Undo what is done to it, doing the same to both sides.",
  substitute_back: (a) => `Put ${a.unknown} = ${a.value} into an equation to find the other unknown.`,
  substitute_check: (a) => `Check: put ${a.values} back into the original. Both sides come to the same number.`,
  state_result: () => "So we have the result.",
};

export const HINT_COPY = {
  strategy: {
    linear: (v: string) =>
      `Your aim is to get ${v} on its own. Look at what is being done to ${v}, then undo it with the inverse operation, doing the same thing to both sides each time.`,
    quadratic: () =>
      "Collect everything on a single side so the other side is empty. Then either write the expression as a product of brackets, or use the discriminant. If a product is nothing, some factor of it must be nothing.",
    quadraticPlain: () =>
      "Do the same thing to both sides until a side is empty. Then split what is left into brackets, or use the discriminant.",
    polynomial: () =>
      "Try small whole numbers and simple fractions to find a value that makes the expression vanish, take that bracket out, and repeat on what is left.",
    simplify: () => "Multiply out any brackets first, then put the like terms together.",
    arith: () => "Work in order: brackets first, then powers and roots, then multiply and divide, then add and subtract.",
    system: () =>
      "Make the numbers in front of a chosen letter match in both equations, then add or subtract the equations so that letter disappears. Solve for the letter that is left, then use it to find the other.",
  },
  nextStep: {
    tidy: () => "First tidy each side: multiply out any brackets and put like terms together.",
    undoAdd: (amount: string) => `Next, do the same thing to both sides: subtract ${amount} from both sides.`,
    undoSub: (amount: string) => `Next, do the same thing to both sides: add ${amount} to both sides.`,
    undoGeneric: () => "Next, undo the number that is added or subtracted, by doing the same thing to both sides.",
    unknownGeneric: () => "Next, get the unknown terms together on a single side by doing the same thing to both sides.",
    divide: (factor: string) => `Last, divide both sides by ${factor}.`,
    multiply: (factor: string) => `Next, multiply both sides by ${factor}.`,
    divideGeneric: () => "Last, undo the number multiplying the unknown by dividing both sides by it.",
    standardForm: () => "Next, do the same thing to both sides so that a side is empty.",
    factor: () => "Next, write the expression as a product of brackets.",
    discriminant: () => "Next, work out the discriminant from the numbers in front of the terms.",
    rationalRoot: () => "Next, try a small whole number or simple fraction that makes the expression vanish.",
    arith: (a: string, op: string, b: string) => `Do ${a} ${op} ${b} next.`,
    arithGeneric: () => "Do the operation inside the innermost brackets first, or the multiplication or division that comes first.",
    eliminate: () => "Next, multiply the equations so that the numbers in front of a chosen letter match.",
    simplify: () => "Next, multiply out any brackets, then collect the like terms.",
    scale: () => "Next, multiply both sides to clear the fractions.",
  },
  leadIn: {
    state: (state: string) => `After that step you have ${state}. What is the next step?`,
    generic: () => "Do that step, then look carefully at what is left and decide the next step.",
  },
  stepsHeader: "Here are all the steps.",
  noSolution: "There is no value that makes both sides equal. See the steps to find out why.",
} as const;

export const ATTEMPT_COPY = {
  works: (v: string, val: string, l: string, r: string) => `Put ${v} = ${val} back in: the left side is ${l} and the right side is ${r}. It works.`,
  fails: (v: string, val: string, l: string, r: string) =>
    `Put ${v} = ${val} back in: the left side is ${l} but the right side is ${r}. They are not equal, so ${val} is not a solution.`,
  correct: "Yes, that is right, and putting it back in confirms it.",
  incomplete: (missing: number) =>
    `Every value you gave works, but there ${missing === 1 ? "is 1 more" : `are ${missing} more`} to find.`,
  hasWrong: "One of your values does not work. Check each one by putting it back into the equation.",
  wrong: "That does not work. Check it by putting it back into the equation.",
  unreadable: "I could not read that as a number or an answer. Try something like x = 3.",
  arithWrong: (shown: string) => `Not quite: you wrote ${shown}. Work through it again, one operation at a time, in order.`,
  arithRight: "Yes, that is right.",
  noSolutionRight: "Yes: there is no value that works.",
  identityRight: "Yes: every value works.",
  stepOk: "That step keeps the equation balanced, and it has the same solutions.",
  stepSkipped: "That has the same solutions, but it is not one balanced step from the line above. Try the move that does the same thing to both sides.",
  stepLost: "That step loses a solution that the line above had. Dividing both sides by the unknown is not allowed, because the unknown could be zero.",
  stepExtra: "That step adds a solution that the line above did not have. Squaring both sides can do that.",
  stepNotEquivalent: "That step changes the solutions, so something went wrong in it. Check each term.",
  stepUnreadable: "I could not read that step as an equation.",
} as const;

export const PUSHBACK_COPY = {
  claimFails: (v: string, val: string, l: string, r: string) =>
    `Let us check it together. Put ${v} = ${val} into the equation: the left side is ${l} and the right side is ${r}. They are not equal, so ${val} does not work.`,
  claimWorks: (v: string, val: string) => `Put ${v} = ${val} back in and it does work. Roots found so far are listed in the steps.`,
  unreadable: "I could not read that value. Tell me the number you think it is and I will put it back into the equation.",
  keyWins: "The worked answer stays. Putting a value back into the equation is the check that decides.",
} as const;
