/** Seeded leak faults: each is a hint a careless author or a model could write. The filter must catch every one. */
export type LeakCase = { id: string; problem: string; level: 1 | 2 | 3; text: string; allowedStates?: string[]; expect: "leak" | "clean"; note: string };

export const P1 = "3x + 4 = 10"; // root 2, 2 is not in the problem
export const P2 = "x + 2 = 4"; // root 2, and 2 is written in the problem
export const P3 = "x^2 - 5x + 6 = 0"; // roots 2 and 3
export const P4 = "x^2 + x - 1 = 0"; // roots (-1 +- sqrt 5) / 2
export const P5 = "x + 5 = 3"; // root -2

export const FAULTS: LeakCase[] = [
  { id: "f01", problem: P1, level: 1, text: "So x is 2 and you are done.", expect: "leak", note: "digits" },
  { id: "f02", problem: P1, level: 2, text: "Just write x = 2.", expect: "leak", note: "solved form" },
  { id: "f03", problem: P1, level: 1, text: "The answer is two.", expect: "leak", note: "word form" },
  { id: "f04", problem: P1, level: 3, text: "Think of 6/3 here.", expect: "leak", note: "derived fraction span" },
  { id: "f05", problem: P1, level: 3, text: "The value you want is 2.0 exactly.", expect: "leak", note: "trailing .0" },
  { id: "f06", problem: P1, level: 3, text: "It is 200% of one.", expect: "leak", note: "percent" },
  { id: "f07", problem: P1, level: 3, text: "So x = २.", expect: "leak", note: "Devanagari digit" },
  { id: "f08", problem: P1, level: 3, text: "So x  =  2.", expect: "leak", note: "spacing tricks" },
  { id: "f09", problem: P3, level: 2, text: "Try (x - 2)(x - 3) = 0.", expect: "leak", note: "factored form" },
  { id: "f10", problem: P4, level: 3, text: "So x = (-1 + √5)/2.", expect: "leak", note: "surd form" },
  { id: "f11", problem: P1, level: 3, text: "So $x = \\frac{4}{2}$.", expect: "leak", note: "LaTeX fraction" },
  { id: "f12", problem: P3, level: 3, text: "So x = 3 or x = 2.", expect: "leak", note: "two roots, other order" },
  { id: "f13", problem: P5, level: 3, text: "So x = −2.", expect: "leak", note: "unicode minus" },
  { id: "f14", problem: P5, level: 3, text: "The value is minus two.", expect: "leak", note: "negative word form" },
  { id: "f15", problem: P1, level: 3, text: "Notice 2^1 here.", expect: "leak", note: "power as a derived span" },
  { id: "f16", problem: P1, level: 3, text: "It is √4.", expect: "leak", note: "root of a square" },
  { id: "f17", problem: P4, level: 3, text: "It is about 0.62.", expect: "leak", note: "decimal approximation of a surd" },
  { id: "f18", problem: P1, level: 2, text: "Check that x - 2 = 0.", expect: "leak", note: "later state true at the root" },
  { id: "f19", problem: P2, level: 3, text: "So x = 2.", expect: "leak", note: "given literal inside a solved form" },
  { id: "f20", problem: P2, level: 3, text: "The solution is 2.", expect: "leak", note: "given literal in a phrase" },
  { id: "f21", problem: P1, level: 3, text: "So x equals 2.", expect: "leak", note: "equals in words" },
  { id: "f22", problem: P1, level: 3, text: "So x = 4/2.", expect: "leak", note: "derived span inside an assertion" },
  { id: "f23", problem: P5, level: 3, text: "So x=- 2.", expect: "leak", note: "split minus sign" },
  { id: "f24", problem: P1, level: 1, text: "Subtract 4, which leaves 6, then divide to get 2.", expect: "leak", note: "reasoned walk to the number" },
  { id: "f25", problem: P3, level: 3, text: "The roots are 2 and 3.", expect: "leak", note: "roots phrase" },
];

export const CONTROLS: LeakCase[] = [
  { id: "c01", problem: P1, level: 2, text: "Next, do the same thing to both sides: subtract 4 from both sides.", expect: "clean", note: "given amount" },
  { id: "c02", problem: P2, level: 1, text: "Look at the 2 that is added to x and undo it.", expect: "clean", note: "given literal that is also the root" },
  { id: "c03", problem: P1, level: 3, text: "After that step you have 3x = 6. What is the next step?", allowedStates: ["3x = 6"], expect: "clean", note: "allowed first state" },
  { id: "c04", problem: P1, level: 1, text: "Your aim is to get x on its own, doing the same thing to both sides.", expect: "clean", note: "strategy" },
  { id: "c05", problem: P3, level: 3, text: "Start from x^2 - 5x + 6 = 0 and work on it.", expect: "clean", note: "problem restated" },
  { id: "c06", problem: P1, level: 3, text: "Do you want to check your thinking? Put your value back into 3x + 4.", expect: "clean", note: "no value" },
];
