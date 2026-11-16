import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { detectMath } from "@/lib/doubt/detect";
import { LIMITS, guardText, targetsCurrentItem } from "@/lib/doubt/guard";
import { buildLadder } from "@/lib/doubt/ladder";
import { answerSetFor, hintLeaks } from "@/lib/doubt/leak";
import { solve } from "@/lib/doubt/solve";
import { FIXTURE_DIR, int, rng, solved } from "./helpers";
import { CONTROLS, FAULTS } from "./leakCases";

/**
 * The shared fixtures are produced here by the TypeScript solver. The Python reference and the factory kernel re-verify
 * them in apps/api/tests/test_doubt_fixture_parity.py. Run with UPDATE_DOUBT_FIXTURES=1 to rewrite them.
 */
const UPDATE = process.env.UPDATE_DOUBT_FIXTURES === "1";
const dir = FIXTURE_DIR;

function check(name: string, data: unknown): void {
  const file = `${dir}${name}`;
  if (UPDATE) {
    mkdirSync(dir, { recursive: true });
    writeFileSync(file, `${JSON.stringify(data, null, 2)}\n`, "utf8");
    return;
  }
  expect(existsSync(file), `${name} is missing; run with UPDATE_DOUBT_FIXTURES=1`).toBe(true);
  expect(JSON.parse(readFileSync(file, "utf8")), `${name} is stale; run with UPDATE_DOUBT_FIXTURES=1`).toEqual(JSON.parse(JSON.stringify(data)));
}

const CURATED = [
  "2x + 3 = 7", "x + 2 = 4", "3x + 4 = 10", "x + 5 = 3", "3x + 2 = x + 10", "2(x + 3) = 14", "x/2 + 1 = 4", "-3x = 12",
  "5 = 2x + 1", "3x + 2 = 7", "x/3 = 1/2", "2x + 2 = 2(x + 1)", "2x + 3 = 2x + 5",
  "x^2 - 5x + 6 = 0", "x^2 - 4x + 4 = 0", "x^2 = 3x", "2x^2 - 3x - 2 = 0", "x^2 = 9", "(x - 1)(x + 4) = 0",
  "x^2 + x - 1 = 0", "x^2 - 2 = 0", "x^2 - 8 = 0", "3x^2 - 2x - 2 = 0", "x^2 + 1 = 0", "x^2 + 2x + 5 = 0",
  "(x-1)(x-2)(x-3) = 0", "x^3 - x = 0", "x^3 - 2 = 0",
  "2 + 3 * 4", "(2 + 3) * 4", "1/3 + 1/6", "2^10 - 24", "7 - 2 * (3 + 1)", "2 + 3 = 6", "2 + 3 = 5",
  "(x + 1)^2", "2(x + 3) - x", "(x + 2)(x - 2)",
  "x + y = 5; x - y = 1", "2x + 3y = 12; x - y = 1", "3x + 2y = 7; 2x + 5y = 12", "x = 4; x + y = 6",
  "x + y = 2; 2x + 2y = 4", "x + y = 2; x + y = 3",
];

function randomInputs(): string[] {
  const r = rng(2026);
  const out: string[] = [];
  for (let i = 0; i < 20; i++) {
    const m = int(r, 2, 9);
    const root = int(r, -12, 12);
    const b = int(r, -20, 20);
    out.push(`${m}x + (${b}) = ${m * root + b}`);
  }
  for (let i = 0; i < 20; i++) {
    const [a, b, c] = [int(r, 1, 4), int(r, -9, 9), int(r, -9, 9)];
    out.push(`${a}x^2 + (${b})x + (${c}) = 0`);
  }
  for (let i = 0; i < 12; i++) {
    const [a1, b1, a2, b2, x, y] = [int(r, -5, 5), int(r, -5, 5), int(r, -5, 5), int(r, -5, 5), int(r, -6, 6), int(r, -6, 6)];
    out.push(`(${a1})x + (${b1})y = ${a1 * x + b1 * y}; (${a2})x + (${b2})y = ${a2 * x + b2 * y}`);
  }
  for (let i = 0; i < 12; i++) out.push(`${int(r, 1, 30)} * (${int(r, 1, 20)} - ${int(r, 1, 9)}) + ${int(r, 1, 50)} / ${int(r, 1, 9)}`);
  return out;
}

