import { describe, expect, it } from "vitest";
import { canon, evalNum, parseEquation, parseExpr, toLinear, toPoly } from "@/lib/doubt/parse";
import { qToString } from "@/lib/doubt/surd";
import { int, rng } from "./helpers";

const val = (s: string): string => {
  const p = parseExpr(s);
  if (!p.ok) throw new Error(`parse failed: ${s} ${p.why}`);
  const v = evalNum(p.ast);
  return v ? qToString(v) : "null";
};

describe("parser", () => {
  it("respects precedence and associativity", () => {
    expect(val("2+3*4")).toBe("14");
    expect(val("(2+3)*4")).toBe("20");
    expect(val("8-3-2")).toBe("3");
    expect(val("2^3^2")).toBe("512");
    expect(val("-2^2")).toBe("-4");
    expect(val("2^-2")).toBe("1/4");
    expect(val("1/2+1/3")).toBe("5/6");
  });
  it("reads implicit multiplication, decimals and Unicode", () => {
    expect(val("2(3+4)")).toBe("14");
    expect(val("3×4÷2")).toBe("6");
    expect(val("−5+2")).toBe("-3");
    expect(val("0.1+0.2")).toBe("3/10");
    expect(val("२+३")).toBe("5");
    expect(val("√16")).toBe("4");
    expect(val("2²")).toBe("4");
    expect(val("\\frac{1}{2}+\\frac{1}{4}")).toBe("3/4");
  });
  it("is an allow-list: no eval, no code, no identifiers", () => {
    for (const bad of ["alert(1)", "constructor", "process.exit()", "1;2", "2**", "2+", "()", "1,2", "a[0]", "{}", "1+1=2=3", "2 3"]) {
      expect(parseExpr(bad).ok, bad).toBe(false);
    }
    expect(parseExpr("sin(x)")).toEqual({ ok: false, why: "function" });
    expect(parseExpr("2<3")).toEqual({ ok: false, why: "inequality" });
  });
  it("caps digits, length and depth", () => {
    expect(parseExpr("1".repeat(30))).toEqual({ ok: false, why: "too_big" });
    expect(parseExpr("1+".repeat(300) + "1")).toEqual({ ok: false, why: "too_big" });
    expect(parseExpr("(".repeat(60) + "1" + ")".repeat(60))).toEqual({ ok: false, why: "too_big" });
  });
  it("never evaluates a huge power into a hang", () => {
    const t0 = Date.now();
    const p = parseExpr("9^99999999");
    const poly = p.ok ? toPoly(p.ast, null) : p;
    expect(poly.ok).toBe(false);
    expect(Date.now() - t0).toBeLessThan(500);
  });
  it("splits equations on exactly one equals sign", () => {
    expect(parseEquation("2x+3=7").ok).toBe(true);
    expect(parseEquation("2x+3").ok).toBe(false);
    expect(parseEquation("1=2=3").ok).toBe(false);
  });
  it("turns expressions into exact polynomials, refusing what it cannot do", () => {
    const p = parseExpr("(x+1)(x-1)");
    const r = p.ok ? toPoly(p.ast, "x") : null;
    expect(r && r.ok && r.poly.show()).toBe("x^2 - 1");
    const div = parseExpr("1/x");
    expect(div.ok && toPoly(div.ast, "x")).toEqual({ ok: false, why: "rational_function" });
    const two = parseExpr("x+y");
    expect(two.ok && toPoly(two.ast, "x")).toEqual({ ok: false, why: "multi_unknown" });
    const irr = parseExpr("√2");
    expect(irr.ok && toPoly(irr.ast, null)).toEqual({ ok: false, why: "irrational" });
    const lin = parseExpr("2x+3y-1");
    const l = lin.ok ? toLinear(lin.ast) : null;
    expect(l && l.ok && l.lin.coef.get("y")?.toString()).toBe("3");
  });
  it("property: canon() round-trips to the same value (500 random trees)", () => {
    const r = rng(5);
    const gen = (d: number): string => {
      if (d === 0 || r() < 0.3) return String(int(r, 1, 9));
      const op = ["+", "-", "*", "/"][int(r, 0, 3)];
      return `(${gen(d - 1)}${op}${gen(d - 1)})`;
    };
    let n = 0;
    for (let i = 0; i < 500; i++) {
      const a = parseExpr(gen(3));
      if (!a.ok) continue;
      const v1 = evalNum(a.ast);
      const b = parseExpr(canon(a.ast));
      expect(b.ok).toBe(true);
      if (!v1 || !b.ok) continue;
      const v2 = evalNum(b.ast);
      expect(v2 && qToString(v2)).toBe(qToString(v1));
      n++;
    }
    expect(n).toBeGreaterThan(300);
  });
});
