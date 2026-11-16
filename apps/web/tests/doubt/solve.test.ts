import { describe, expect, it } from "vitest";
import { B0, Frac, bgcd } from "@/lib/doubt/frac";
import { RULE_IDS } from "@/lib/doubt/rules";
import { renderSteps } from "@/lib/doubt/steps";
import { solve } from "@/lib/doubt/solve";
import { int, rng, solved } from "./helpers";

const values = (t: string): string[] => {
  const { s } = solved(t);
  return s.answer.kind === "values" ? s.answer.values : s.answer.kind === "surd" ? [...s.answer.values, ...s.answer.surds] : [];
};

describe("arithmetic", () => {
  it("evaluates exactly with a step per operation, in BODMAS order", () => {
    const { s } = solved("2 + 3 * 4");
    expect(s.answer).toEqual({ kind: "values", values: ["14"] });
    expect(s.steps.map((x) => x.args.result)).toEqual(["12", "14"]);
    expect(solved("(2+3)*4").s.answer).toEqual({ kind: "values", values: ["20"] });
    expect(values("1/3 + 1/6")).toEqual(["1/2"]);
    expect(values("2^10 - 24")).toEqual(["1000"]);
    expect(values("√49 + 3")).toEqual(["10"]);
    expect(values("0.1 + 0.2")).toEqual(["3/10"]);
  });
  it("checks a claimed value", () => {
    expect(solved("2 + 3 = 5").s.claimTrue).toBe(true);
    expect(solved("2 + 3 = 6").s.claimTrue).toBe(false);
  });
});

describe("linear equations", () => {
  it("one step, two step, unknown on both sides, brackets, fractions, negative coefficient", () => {
    expect(values("x + 2 = 4")).toEqual(["2"]);
    expect(values("2x + 3 = 7")).toEqual(["2"]);
    expect(values("3x + 2 = x + 10")).toEqual(["4"]);
    expect(values("2(x + 3) = 14")).toEqual(["4"]);
    expect(values("x/2 + 1 = 4")).toEqual(["6"]);
    expect(values("-3x = 12")).toEqual(["-4"]);
    expect(values("5 = 2x + 1")).toEqual(["2"]);
    expect(values("3x + 2 = 7")).toEqual(["5/3"]);
    expect(values("x/3 = 1/2")).toEqual(["3/2"]);
  });
  it("identity and no solution", () => {
    expect(solved("2x + 2 = 2(x + 1)").s.status).toBe("identity");
    expect(solved("2x + 3 = 2x + 5").s.status).toBe("no_solution");
  });
  it("uses the student's letter in the trace", () => {
    const { s } = solved("3n - 2 = 10");
    expect(s.answer).toEqual({ kind: "values", values: ["4"] });
    expect(JSON.stringify(s.steps)).toContain("3n");
  });
  it("teaches the same operation on both sides, never moving a term across", () => {
    for (const t of ["2x + 3 = 7", "3x + 2 = x + 10", "x - 4 = 9", "2(x + 3) = 14"]) {
      const text = renderSteps(solved(t).s.steps).join(" ");
      expect(text).toMatch(/both sides/);
      expect(text).not.toMatch(/across|flip|change the sign|transpos|move (it|the|each)/i);
    }
  });
});

describe("quadratics", () => {
  it("factorable, repeated, zero root, leading coefficient", () => {
    expect(values("x^2 - 5x + 6 = 0")).toEqual(["2", "3"]);
    expect(values("x^2 - 4x + 4 = 0")).toEqual(["2"]);
    expect(values("x^2 = 3x")).toEqual(["0", "3"]);
    expect(values("2x^2 - 3x - 2 = 0")).toEqual(["-1/2", "2"]);
    expect(values("x^2 = 9")).toEqual(["-3", "3"]);
    expect(values("(x - 1)(x + 4) = 0")).toEqual(["-4", "1"]);
  });
  it("exact surds, no floats", () => {
    const a = solved("x^2 + x - 1 = 0").s.answer;
    expect(a).toEqual({ kind: "surd", values: [], surds: ["-1/2-1/2√5", "-1/2+1/2√5"] });
    const b = solved("x^2 - 2 = 0").s.answer;
    expect(b).toEqual({ kind: "surd", values: [], surds: ["-√2", "√2"] });
    const c = solved("x^2 - 8 = 0").s.answer;
    expect(c).toEqual({ kind: "surd", values: [], surds: ["-2√2", "2√2"] });
    expect(JSON.stringify(solved("3x^2 - 2x - 2 = 0").s.answer)).not.toMatch(/\d\.\d/);
  });
  it("no real roots", () => {
    const { s } = solved("x^2 + 1 = 0");
    expect(s.status).toBe("no_solution");
    expect(s.why).toBe("no_real_roots");
    expect(s.steps.map((x) => x.rule)).toContain("no_real_roots");
  });
  it("cubics and quartics with rational roots", () => {
    expect(values("(x-1)(x-2)(x-3) = 0")).toEqual(["1", "2", "3"]);
    expect(values("x^3 - x = 0")).toEqual(["-1", "0", "1"]);
    expect(solved("x^3 - 2 = 0").s.status).toBe("unsupported");
  });
  it("every answer is put back exactly", () => {
    for (const t of ["x^2 - 5x + 6 = 0", "x^2 + x - 1 = 0", "2x^2 = 3x + 2", "x^2 - 8 = 0"]) {
      const { s } = solved(t);
      expect(s.checked).toEqual({ by: "substitution", exact: true, ok: true });
    }
  });
});

