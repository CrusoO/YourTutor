import { describe, expect, it } from "vitest";
import { answerSetFor, contradictsKey, hintLeaks, wordsToDigits } from "@/lib/doubt/leak";
import { int, rng, solved } from "./helpers";
import { CONTROLS, FAULTS } from "./leakCases";

function verdict(c: (typeof FAULTS)[number]) {
  const { c: cand, s } = solved(c.problem);
  return hintLeaks(c.text, c.level, answerSetFor(cand, s), { allowedStates: c.allowedStates });
}

describe("leak filter: seeded faults", () => {
  it("has at least 14 distinct disguises", () => {
    expect(FAULTS.length).toBeGreaterThanOrEqual(14);
    expect(new Set(FAULTS.map((f) => f.note)).size).toBeGreaterThanOrEqual(14);
  });
  for (const f of FAULTS) {
    it(`kills ${f.id}: ${f.note}`, () => {
      const v = verdict(f);
      expect(v.leaks, `${f.text} -> ${JSON.stringify(v)}`).toBe(true);
    });
  }
  it("kill rate is 100 percent", () => {
    const killed = FAULTS.filter((f) => verdict(f).leaks).length;
    expect(killed).toBe(FAULTS.length);
  });
  for (const c of CONTROLS) {
    it(`does not block ${c.id}: ${c.note}`, () => {
      const v = verdict(c);
      expect(v.leaks, `${c.text} -> ${JSON.stringify(v)}`).toBe(false);
    });
  }
  it("a given literal is not a leak", () => {
    expect(verdict({ ...CONTROLS[1] }).leaks).toBe(false);
  });
  it("level 4 is the answer and is never filtered", () => {
    const { c, s } = solved("3x + 4 = 10");
    expect(hintLeaks("x = 2", 4, answerSetFor(c, s)).leaks).toBe(false);
  });
});

describe("leak filter: levels", () => {
  it("levels 1 and 2 reject numbers that are not in the problem; level 3 allows a worked state", () => {
    const { c, s } = solved("3x + 4 = 10");
    const a = answerSetFor(c, s);
    expect(hintLeaks("Subtract 6 from both sides.", 2, a).reasons).toContain("derived_number");
    expect(hintLeaks("You now have 3x = 6.", 3, a, { allowedStates: ["3x = 6"] }).leaks).toBe(false);
    expect(hintLeaks("You now have 6x = 12.", 3, a).reasons).toContain("later_state");
    expect(hintLeaks("You now have x - 2 = 0.", 3, a, { allowedStates: ["3x = 6"] }).leaks).toBe(true);
  });
  it("number words become digits", () => {
    expect(wordsToDigits("minus twenty-one")).toContain("-21");
    expect(wordsToDigits("one hundred and five")).toContain("105");
    expect(wordsToDigits("half")).toContain("(1/2)");
  });
  it("property: any text that states a root is blocked, any text with an unrelated value is not (300 random)", () => {
    const r = rng(77);
    for (let i = 0; i < 300; i++) {
      const root = int(r, -20, 20);
      const m = int(r, 2, 9);
      const b = int(r, 11, 40);
      const rhs = m * root + b;
      const { c, s } = solved(`${m}x + ${b} = ${rhs}`.replace("+ -", "- "));
      const a = answerSetFor(c, s);
      const forms = [`x = ${root}`, `So x is ${root}.`, `the answer is ${root}`, `x=${root}.0`];
      for (const t of forms) expect(hintLeaks(t, 3, a).leaks, `${c.display} :: ${t}`).toBe(true);
      expect(hintLeaks("Do the same thing to both sides.", 1, a).leaks).toBe(false);
    }
  });
});

describe("contradicts_key", () => {
  it("flags a reply that states a value that is not an answer", () => {
    const { c, s } = solved("2x + 3 = 7");
    const a = answerSetFor(c, s);
    expect(contradictsKey("Actually x = 3 is the answer.", a).contradicts).toBe(true);
    expect(contradictsKey("x = 2 works.", a).contradicts).toBe(false);
    expect(contradictsKey("Try putting numbers back in.", a).contradicts).toBe(false);
  });
  it("checks each root of a quadratic", () => {
    const { c, s } = solved("x^2 - 5x + 6 = 0");
    const a = answerSetFor(c, s);
    expect(contradictsKey("x = 2 or x = 3", a).contradicts).toBe(false);
    expect(contradictsKey("x = 2 or x = 4", a).contradicts).toBe(true);
  });
});
