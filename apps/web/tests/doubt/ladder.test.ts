import { describe, expect, it } from "vitest";
import { Frac } from "@/lib/doubt/frac";
import { HINT_COPY, LABELS } from "@/lib/doubt/copy.en";
import { buildLadder } from "@/lib/doubt/ladder";
import { wordsToDigits } from "@/lib/doubt/leak";
import { int, rng, solved } from "./helpers";

const PROBLEMS = [
  "2x + 3 = 7",
  "3x + 4 = 10",
  "x + 2 = 4",
  "x + 5 = 3",
  "3x + 2 = x + 10",
  "2(x + 3) = 14",
  "x/2 + 1 = 4",
  "x^2 - 5x + 6 = 0",
  "x^2 = 3x",
  "x^2 + x - 1 = 0",
  "2x^2 - 3x - 2 = 0",
  "x^2 + 1 = 0",
  "(x-1)(x-2)(x-3) = 0",
  "2 + 3 * 4",
  "(2 + 3) * 4",
  "(x + 1)^2",
  "x + y = 5; x - y = 1",
  "2x + 3y = 12; x - y = 1",
];

/** Independent oracle: pull every number out of the text and compare with the exact answers. */
function numbersIn(text: string): Frac[] {
  const out: Frac[] = [];
  for (const m of wordsToDigits(text.toLowerCase()).matchAll(/\d+(?:\.\d+)?(?:\/\d+)?/g)) {
    const f = Frac.parse(m[0]);
    if (f) out.push(f);
  }
  return out;
}

describe("hint ladder", () => {
  it("has four levels for a solved problem, strategy first and full steps last", () => {
    const { c, s } = solved("2x + 3 = 7");
    const l = buildLadder(c, s);
    expect(l.levels.map((x) => x.level)).toEqual([1, 2, 3, 4]);
    expect(l.levels[0].text).toMatch(/on its own/);
    expect(l.levels[1].text).toMatch(/subtract 3 from both sides/);
    expect(l.levels[2].text).toMatch(/2x = 4/);
    expect(l.levels[3].text).toMatch(/x = 2/);
    expect(l.levels[3].text).toContain(LABELS.device);
  });
  it("levels 1 to 3 never contain a root or the final value (every problem, every level)", () => {
    for (const p of PROBLEMS) {
      const { c, s } = solved(p);
      const l = buildLadder(c, s);
      const answers = s.exact.map((q) => q.p); // rational parts
      const given = new Set<string>();
      for (const t of [c.lhsText, c.rhsText, c.expr, ...(c.system?.texts ?? [])]) {
        for (const m of (t ?? "").matchAll(/\d+/g)) given.add(m[0]);
      }
      for (const lv of l.levels.filter((x) => x.level < 4)) {
        const text = lv.text;
        for (const n of numbersIn(text)) {
          const isAnswer = s.exact.some((q) => q.d === BigInt(0) && (q.p.eq(n) || q.p.eq(n.neg())));
          if (isAnswer) expect(given.has(n.toString()), `${p} L${lv.level}: ${text}`).toBe(true);
        }
        expect(text, `${p} L${lv.level}`).not.toMatch(/√/);
        void answers;
      }
    }
  });
  it("levels 1 and 2 use only numbers written in the problem", () => {
    for (const p of PROBLEMS) {
      const { c, s } = solved(p);
      const given = new Set<string>();
      for (const t of [c.lhsText, c.rhsText, c.expr, ...(c.system?.texts ?? [])]) for (const m of (t ?? "").matchAll(/\d+/g)) given.add(m[0]);
      for (const lv of buildLadder(c, s).levels.filter((x) => x.level <= 2)) {
        for (const n of numbersIn(lv.text)) expect(given.has(n.toString()), `${p} L${lv.level}: ${lv.text}`).toBe(true);
      }
    }
  });
  it("falls back to plainer text when the author's hint would leak", () => {
    const { c, s } = solved("x + 2 = 4"); // one step: the first state is the answer
    const l = buildLadder(c, s);
    const three = l.levels.find((x) => x.level === 3);
    expect(three?.fallback).toBe(true);
    expect(three?.text).not.toMatch(/x = 2/);
  });
  it("level 4 carries every step and the answer; no solution says so", () => {
    const { c, s } = solved("x^2 + 1 = 0");
    const l4 = buildLadder(c, s).levels.find((x) => x.level === 4);
    expect(l4?.text).toMatch(/no real/i);
    expect(l4?.text).toContain(HINT_COPY.noSolution);
  });
  it("is empty for an unsupported solution", () => {
    const { c, s } = solved("x^3 - 2 = 0");
    expect(s.status).toBe("unsupported");
    expect(buildLadder(c, s).levels).toEqual([]);
  });
  it("hint wording teaches the same operation on both sides and never the move-across shortcut", () => {
    const BANNED = /across|flip|change (the )?sign|switch (the )?sign|transpos|cross over|carry over|send it|take it to the other side/i;
    const texts: string[] = [];
    for (const p of PROBLEMS) {
      const { c, s } = solved(p);
      for (const lv of buildLadder(c, s).levels) texts.push(lv.text);
    }
    for (const group of Object.values(HINT_COPY.strategy)) texts.push((group as (v: string) => string)("x"));
    for (const t of texts) expect(t).not.toMatch(BANNED);
    expect(buildLadder(solved("2x + 3 = 7").c, solved("2x + 3 = 7").s).levels[0].text).toMatch(/same thing to both sides/);
  });
  it("authored level 1 to 3 copy has no number words or digits to leak through", () => {
    const authored = [
      ...Object.values(HINT_COPY.strategy).map((f) => (f as (v: string) => string)("x")),
      HINT_COPY.nextStep.tidy(),
      HINT_COPY.nextStep.undoGeneric(),
      HINT_COPY.nextStep.unknownGeneric(),
      HINT_COPY.nextStep.divideGeneric(),
      HINT_COPY.nextStep.standardForm(),
      HINT_COPY.nextStep.factor(),
      HINT_COPY.nextStep.discriminant(),
      HINT_COPY.nextStep.rationalRoot(),
      HINT_COPY.nextStep.arithGeneric(),
      HINT_COPY.nextStep.eliminate(),
      HINT_COPY.nextStep.simplify(),
      HINT_COPY.nextStep.scale(),
      HINT_COPY.leadIn.generic(),
    ];
    for (const t of authored) expect(wordsToDigits(t.toLowerCase())).not.toMatch(/\d/);
  });
  it("property: random linear problems never leak at levels 1 to 3 (300 random)", () => {
    const r = rng(99);
    for (let i = 0; i < 300; i++) {
      const root = int(r, -15, 15);
      const m = int(r, 2, 9);
      const b = int(r, 11, 40);
      const { c, s } = solved(`${m}x + ${b} = ${m * root + b}`.replace("+ -", "- "));
      for (const lv of buildLadder(c, s).levels.filter((x) => x.level < 4)) {
        const hits = numbersIn(lv.text).filter((n) => n.eq(Frac.of(Math.abs(root))) && Math.abs(root) !== 0);
        const given = new RegExp(`\\b${Math.abs(root)}\\b`).test(c.display);
        if (hits.length && !given) throw new Error(`${c.display} L${lv.level}: ${lv.text}`);
      }
    }
  });
});
