import { describe, expect, it } from "vitest";
import { boardLabel, messageText, optionLabel, prettify } from "@/lib/chat/labels";
import { initialState, reduce, type ContextLike } from "@/lib/chat/machine";
import { t } from "@/lib/messages";

const copy = t("en");
const ctx: ContextLike = {
  curricula: [
    { id: "sample_board", titles: { en: "Sample Board", hi: "नमूना" }, grades: [] },
    { id: "plain_board", grades: [] },
  ],
};

describe("registry labels", () => {
  it("turns an id into readable words when the registry gives no title", () => {
    expect(prettify("plain_board")).toBe("Plain board");
    expect(prettify("math")).toBe("Math");
  });

  it("uses the registry title in the visitor's language, then English, then the id", () => {
    expect(boardLabel(ctx, "sample_board", "hi")).toBe("नमूना");
    expect(boardLabel(ctx, "sample_board", "ne")).toBe("Sample Board");
    expect(boardLabel(ctx, "plain_board", "en")).toBe("Plain board");
    expect(boardLabel(null, "any_id", "en")).toBe("Any id");
  });

  it("puts class numbers through the locale string", () => {
    expect(optionLabel(copy, ctx, "grade", 9, "en")).toBe("Class 9");
  });
});

describe("finished workflow summaries", () => {
  it("the machine adds a short structured note: titles and a status, never typed text", () => {
    const s = reduce(initialState(), { type: "summary", skill: "Two-step equations", status: "can_do_it", next: "Multi-step" }, ctx);
    const note = s.messages.at(-1)!;
    expect(note.key).toBe("summary");
    expect(Object.keys(note.data ?? {}).sort()).toEqual(["next", "skill", "status"]);
    expect(messageText(copy, ctx, note, "en")).toBe("You worked on Two-step equations. (Can do it) Next up: Multi-step.");
  });

  it("says something kind even when it knows nothing about the session", () => {
    const s = reduce(initialState(), { type: "summary" }, ctx);
    expect(messageText(copy, ctx, s.messages.at(-1)!, "en")).toBe(copy.chatSummaryGeneric);
  });
});