const DETECT_INPUTS = [
  "2x + 3 = 7", "solve 2x+3=7", "2x+3=7 hal karo", "x ka value nikalo 2x+3=7", "find x if 2x + 3 = 7", "2x+3=7, find x",
  "2x+3=7 हल करो", "x^2 - 5x + 6 = 0", "2(3+4)*5", "(x+1)^2", "x + y = 5 and x - y = 1",
  "2x+3y=12; x-y=1", "5 + 3 = 8", "3 x 4", "3n - 2 = 10",
  "my name is Ravi and I am 12", "I have 2 apples and 3 pears", "what is the capital of France", "meet me at 5 pm",
  "9876543210", "+91 98765 43210", "call 98765-43210", "my number is 9876543210 and 2x+3=7", "2000000000 + 1", "123456789 + 1",
  "sin x = 1/2", "2x + 3 < 7", "a + b = c", "1/x = 3", "x^20 = 1", "Ravi has 3 apples and buys 4 more, how many now? 3 + 4",
  "", "7", "hello", "2x",
];

describe("shared fixtures", () => {
  it("detect.json", () => {
    check(
      "detect.json",
      DETECT_INPUTS.map((input) => {
        const d = detectMath(input);
        const result = d.kind === "candidate" ? `candidate:${d.candidate.kind}` : d.kind === "unsupported" ? `unsupported:${d.why}` : "none";
        const lhs = d.kind === "candidate" ? (d.candidate.lhs ?? null) : null;
        return { input, result, lhs };
      }),
    );
  });

  it("cases.json", () => {
    const cases = [...CURATED, ...randomInputs()].map((input, i) => {
      const d = detectMath(input);
      if (d.kind !== "candidate") throw new Error(`fixture input is not a candidate: ${input}`);
      const c = d.candidate;
      const s = solve(c);
      return {
        id: `case-${String(i + 1).padStart(3, "0")}`,
        input,
        kind: c.kind,
        variable: c.variable,
        expr: c.expr ?? null,
        claimed: c.claimed ?? null,
        lhsText: c.lhsText ?? null,
        rhsText: c.rhsText ?? null,
        lhs: c.lhs ?? null,
        rhs: c.rhs ?? null,
        system: c.system ?? null,
        status: s.status,
        why: s.why ?? null,
        answer: s.answer,
        claimTrue: s.claimTrue ?? null,
        rules: s.steps.map((x) => x.rule),
      };
    });
    expect(cases.length).toBeGreaterThan(100);
    check("cases.json", cases);
  });

  it("ladder.json", () => {
    const rows = CURATED.map((input) => {
      const { c, s } = solved(input);
      const l = buildLadder(c, s);
      const given = [...new Set([c.lhsText, c.rhsText, c.expr, c.claimed, ...(c.system?.texts ?? [])].flatMap((t) => (t ?? "").match(/\d+/g) ?? []))];
      return {
        input,
        status: s.status,
        answerValues: s.answer.kind === "values" ? s.answer.values : s.answer.kind === "surd" ? s.answer.values : s.answer.kind === "pair" ? [s.answer.x, s.answer.y] : [],
        given,
        levels: l.levels.map((x) => ({ level: x.level, id: x.id, text: x.text, fallback: x.fallback })),
      };
    });
    check("ladder.json", rows);
  });

  it("leak.json", () => {
    const rows = [...FAULTS, ...CONTROLS].map((f) => {
      const { c, s } = solved(f.problem);
      const v = hintLeaks(f.text, f.level, answerSetFor(c, s), { allowedStates: f.allowedStates });
      return { id: f.id, problem: f.problem, level: f.level, text: f.text, allowedStates: f.allowedStates ?? [], expect: f.expect, note: f.note, leaks: v.leaks };
    });
    expect(rows.filter((r) => r.expect === "leak").every((r) => r.leaks)).toBe(true);
    expect(rows.filter((r) => r.expect === "clean").every((r) => !r.leaks)).toBe(true);
    check("leak.json", rows);
  });

  it("guard.json", () => {
    const stem = "Solve 2x + 3 = 7. Show your working.";
    const questions = [
      "2x+3 = 7", "what is 2 and 3 and 7", "x + 1 = 5", "solve 2x + 3 = 7 please", "7 = 2x + 3", "hello", "3 and 7 together",
    ];
    const stems = [stem, "Find the value of 3 apples.", "Solve x^2 - 5x + 6 = 0."];
    const item = questions.flatMap((q) => stems.map((st) => ({ question: q, stem: st, expect: targetsCurrentItem(q, st) })));
    const text = [
      "2x + 3 = 7", "x^2 - 5x + 6 = 0", "2^10", "1+".repeat(150), "1234567890 + 1", "2^99999999", "2^13", "2^(9^9)", "x^x", "9**99",
    ].map((t) => {
      const g = guardText(t);
      return { text: t, ok: g.ok, why: g.ok ? null : g.why };
    });
    check("guard.json", { limits: LIMITS, item, text });
  });
});
