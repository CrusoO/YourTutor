import { describe, expect, it } from "vitest";
import { guardCandidate, guardText, routesToPracticeHelp, stemEquations, targetsCurrentItem } from "@/lib/doubt/guard";
import { cand } from "./helpers";

describe("guardText", () => {
  it("accepts ordinary input", () => {
    expect(guardText("2x + 3 = 7")).toEqual({ ok: true });
    expect(guardText("x^2 - 5x + 6 = 0")).toEqual({ ok: true });
    expect(guardText("2^10")).toEqual({ ok: true });
  });
  it("rejects over-long strings, big numbers and huge exponents", () => {
    expect(guardText("1+".repeat(150))).toEqual({ ok: false, why: "too_long" });
    expect(guardText("1234567890 + 1")).toEqual({ ok: false, why: "too_big_number" });
    expect(guardText("2^99999999")).toEqual({ ok: false, why: "huge_exponent" });
    expect(guardText("2^13")).toEqual({ ok: false, why: "huge_exponent" });
    expect(guardText("2^(9^9)")).toEqual({ ok: false, why: "huge_exponent" });
    expect(guardText("x^x")).toEqual({ ok: false, why: "huge_exponent" });
    expect(guardText("9**99")).toEqual({ ok: false, why: "huge_exponent" });
  });
});

describe("guardCandidate", () => {
  it("rejects trees that are too big", () => {
    expect(guardCandidate(cand("2x + 3 = 7"))).toEqual({ ok: true });
    const long = Array.from({ length: 30 }, (_, i) => `${i + 1}x`).join(" + ");
    const c = cand(`${long} = 7`);
    expect(guardCandidate(c)).toEqual({ ok: false, why: "too_many_terms" });
  });
  it("rejects polynomials above the device degree", () => {
    expect(guardCandidate(cand("x^5 = 32"))).toEqual({ ok: false, why: "high_degree" });
  });
});

describe("practice item in play", () => {
  const stem = "Solve 2x + 3 = 7. Show your working.";
  it("mirrors the server's equation extraction", () => {
    expect(stemEquations(stem)).toEqual(["2x+3=7"]);
    expect(stemEquations("Find the value of 3 apples.")).toEqual([]);
  });
  it("flags the item's own equation (any spacing) and shared numbers", () => {
    expect(targetsCurrentItem("2x+3 = 7", stem)).toBe("stem_expression");
    expect(targetsCurrentItem("what is 2 and 3 and 7", stem)).toBe("stem_numbers");
    expect(targetsCurrentItem("x + 1 = 5", stem)).toBeNull();
    expect(targetsCurrentItem("anything", null)).toBeNull();
  });
  it("routes an equivalent writing of the same equation to practice help", () => {
    expect(routesToPracticeHelp(cand("2x + 3 = 7"), [stem])).toBe(true);
    expect(routesToPracticeHelp(cand("7 = 2x + 3"), [stem])).toBe(true);
    expect(routesToPracticeHelp(cand("4x + 6 = 14"), [stem])).toBe(true);
    expect(routesToPracticeHelp(cand("5x + 1 = 9"), [stem])).toBe(false);
    expect(routesToPracticeHelp(cand("2x + 3 = 7"), [])).toBe(false);
  });
});
