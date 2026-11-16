import { describe, expect, it } from "vitest";
import { checkAnswer, checkStep, parseStudentValues } from "@/lib/doubt/attempt";
import { solved } from "./helpers";

const ans = (problem: string, text: string) => {
  const { c, s } = solved(problem);
  return checkAnswer(c, s, text);
};

describe("checkAnswer", () => {
  it("accepts the right value in several writings and shows the substitution", () => {
    for (const t of ["2", "x = 2", "x=2", "x is 2", "4/2", "2.0", "two"]) expect(ans("2x + 3 = 7", t).verdict, t).toBe("correct");
    expect(ans("2x + 3 = 7", "x = 3").text).toMatch(/does not work/);
    expect(ans("2x + 3 = 7", "x = 3").evidence[0]).toBe("Put x = 3 back in: the left side is 9 but the right side is 7. They are not equal, so 3 is not a solution.");
  });
  it("catches a lost root and an extra root by comparing sets", () => {
    expect(ans("x^2 - 5x + 6 = 0", "x = 2").verdict).toBe("incomplete");
    expect(ans("x^2 - 5x + 6 = 0", "x = 2").missing).toBe(1);
    expect(ans("x^2 - 5x + 6 = 0", "2 or 3").verdict).toBe("correct");
    expect(ans("x^2 - 5x + 6 = 0", "2, 3, 4").verdict).toBe("has_wrong_value");
    expect(ans("x^2 = 3x", "3").verdict).toBe("incomplete");
    expect(ans("x^2 = 3x", "0 and 3").verdict).toBe("correct");
  });
  it("checks surd answers exactly", () => {
    expect(ans("x^2 + x - 1 = 0", "(-1 + √5)/2, (-1 - √5)/2").verdict).toBe("correct");
    expect(ans("x^2 + x - 1 = 0", "(-1 + √5)/2").verdict).toBe("incomplete");
    expect(ans("x^2 + x - 1 = 0", "0.618").verdict).toBe("wrong");
  });
  it("handles no solution, identity, arithmetic, simplify and systems", () => {
    expect(ans("x^2 + 1 = 0", "no solution").verdict).toBe("correct");
    expect(ans("x^2 + 1 = 0", "x = 1").verdict).toBe("wrong");
    expect(ans("2x + 2 = 2(x + 1)", "all values").verdict).toBe("correct");
    expect(ans("2 + 3 * 4", "14").verdict).toBe("correct");
    expect(ans("2 + 3 * 4", "20").verdict).toBe("wrong");
    expect(ans("(x + 1)^2", "x^2 + 2x + 1").verdict).toBe("correct");
    expect(ans("(x + 1)^2", "x^2 + 1").verdict).toBe("wrong");
    expect(ans("x + y = 5; x - y = 1", "x = 3, y = 2").verdict).toBe("correct");
    expect(ans("x + y = 5; x - y = 1", "(3, 2)").verdict).toBe("correct");
    expect(ans("x + y = 5; x - y = 1", "x = 2, y = 3").verdict).toBe("wrong");
  });
  it("never prints the answer when the student is wrong", () => {
    const r = ans("2x + 3 = 7", "x = 5");
    expect(JSON.stringify(r)).not.toMatch(/x = 2\b/);
  });
  it("says it could not read nonsense", () => {
    for (const t of ["", "banana", "x = ", "2x + ?"]) expect(ans("2x + 3 = 7", t).verdict).toBe("unreadable");
    expect(parseStudentValues("1;2;3;4;5;6;7;8", ["x"])).toBeNull();
  });
});

describe("checkStep", () => {
  const step = (problem: string, prev: string, next: string) => checkStep(solved(problem).c, prev, next);
  it("accepts balanced moves", () => {
    expect(step("2x + 3 = 7", "2x + 3 = 7", "2x = 4").verdict).toBe("ok");
    expect(step("2x + 3 = 7", "2x = 4", "x = 2").verdict).toBe("ok");
    expect(step("2x + 3 = 7", "2x + 3 = 7", "7 = 2x + 3").verdict).toBe("ok");
    expect(step("x^2 - 5x + 6 = 0", "x^2 - 5x + 6 = 0", "(x - 2)(x - 3) = 0").verdict).toBe("ok");
    expect(step("x^2 - 5x + 6 = 0", "(x - 2)(x - 3) = 0", "x - 2 = 0 or x - 3 = 0").verdict).toBe("ok");
    expect(step("x^2 - 5x + 6 = 0", "x^2 - 5x + 6 = 0", "x^2 = 5x - 6").verdict).toBe("ok");
  });
  it("catches an arithmetic slip", () => {
    expect(step("2x + 3 = 7", "2x + 3 = 7", "2x = 5").verdict).toBe("not_equivalent");
  });
  it("catches a lost root (dividing by the unknown) and an extra root (squaring)", () => {
    expect(step("x^2 = 3x", "x^2 = 3x", "x = 3").verdict).toBe("lost_roots");
    expect(step("x = 3", "x = 3", "x^2 = 9").verdict).toBe("extra_roots");
  });
  it("separates equivalent from legal", () => {
    const r = step("2x + 3 = 7", "2x + 3 = 7", "x + 1.5 = 3.5");
    expect(r.equivalent).toBe(true);
    expect(r.legal).toBe(true);
    const jump = step("x = 2", "x = 2", "(x - 2)^2 = 0");
    expect(jump.equivalent).toBe(true);
    expect(jump.legal).toBe(false);
    expect(jump.verdict).toBe("equivalent_not_a_move");
  });
  it("is unreadable for a non-equation", () => {
    expect(step("2x + 3 = 7", "2x + 3 = 7", "hello").verdict).toBe("unreadable");
  });
});
