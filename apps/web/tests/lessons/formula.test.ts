import { describe, expect, it } from "vitest";
import { compileFormula, finiteOver, linspace } from "@/lib/lessons/formula";

const run = (src: string, vars: Record<string, number> = {}) => compileFormula(src, Object.keys(vars))?.(vars);

describe("compileFormula", () => {
  it("does arithmetic with the usual precedence and a right-binding power", () => {
    expect(run("2 + 3 * 4")).toBe(14);
    expect(run("(2 + 3) * 4")).toBe(20);
    expect(run("2 ^ 3 ^ 2")).toBe(512);
    expect(run("-2 ^ 2")).toBe(-4);
    expect(run("2 ** 3")).toBe(8);
    expect(run("10 / 4")).toBe(2.5);
  });

  it("uses the named variables, multi-letter names included", () => {
    expect(run("0.5 * mass * velocity ^ 2", { mass: 2, velocity: 3 })).toBe(9);
    expect(run("barrier_width * 2", { barrier_width: 4 })).toBe(8);
  });

  it("knows a short list of functions and the constants pi and e", () => {
    expect(run("sqrt(16)")).toBe(4);
    expect(run("exp(0)")).toBe(1);
    expect(run("ln(e)")).toBeCloseTo(1);
    expect(run("log(1000)")).toBeCloseTo(3);
    expect(run("abs(-3)")).toBe(3);
    expect(run("cos(0) + sin(0)")).toBe(1);
    expect(run("2 * pi")).toBeCloseTo(6.283185, 5);
    expect(run("exp(-2 * x)", { x: 1 })).toBeCloseTo(Math.exp(-2));
  });

  it("lets a variable shadow a constant", () => {
    expect(run("e * 2", { e: 5 })).toBe(10);
  });

  it("rejects anything outside the grammar instead of running it", () => {
    for (const bad of [
      "alert(1)",
      "constructor",
      "x.y",
      "x['a']",
      "window",
      "1; 2",
      "a = 1",
      "`x`",
      "x => x",
      "2 +",
      "(1 + 2",
      "1 + 2)",
      "unknown + 1",
      "",
    ]) {
      expect(compileFormula(bad, ["x"]), bad).toBeNull();
    }
  });

  it("rejects an over-long or over-nested formula", () => {
    expect(compileFormula("1+".repeat(150) + "1", [])).toBeNull();
    expect(compileFormula("(".repeat(20) + "1" + ")".repeat(20), [])).toBeNull();
  });

  it("does not let a function name be used as a plain variable that is not allowed", () => {
    expect(compileFormula("sqrt", [])).toBeNull();
  });
});

describe("finiteOver", () => {
  it("accepts a formula that is finite across the range and rejects one that is not", () => {
    const fine = compileFormula("x ^ 2", ["x"])!;
    const bad = compileFormula("1 / x", ["x"])!;
    expect(finiteOver(fine, "x", -5, 5)).toBe(true);
    expect(finiteOver(bad, "x", -5, 5)).toBe(false);
    expect(finiteOver(compileFormula("sqrt(x)", ["x"])!, "x", -1, 1)).toBe(false);
  });

  it("linspace includes both ends", () => {
    expect(linspace(0, 1, 3)).toEqual([0, 0.5, 1]);
    expect(linspace(2, 2, 1)).toEqual([2]);
  });
});
