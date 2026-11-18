import { describe, expect, it } from "vitest";
import { t } from "@/lib/messages";
import { withSession } from "@/lib/session/copy";
import {
  answerMatches,
  explanationSteps,
  fmt,
  move,
  parseIntegerStem,
  plainSourceLabel,
  showSignHintButton,
  signCase,
  signRuleLines,
  verifiedParse,
  visibleSteps,
} from "@/lib/session/integer-stem";

const copy = withSession(t("en"));

describe("parseIntegerStem", () => {
  it.each([
    ["Compute 10 + (-7).", 10, "+", -7, 3],
    ["Compute 10 + 7.", 10, "+", 7, 17],
    ["Compute 10 - 7.", 10, "-", 7, 3],
    ["Compute 4 - (-6).", 4, "-", -6, 10],
    ["Compute (-3) + 5", -3, "+", 5, 2],
    ["Compute -3 + 5", -3, "+", 5, 2],
    ["Compute -3 - (-5).", -3, "-", -5, 2],
    ["10+(-7)", 10, "+", -7, 3],
    ["  Evaluate   10   -   (  -7 )  =  ?  ", 10, "-", -7, 17],
    ["Compute 10 − 7.", 10, "-", 7, 3],
    ["compute 5 + -2", 5, "+", -2, 3],
    ["What is 8 - 12?", 8, "-", 12, -4],
    ["0 + 0", 0, "+", 0, 0],
  ])("%s", (stem, start, op, operand, result) => {
    expect(parseIntegerStem(stem)).toEqual({ start, op, operand, result });
  });

  it.each([
    "Solve for x: x + 4 = 10",
    "Compute x + 3.",
    "Compute 1.5 + 2.",
    "Compute 10 * 7.",
    "Compute 10 / 5.",
    "Compute 10 x 7.",
    "Compute 10 + 7 + 2.",
    "Compute 10.",
    "Compute 10 +",
    "Compute 1234 + 5.",
    "Compute 99999999999999999999 + 1.",
    "Compute 10 + ((-7)).",
    "Compute 10 + (-7",
    "Compute 10 + 7 apples.",
    "Compute 2^3 + 1.",
    "Add 10 and 7.",
    "",
  ])("rejects %s", (stem) => {
    expect(parseIntegerStem(stem)).toBeNull();
  });

  it("rejects non-strings and very long text", () => {
    expect(parseIntegerStem(undefined)).toBeNull();
    expect(parseIntegerStem(null)).toBeNull();
    expect(parseIntegerStem("Compute " + "1".repeat(200) + " + 1")).toBeNull();
  });
});

describe("result check", () => {
  it("matches only when the computed result equals the answer", () => {
    const p = parseIntegerStem("Compute 10 + (-7).")!;
    expect(answerMatches(p, "3")).toBe(true);
    expect(answerMatches(p, " 3 ")).toBe(true);
    expect(answerMatches(p, "17")).toBe(false);
    expect(answerMatches(p, "x = 3")).toBe(false);
    expect(answerMatches(p, undefined)).toBe(false);
    expect(verifiedParse("Compute 10 + (-7).", "3")?.result).toBe(3);
    expect(verifiedParse("Compute 10 + (-7).", "4")).toBeNull();
    expect(verifiedParse("Compute 10 - 12.", "−2")?.result).toBe(-2);
    expect(verifiedParse("Solve x", "3")).toBeNull();
  });
});

