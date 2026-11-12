import { describe, expect, it } from "vitest";
import {
  checkPrediction,
  choiceValueToNumber,
  clampToLine,
  directionOf,
  expression,
  fmt,
  guessToChoiceValue,
  hopAnnouncement,
  isSafeFigure,
  isSafeInt,
  landing,
  narrationScript,
  numberWords,
  pathPoints,
  predictScript,
  tokenText,
  valueFromX,
  viewWindow,
} from "@/lib/lessons/numberline";

describe("number line maths", () => {
  it("lands at start plus delta and gives one path point per hop", () => {
    expect(landing(-8, 5)).toBe(-3);
    expect(landing(3, -7)).toBe(-4);
    expect(pathPoints(-8, 5)).toEqual([-8, -7, -6, -5, -4, -3]);
    expect(pathPoints(3, -7)).toEqual([3, 2, 1, 0, -1, -2, -3, -4]);
  });

  it("reads the sign as a direction: positive right, negative left", () => {
    expect(directionOf(5)).toBe("right");
    expect(directionOf(-7)).toBe("left");
  });

  it("refuses numbers outside -20..20, fractions and a move of nothing", () => {
    expect(isSafeInt(20)).toBe(true);
    expect(isSafeInt(-20)).toBe(true);
    expect(isSafeInt(21)).toBe(false);
    expect(isSafeInt(2.5)).toBe(false);
    expect(isSafeInt(Number.NaN)).toBe(false);
    expect(isSafeFigure(-8, 5)).toBe(true);
    expect(isSafeFigure(15, 10)).toBe(false); // lands on 25
    expect(isSafeFigure(0, 0)).toBe(false);
    expect(isSafeFigure(25, -5)).toBe(false);
  });

  it("clamps and maps pixels to whole numbers inside the window", () => {
    expect(clampToLine(99)).toBe(20);
    expect(clampToLine(-99)).toBe(-20);
    const win = { min: -10, max: 10 };
    expect(valueFromX(0, 0, 200, win)).toBe(-10);
    expect(valueFromX(200, 0, 200, win)).toBe(10);
    expect(valueFromX(100, 0, 200, win)).toBe(0);
    expect(valueFromX(-50, 0, 200, win)).toBe(-10);
    expect(valueFromX(5, 0, 0, win)).toBe(-10);
  });

  it("keeps zero, start and landing inside the window, never wider than the safe range", () => {
    const w = viewWindow([-8, -3]);
    expect(w.min).toBeLessThanOrEqual(-9);
    expect(w.max).toBeGreaterThanOrEqual(1);
    expect(viewWindow([1, 2]).max - viewWindow([1, 2]).min).toBeGreaterThanOrEqual(10);
    const wide = viewWindow([-20, 20]);
    expect(wide).toEqual({ min: -20, max: 20 });
  });
});

describe("wording", () => {
  it("draws a real minus sign", () => {
    expect(fmt(-3)).toBe("−3");
    expect(expression(-8, 5)).toBe("−8 + 5");
    expect(expression(3, -7)).toBe("3 − 7");
    expect(tokenText(5)).toBe("+5");
    expect(tokenText(-7)).toBe("−7");
  });

  it("narrates the hop sequence from the numbers", () => {
    expect(narrationScript(-8, 5)).toBe(
      "Start at minus eight. Add five: five steps to the right. Minus seven, minus six, minus five, minus four, minus three. You land on minus three.",
    );
  });

  it("narrates a subtraction as steps to the left", () => {
    expect(narrationScript(3, -7)).toBe(
      "Start at three. Subtract seven: seven steps to the left. Two, one, zero, minus one, minus two, minus three, minus four. You land on minus four.",
    );
    expect(narrationScript(0, -1)).toContain("one step to the left");
  });

  it("does not give the answer before the guess", () => {
    const text = predictScript(-8, 5);
    expect(text).toContain("Where do you think you land?");
    expect(text).not.toContain("minus three");
  });

  it("says nothing for a figure it would refuse", () => {
    expect(narrationScript(30, 1)).toBe("");
    expect(predictScript(0, 0)).toBe("");
    expect(numberWords(-20)).toBe("minus twenty");
  });

  it("announces each hop and the landing", () => {
    expect(hopAnnouncement(2, 5, -6)).toBe("Hop 2 of 5: minus six.");
    expect(hopAnnouncement(5, 5, -3)).toBe("Hop 5 of 5: minus three. You land on minus three.");
    expect(hopAnnouncement(0, 5, -8)).toBe("Start at minus eight.");
  });
});

describe("checkPrediction", () => {
  it("is correct on the true landing", () => {
    const r = checkPrediction(-8, 5, -3);
    expect(r).toMatchObject({ correct: true, kind: "correct", landing: -3 });
    expect(r.reason).toContain("lands on −3");
  });

  it("explains moving the wrong way in plain words, without a scold", () => {
    const r = checkPrediction(-8, 5, -13);
    expect(r.correct).toBe(false);
    expect(r.kind).toBe("other_way");
    expect(r.reason).toContain("same number of steps, but left");
    expect(r.reason).toContain("Adding 5 moves 5 steps right from −8");
    expect(r.reason.toLowerCase()).not.toMatch(/wrong|incorrect|bad|mistake/);
  });

  it("explains the sign flipped across zero, ignoring the start, and not moving", () => {
    expect(checkPrediction(-8, 5, 3).kind).toBe("other_side_of_zero");
    expect(checkPrediction(-8, 5, 5).kind).toBe("forgot_start");
    expect(checkPrediction(-8, 5, -8).kind).toBe("stayed");
    expect(checkPrediction(-8, 5, -1).kind).toBe("off");
  });

  it("reads a subtraction as a move left", () => {
    const r = checkPrediction(3, -7, 10);
    expect(r.landing).toBe(-4);
    expect(r.kind).toBe("other_way");
    expect(r.reason).toContain("Subtracting 7 moves 7 steps left from 3");
    expect(checkPrediction(3, -7, 4).kind).toBe("other_side_of_zero");
  });
});

describe("choice mapping", () => {
  const choices = [{ value: "9" }, { value: "−9" }, { value: "21" }];
  it("maps a placed number onto a matching choice, typographic minus included", () => {
    expect(guessToChoiceValue(9, choices)).toBe("9");
    expect(guessToChoiceValue(-9, choices)).toBe("−9");
    expect(guessToChoiceValue(4, choices)).toBe("4");
    expect(choiceValueToNumber("−9")).toBe(-9);
    expect(choiceValueToNumber("a lot")).toBeNull();
  });
});
