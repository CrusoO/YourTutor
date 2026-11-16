import { describe, expect, it } from "vitest";
import { detectMath } from "@/lib/doubt/detect";

const kind = (t: string) => {
  const d = detectMath(t);
  return d.kind === "candidate" ? d.candidate.kind : d.kind === "unsupported" ? `unsupported:${d.why}` : "none";
};

describe("detectMath", () => {
  it("finds the usual classes", () => {
    expect(kind("2x + 3 = 7")).toBe("poly_eq");
    expect(kind("x^2 - 5x + 6 = 0")).toBe("poly_eq");
    expect(kind("2(3+4)*5")).toBe("arith");
    expect(kind("12 / 4 + 3")).toBe("arith");
    expect(kind("(x+1)^2")).toBe("poly_simplify");
    expect(kind("x + y = 5 and x - y = 1")).toBe("linear_system");
    expect(kind("2x+3y=12; x-y=1")).toBe("linear_system");
    expect(kind("5 + 3 = 8")).toBe("arith");
  });
  it("sentences are not candidates", () => {
    for (const s of [
      "my name is Ravi and I am 12",
      "I have 2 apples and 3 pears",
      "what is the capital of France",
      "please explain photosynthesis",
      "I scored 90 in maths yesterday",
      "meet me at 5 pm",
    ]) {
      expect(detectMath(s).kind, s).not.toBe("candidate");
    }
    expect(kind("Ravi has 3 apples and buys 4 more, how many now? 3 + 4")).toBe("unsupported:word_problem");
  });
  it("phone numbers never become numbers", () => {
    for (const s of ["9876543210", "+91 98765 43210", "call 98765-43210", "my number is 9876543210 and 2x+3=7", "0123456789012"]) {
      const d = detectMath(s);
      if (d.kind === "candidate") {
        expect(JSON.stringify(d.candidate)).not.toMatch(/\d{7,}/);
        expect(d.candidate.display).not.toMatch(/98765|43210/);
      }
    }
    expect(detectMath("+91 98765 43210").kind).toBe("none");
    expect(kind("2000000000 + 1")).not.toBe("arith");
    expect(kind("123456789 + 1")).toBe("arith");
  });
  it("strips Hinglish, Hindi and English verbs", () => {
    for (const s of [
      "solve 2x+3=7",
      "2x+3=7 hal karo",
      "x ka value nikalo 2x+3=7",
      "find x if 2x + 3 = 7",
      "2x+3=7 हल करो",
      "please solve 2x+3=7 pls",
      "2x+3=7, find x",
      "2x+3=7 ka answer batao",
    ]) {
      const d = detectMath(s);
      expect(d.kind, s).toBe("candidate");
      if (d.kind === "candidate") expect(d.candidate.lhs).toEqual(["3", "2"]);
    }
  });
  it("keeps the student's letter for display and uses x inside", () => {
    const d = detectMath("3n - 2 = 10");
    expect(d.kind === "candidate" && d.candidate.variable).toBe("n");
    expect(d.kind === "candidate" && d.candidate.lhsText).toBe("3*x - 2");
    expect(d.kind === "candidate" && d.candidate.display).toContain("n");
  });
  it("says why when it cannot help", () => {
    expect(kind("sin x = 1/2")).toBe("unsupported:function");
    expect(kind("2x + 3 < 7")).toBe("unsupported:inequality");
    expect(kind("a + b = c")).toBe("unsupported:multi_unknown");
    expect(kind("1/x = 3")).toBe("unsupported:rational_function");
    expect(kind("x^20 = 1")).toBe("unsupported:too_big");
    expect(detectMath("a".repeat(500)).kind).toBe("unsupported");
  });
  it("needs an operator and two operands", () => {
    for (const s of ["", "   ", "7", "x", "hello", "2x", "?!", "="]) expect(detectMath(s).kind, s).not.toBe("candidate");
  });
  it("reads 3 x 4 as multiplication and an equals-with-claim as arithmetic", () => {
    const d = detectMath("3 x 4");
    expect(d.kind === "candidate" && d.candidate.kind).toBe("arith");
    const e = detectMath("2+3=6");
    expect(e.kind === "candidate" && e.candidate.claimed).toBe("6");
  });
});