describe("simplify and systems", () => {
  it("expands and collects", () => {
    expect(solved("(x + 1)^2").s.answer).toMatchObject({ kind: "expr", value: "x^2 + 2x + 1" });
    expect(solved("2(x + 3) - x").s.answer).toMatchObject({ kind: "expr", value: "x + 6" });
    expect(solved("(x + 2)(x - 2)").s.answer).toMatchObject({ kind: "expr", value: "x^2 - 4" });
  });
  it("2x2 systems", () => {
    expect(solved("x + y = 5; x - y = 1").s.answer).toEqual({ kind: "pair", x: "3", y: "2" });
    expect(solved("2x + 3y = 12; x - y = 1").s.answer).toEqual({ kind: "pair", x: "3", y: "2" });
    expect(solved("3x + 2y = 7; 2x + 5y = 12").s.answer).toEqual({ kind: "pair", x: "1", y: "2" });
    expect(solved("x = 4; x + y = 6").s.answer).toEqual({ kind: "pair", x: "4", y: "2" });
    expect(solved("x + y = 2; 2x + 2y = 4").s.status).toBe("identity");
    expect(solved("x + y = 2; x + y = 3").s.status).toBe("no_solution");
  });
});

describe("rule ids are closed", () => {
  it("every step names a known rule", () => {
    const known = new Set<string>(RULE_IDS);
    for (const t of ["2x+3=7", "x^2+x-1=0", "x^2+1=0", "(x-1)(x-2)(x-3)=0", "x+y=5;x-y=1", "(x+1)^2", "2+3*4", "3x+2=x+10"]) {
      for (const st of solved(t).s.steps) expect(known.has(st.rule), `${t}: ${st.rule}`).toBe(true);
    }
  });
});

describe("property tests against an independent BigInt oracle", () => {
  it("linear a x + b = c: solver root equals c-b over a (400 random)", () => {
    const r = rng(21);
    for (let i = 0; i < 400; i++) {
      let a = int(r, -12, 12);
      if (a === 0) a = 3;
      const b = int(r, -30, 30);
      const c = int(r, -30, 30);
      const text = `${a}x + ${b} = ${c}`.replace("+ -", "- ");
      const { s } = solved(text);
      const num = BigInt(c - b);
      const den = BigInt(a);
      const g = bgcd(num, den) || BigInt(1);
      let n = num / g;
      let d = den / g;
      if (d < B0) {
        n = -n;
        d = -d;
      }
      expect(s.answer).toEqual({ kind: "values", values: [d === BigInt(1) ? `${n}` : `${n}/${d}`] });
      expect(s.checked.ok).toBe(true);
    }
  });
  it("quadratics built from roots: solver returns exactly those roots (300 random)", () => {
    const r = rng(33);
    for (let i = 0; i < 300; i++) {
      const [p, q] = [Frac.of(int(r, -9, 9), int(r, 1, 4)), Frac.of(int(r, -9, 9), int(r, 1, 4))];
      const a = int(r, 1, 4);
      // a (x - p)(x - q) = a x^2 - a(p+q) x + a p q; cleared to integers
      const lcm = p.d * q.d;
      const A = BigInt(a) * lcm * lcm;
      const B = p.add(q).neg().mul(Frac.of(A));
      const C = p.mul(q).mul(Frac.of(A));
      const text = `${A}x^2 + (${B})x + (${C}) = 0`;
      const { s } = solved(text);
      const expected = [...new Set([p.toString(), q.toString()])].sort((u, v) => (Frac.parse(u) as Frac).cmp(Frac.parse(v) as Frac));
      expect(s.answer).toEqual({ kind: "values", values: expected });
      expect(s.checked.ok).toBe(true);
    }
  });
  it("2x2 systems with a planted solution (300 random)", () => {
    const r = rng(44);
    let n = 0;
    for (let i = 0; i < 300; i++) {
      const [a1, b1, a2, b2] = [int(r, -6, 6), int(r, -6, 6), int(r, -6, 6), int(r, -6, 6)];
      if (a1 * b2 - a2 * b1 === 0) continue;
      const [x, y] = [int(r, -9, 9), int(r, -9, 9)];
      const c1 = a1 * x + b1 * y;
      const c2 = a2 * x + b2 * y;
      const text = `(${a1})x + (${b1})y = ${c1}; (${a2})x + (${b2})y = ${c2}`;
      const { s } = solved(text);
      expect(s.answer, text).toEqual({ kind: "pair", x: String(x), y: String(y) });
      n++;
    }
    expect(n).toBeGreaterThan(200);
  });
  it("irrational quadratics: roots satisfy the equation exactly (200 random)", () => {
    const r = rng(55);
    let n = 0;
    for (let i = 0; i < 200; i++) {
      const [a, b, c] = [int(r, 1, 5), int(r, -9, 9), int(r, -9, 9)];
      const text = `${a}x^2 + (${b})x + (${c}) = 0`;
      const d = b * b - 4 * a * c;
      const { s } = solved(text);
      if (d < 0) expect(s.status).toBe("no_solution");
      else expect(s.checked.ok, text).toBe(true);
      n++;
    }
    expect(n).toBe(200);
  });
  it("solve never throws on odd candidates", () => {
    expect(solve({ schema: "doubt-expr/1", kind: "poly_eq", variable: "x", display: "?" }).status).toBe("unsupported");
    expect(solve({ schema: "doubt-expr/1", kind: "linear_system", variable: "xy", display: "?" }).status).toBe("unsupported");
  });
});
