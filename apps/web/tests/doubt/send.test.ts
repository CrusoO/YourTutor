import { readFileSync } from "node:fs";
import { join } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import { doubtServerEnabled } from "@/lib/flags";
import { checkOnServer, readResult, refusalOf, toDoubtExpr, valid, type DoubtExprWire } from "@/lib/doubt/send";
import type { MathCandidate } from "@/lib/doubt/types";

const CASES = JSON.parse(
  readFileSync(join(process.cwd(), "..", "..", "packages", "shared", "fixtures", "doubt", "cases.json"), "utf8"),
) as (MathCandidate & { id: string; status: string })[];

const lin: MathCandidate = {
  schema: "doubt-expr/1",
  kind: "poly_eq",
  variable: "x",
  display: "2x + 3 = 7 and my name is Asha",
  lhsText: "2*x + 3",
  rhsText: "7",
  lhs: ["3", "2"],
  rhs: ["7"],
};

const good = {
  schema: "doubt-result/1",
  verified: true,
  label: "checked_by_code",
  reason: null,
  answer: { kind: "values", values: ["2"] },
  steps: [{ rule: "subtract_both_sides", args: { amount: "3" }, before: "2x + 3 = 7", after: "2x = 4" }],
  proof: { kernel: "1", checker: "algebra:1" },
};

afterEach(() => vi.unstubAllEnvs());

describe("the server flag", () => {
  it("is off unless exactly true", () => {
    expect(doubtServerEnabled()).toBe(false);
    vi.stubEnv("NEXT_PUBLIC_DOUBT_SERVER", "1");
    expect(doubtServerEnabled()).toBe(false);
    vi.stubEnv("NEXT_PUBLIC_DOUBT_SERVER", "true");
    expect(doubtServerEnabled()).toBe(true);
  });
});

describe("toDoubtExpr", () => {
  it("sends numbers and two enumerated words, never the student's text or display", () => {
    const w = toDoubtExpr(lin);
    expect(w).toEqual({ schema: "doubt-expr/1", kind: "poly_eq", lhs: ["3", "2"], rhs: ["7"] });
    expect(JSON.stringify(w)).not.toMatch(/Asha|display|Text/);
  });
  it("does not send arithmetic or simplify", () => {
    expect(toDoubtExpr({ ...lin, kind: "arith", expr: "2+2" })).toBeNull();
    expect(toDoubtExpr({ ...lin, kind: "poly_simplify", expr: "(x+1)^2" })).toBeNull();
  });
  it("refuses a number longer than nine digits and a zero denominator", () => {
    expect(toDoubtExpr({ ...lin, rhs: ["9876543210"] })).toBeNull();
    expect(toDoubtExpr({ ...lin, rhs: ["1/0"] })).toBeNull();
    expect(toDoubtExpr({ ...lin, rhs: ["x"] })).toBeNull();
    expect(toDoubtExpr({ ...lin, lhs: ["1", "1", "1", "1", "1", "1"] })).toBeNull();
  });
  it("builds a system", () => {
    const sys: MathCandidate = {
      ...lin,
      kind: "linear_system",
      system: { coeffs: [["1", "1"], ["1", "-1"]], consts: ["5", "1"], texts: ["x + y=5", "x - y=1"] },
    };
    expect(toDoubtExpr(sys)).toEqual({
      schema: "doubt-expr/1",
      kind: "linear_system",
      system: { coeffs: [["1", "1"], ["1", "-1"]], consts: ["5", "1"] },
    });
  });
  it("every shared fixture that can be sent is a valid wire object with no free text", () => {
    let sent = 0;
    for (const c of CASES) {
      const w = toDoubtExpr(c);
      if (!w) continue;
      sent++;
      expect(valid(w), c.id).toBe(true);
      const strings: string[] = [];
      JSON.stringify(w, (_k, v) => (typeof v === "string" && (strings.push(v), v)) || v);
      for (const s of strings) expect(s, c.id).toMatch(/^(doubt-expr\/1|poly_eq|linear_system|-?[0-9]{1,9}(\/[0-9]{1,9})?)$/);
    }
    expect(sent).toBeGreaterThanOrEqual(45);
  });
});

describe("readResult", () => {
  it("accepts only a complete kernel-verified reply as verified", () => {
    expect(readResult(good)).toMatchObject({ verified: true });
    for (const bad of [
      { ...good, label: "not_verified" },
      { ...good, proof: null },
      { ...good, schema: "x" },
      { ...good, steps: [{ rule: "move_across", args: {}, before: "", after: "" }] },
      { ...good, answer: { kind: "weird" } },
      null,
      "text",
    ]) {
      expect(readResult(bad), JSON.stringify(bad)).toMatchObject({ verified: false });
    }
  });
  it("passes the server's reason through when not verified", () => {
    expect(readResult({ schema: "doubt-result/1", verified: false, reason: "irrational_roots" })).toEqual({
      verified: false,
      reason: "irrational_roots",
    });
  });
});

describe("refusals", () => {
  it("maps status and code", () => {
    expect(refusalOf(404, null)).toBe("disabled");
    expect(refusalOf(403, { detail: { code: "math_check_consent_required" } })).toBe("consent");
    expect(refusalOf(429, null)).toBe("rate");
    expect(refusalOf(422, null)).toBe("invalid");
    expect(refusalOf(500, null)).toBe("failed");
  });
});

describe("checkOnServer", () => {
  it("hands the transport exactly the wire JSON", async () => {
    const t = vi.fn().mockResolvedValue({ status: 200, json: good });
    const out = await checkOnServer(lin, t);
    expect(t).toHaveBeenCalledTimes(1);
    const sent = JSON.parse(t.mock.calls[0][0]) as DoubtExprWire;
    expect(sent).toEqual(toDoubtExpr(lin));
    expect(out).toMatchObject({ ok: true, result: { verified: true } });
  });
  it("does not call the transport for a kind that is not sent", async () => {
    const t = vi.fn();
    expect(await checkOnServer({ ...lin, kind: "arith", expr: "1+1" }, t)).toBeNull();
    expect(t).not.toHaveBeenCalled();
  });
  it("turns a refusal or a network failure into a refusal", async () => {
    expect(await checkOnServer(lin, async () => ({ status: 403, json: { detail: { code: "math_check_consent_required" } } }))).toEqual({
      ok: false,
      refusal: "consent",
    });
    expect(
      await checkOnServer(lin, async () => {
        throw new Error("down");
      }),
    ).toEqual({ ok: false, refusal: "failed" });
  });
});
