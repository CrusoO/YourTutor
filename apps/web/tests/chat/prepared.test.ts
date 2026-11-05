import { describe, expect, it } from "vitest";
import { compileFormula, finiteOver } from "@/lib/lessons/formula";
import { usableBlocks, type AiBlock } from "@/lib/lessons/ai-lesson";
import { blockSpeech } from "@/lib/lessons/block-speech";
import { PREPARED_TRAIN_BLOCKS } from "@/lib/lessons/prepared-train";
import { findPrepared, normalise, preparedEnabled } from "@/lib/chat/prepared";

const DEMO =
  "I've tried this five times and I keep getting two answers, 40 and -45, and I don't know which one is right. A train travels 360 km at a uniform speed. If the speed had been 5 km/h more, it would have taken 1 hour less. Find the speed of the train. I'm so frustrated.";

describe("normalise", () => {
  it("lower-cases, unifies minus signs and quotes, and collapses spaces", () => {
    expect(normalise("  A   TRAIN− 45’s\n km ")).toBe("a train- 45's km");
  });
});

describe("findPrepared", () => {
  it("matches the demo question exactly as typed", () => {
    expect(findPrepared(DEMO)?.id).toBe("train-360-km");
  });
  it("still matches with other spaces, capitals and a unicode minus", () => {
    expect(findPrepared(DEMO.toUpperCase().replace("-45", "−45").replace(/ /g, "  "))?.id).toBe("train-360-km");
  });
  it("matches the textbook wording without the emotional lead-in", () => {
    expect(findPrepared("A train travels 360 km at a uniform speed. If the speed had been 5 km/h more, it would have taken 1 hour less. Find the speed of the train.")?.id).toBe("train-360-km");
  });
  it("does not match a similar question with other numbers", () => {
    expect(findPrepared("A train travels 480 km at a uniform speed. If the speed had been 8 km/h more, it would have taken 3 hours less. Find the speed of the train.")).toBeNull();
  });
  it("does not match a train question that lacks the 5 km/h and 1 hour", () => {
    expect(findPrepared("A train travels 360 km at a uniform speed. How long does it take at 40 km/h?")).toBeNull();
  });
  it("does not match an unrelated or empty question", () => {
    expect(findPrepared("what is photosynthesis")).toBeNull();
    expect(findPrepared("   ")).toBeNull();
  });
  it("does not match a very long text that merely contains the words", () => {
    expect(findPrepared(DEMO + " " + "x".repeat(600))).toBeNull();
  });
});

describe("preparedEnabled", () => {
  it("is on only for the exact value true", () => {
    expect(preparedEnabled("true")).toBe(true);
    for (const v of [undefined, "", "false", "1", "TRUE", "yes"]) expect(preparedEnabled(v)).toBe(false);
  });
});

describe("the prepared train lesson", () => {
  it("is a lesson the existing player accepts, with nothing dropped", () => {
    const usable = usableBlocks({ kind: "lesson", level: "class 10", objectives: [], blocks: PREPARED_TRAIN_BLOCKS });
    expect(usable).not.toBeNull();
    expect(usable!.length).toBe(PREPARED_TRAIN_BLOCKS.length);
  });
  it("starts with a hook and a prediction, and has a picture, a widget and a check", () => {
    const kinds = PREPARED_TRAIN_BLOCKS.map((b: AiBlock) => b.kind);
    expect(kinds.slice(0, 2)).toEqual(["hook", "predict"]);
    expect(kinds).toContain("widget");
    expect(kinds).toContain("check");
    expect(kinds[kinds.length - 1]).toBe("recap");
  });
  it("has maths that is true: time = 360 / speed, 40 gives 9 h, 45 gives 8 h", () => {
    const w = PREPARED_TRAIN_BLOCKS.find((b: AiBlock) => b.kind === "widget" && b.widget_kind === "slider_sim");
    expect(w).toBeDefined();
    const spec = (w as Extract<AiBlock, { kind: "widget" }>).spec as { variable: string; formula: string; min: number; max: number };
    const f = compileFormula(spec.formula, [spec.variable])!;
    expect(f({ [spec.variable]: 40 })).toBe(9);
    expect(f({ [spec.variable]: 45 })).toBe(8);
    expect(finiteOver(f, spec.variable, spec.min, spec.max, {})).toBe(true);
  });
  it("marks the right answers: 40 km/h is a speed, -45 is not; 45 km/h takes 8 hours", () => {
    const checks = PREPARED_TRAIN_BLOCKS.filter((b: AiBlock) => b.kind === "check") as Extract<AiBlock, { kind: "check" }>[];
    expect(checks.length).toBeGreaterThanOrEqual(2);
    const speed = checks.find((c) => /speed/i.test(c.question))!;
    expect(speed.options[speed.correct]).toMatch(/^40/);
    const hours = checks.find((c) => /45/.test(c.question))!;
    expect(hours.options[hours.correct]).toMatch(/^8 hours/);
    for (const c of checks) {
      expect(c.feedback_per_option).toHaveLength(c.options.length);
      expect(c.hint_ladder.length).toBeGreaterThan(0);
    }
  });
  it("keeps every line short and plain: no sentence over 28 words", () => {
    const text = PREPARED_TRAIN_BLOCKS.map((b) => blockSpeech(b)).join(" ");
    for (const s of text.split(/(?<=[.?!])\s+/)) expect(s.split(/\s+/).length).toBeLessThanOrEqual(28);
  });
});

describe("blockSpeech", () => {
  it("returns the words a block says, and nothing for a widget without text", () => {
    expect(blockSpeech({ kind: "hook", text: "One.", question: "Two?" })).toBe("One. Two?");
    expect(blockSpeech({ kind: "explain", text: "A.", analogy: "B." })).toContain("B.");
    expect(blockSpeech({ kind: "recap", three_bullets: ["a", "b", "c"], spaced_review_question: "q?" })).toContain("q?");
  });
});