describe("sign explanation text", () => {
  const p = (s: string) => parseIntegerStem(s)!;
  it("names the four cases", () => {
    expect(signCase(p("Compute 10 + 7."))).toBe("plus");
    expect(signCase(p("Compute 10 - 7."))).toBe("minus");
    expect(signCase(p("Compute 10 + (-7)."))).toBe("add-negative");
    expect(signCase(p("Compute 10 - (-7)."))).toBe("subtract-negative");
  });
  it("always gives the general rule; adds the extra line only for negatives", () => {
    expect(signRuleLines(p("Compute 10 + 7."), copy)).toEqual({
      general: "A plus sign means go right. A minus sign means go left.",
      specific: null,
    });
    expect(signRuleLines(p("Compute 10 - 7."), copy).specific).toBeNull();
    expect(signRuleLines(p("Compute 10 + (-7)."), copy).specific).toBe(
      "Adding a negative number moves you left, the same as taking away.",
    );
    expect(signRuleLines(p("Compute 10 - (-7)."), copy).specific).toBe("Taking away a negative moves you right.");
  });
  it("builds the steps from the numbers, in code", () => {
    expect(explanationSteps(p("Compute 10 + (-7)."), copy)).toEqual([
      "Start at 10.",
      "Adding −7 means move 7 steps left.",
      "You land on 3.",
    ]);
    expect(explanationSteps(p("Compute 10 - (-7)."), copy)).toEqual([
      "Start at 10.",
      "Subtracting −7 means move 7 steps right.",
      "You land on 17.",
    ]);
    expect(explanationSteps(p("Compute 3 - 1."), copy)[1]).toBe("Subtracting 1 means move 1 step left.");
    expect(explanationSteps(p("Compute 3 + 0."), copy)[1]).toBe("Adding 0 means you do not move.");
  });
  it("leaves the landing out when asked (the hint)", () => {
    const steps = explanationSteps(p("Compute 10 + (-7)."), copy, false);
    expect(steps).toHaveLength(2);
    expect(steps.join(" ")).not.toMatch(/land|\b3\b/);
  });
  it("moves and formats", () => {
    expect(move(p("Compute 10 + (-7)."))).toBe(-7);
    expect(move(p("Compute 10 - (-7)."))).toBe(7);
    expect(fmt(-4)).toBe("−4");
  });
});

describe("hint button rule", () => {
  const parse = parseIntegerStem("Compute 10 + (-7).");
  it("needs a parse and a first wrong answer, Help, or a hint on screen", () => {
    expect(showSignHintButton(parse, { wrongOnce: false, helpAsked: false, hintShown: false })).toBe(false);
    expect(showSignHintButton(parse, { wrongOnce: true, helpAsked: false, hintShown: false })).toBe(true);
    expect(showSignHintButton(parse, { wrongOnce: false, helpAsked: true, hintShown: false })).toBe(true);
    expect(showSignHintButton(parse, { wrongOnce: false, helpAsked: false, hintShown: true })).toBe(true);
    expect(showSignHintButton(null, { wrongOnce: true, helpAsked: true, hintShown: true })).toBe(false);
  });
});

describe("stray variable steps", () => {
  it("hides x = steps when the stem has no x", () => {
    expect(visibleSteps(["Adding -7 to 10 is 3.", "x = 3"], "Compute 10 + (-7).")).toEqual(["Adding -7 to 10 is 3."]);
    expect(visibleSteps(["a", "2. x = 3", "X=4"], "Compute 1 + 2.")).toEqual(["a"]);
  });
  it("keeps them when the stem has an x", () => {
    expect(visibleSteps(["Subtract 4.", "x = 6"], "Solve for x: x + 4 = 10")).toEqual(["Subtract 4.", "x = 6"]);
  });
  it("keeps steps that merely mention x or start with another letter", () => {
    expect(visibleSteps(["max = 3", "Then x is found"], "Compute 1 + 2.")).toEqual(["max = 3", "Then x is found"]);
    expect(visibleSteps(undefined, "Compute 1 + 2.")).toEqual([]);
  });
});

describe("plainSourceLabel", () => {
  it("drops 'authored note' and says whole numbers", () => {
    expect(plainSourceLabel("Adding and subtracting integers (authored note)")).toBe(
      "From the lesson: Adding and subtracting whole numbers",
    );
    expect(plainSourceLabel("Integers - Authored notes")).toBe("From the lesson: Whole numbers");
    expect(plainSourceLabel("Authored note")).toBe("From the lesson");
  });
  it("leaves other labels alone", () => {
    expect(plainSourceLabel("NCERT Class 7, chapter 1")).toBe("NCERT Class 7, chapter 1");
  });
});
