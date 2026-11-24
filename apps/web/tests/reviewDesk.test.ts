import { afterEach, describe, expect, it, vi } from "vitest";
import {
  allYes,
  buildBody,
  clampSeconds,
  CHECK_COUNT,
  dayFraction,
  emptyDraft,
  enoughNote,
  formatClock,
  formatHours,
  keyAction,
  median,
  missingNotes,
  moveBlocked,
  placeServerErrors,
  problemsFor,
  rememberTour,
  tickSeconds,
  tourSeen,
  type Draft,
} from "@/lib/reviewDesk";

const yes = (): Draft => ({ ...emptyDraft(), checks: [true, true, true] });

describe("notes", () => {
  it("counts only characters that are not spaces", () => {
    expect(enoughNote("1234567")).toBe(false);
    expect(enoughNote("1234 5678")).toBe(true);
    expect(enoughNote("   a b c d   ")).toBe(false);
    expect(enoughNote("")).toBe(false);
  });

  it("lists each needs-a-fix question whose note is too short, and blocks moving on", () => {
    const d = { ...emptyDraft(), checks: [true, false, false] as Draft["checks"], notes: ["", "short", "this is long enough"] };
    expect(missingNotes(d)).toEqual([1]);
    expect(moveBlocked(d)).toBe(true);
    expect(moveBlocked({ ...d, notes: ["", "now long enough", "this is long enough"] })).toBe(false);
  });
});

describe("what each decision needs", () => {
  it("has three questions, and approve needs all three yes", () => {
    expect(CHECK_COUNT).toBe(3);
    expect(emptyDraft().checks).toHaveLength(3);
    expect(problemsFor("approve", emptyDraft()).map((p) => p.field)).toEqual(["checks"]);
    expect(problemsFor("approve", { ...yes(), checks: [true, true, false] }).length).toBe(1);
    expect(problemsFor("approve", yes())).toEqual([]);
    expect(allYes(yes())).toBe(true);
  });

  it("fix and reject need a severity, a reason and a note for each needs-a-fix answer", () => {
    const d = { ...yes(), checks: [true, false, true] as Draft["checks"] };
    expect(problemsFor("fix", d).map((p) => p.field)).toEqual(["severity", "reason_code", "fix_notes"]);
    // Reject needs no severity: it is always a blocker
    expect(problemsFor("reject", d).map((p) => p.field)).toEqual(["reason_code", "fix_notes"]);
    const ready = { ...d, severity: "must_fix" as const, reason: "4", notes: ["", "the formula is wrong", ""] };
    expect(problemsFor("reject", ready)).toEqual([]);
    expect(problemsFor("fix", ready)).toEqual([]);
  });

  it("with no question marked, the general note must have 8 characters", () => {
    const d = { ...yes(), severity: "blocker" as const, reason: "6" };
    expect(problemsFor("fix", d).map((p) => p.field)).toEqual(["note"]);
    expect(problemsFor("fix", { ...d, note: "this is wrong" })).toEqual([]);
  });

  it("skip is blocked only by an unfinished required note", () => {
    expect(problemsFor("skip", emptyDraft())).toEqual([]);
    const d = { ...emptyDraft(), checks: [false, null, null] as Draft["checks"] };
    expect(problemsFor("skip", d)).toHaveLength(1);
  });
});

describe("request body", () => {
  const card = { content_hash: "h" };
  it("sends the three answers and the clamped time on an approval", () => {
    expect(buildBody(card, "approve", yes(), 99999)).toEqual({
      content_hash: "h",
      decision: "approve",
      checks: [true, true, true],
      active_seconds: 7200,
    });
  });
  it("sends trimmed fix notes by question index, severity and reason", () => {
    const d: Draft = { ...emptyDraft(), checks: [true, false, true], notes: ["", "  fix this now  ", ""], severity: "must_fix", reason: "4", note: "  " };
    expect(buildBody(card, "fix", d, 12.7)).toEqual({
      content_hash: "h",
      decision: "fix",
      checks: [true, false, true],
      severity: "must_fix",
      reason_code: "4",
      fix_notes: [{ question_index: 1, text: "fix this now" }],
      active_seconds: 12,
    });
  });
  it("makes a reject a blocker whatever the severity buttons say", () => {
    const d: Draft = { ...emptyDraft(), checks: [false, true, true], notes: ["the question is unclear", "", ""], severity: "nice_to_fix", reason: "1" };
    expect(buildBody(card, "reject", d, 3)).toMatchObject({ decision: "reject", severity: "blocker", reason_code: "1" });
    expect(buildBody(card, "reject", { ...d, severity: null }, 3)).toMatchObject({ severity: "blocker" });
  });
  it("sends only the time on a skip", () => {
    expect(buildBody(card, "skip", yes(), 5)).toEqual({ content_hash: "h", decision: "skip", active_seconds: 5 });
  });
});

describe("timer", () => {
  it("counts a second only when not paused and the tab is visible", () => {
    expect(tickSeconds(10, { paused: false, hidden: false })).toBe(11);
    expect(tickSeconds(10, { paused: true, hidden: false })).toBe(10);
    expect(tickSeconds(10, { paused: false, hidden: true })).toBe(10);
  });
  it("clamps to what the server accepts", () => {
    expect(clampSeconds(-4)).toBe(0);
    expect(clampSeconds(1e9)).toBe(7200);
    expect(clampSeconds(Number.NaN)).toBe(0);
    expect(formatClock(75)).toBe("1:15");
    expect(median([5, 1, 9])).toBe(5);
  });
});

describe("keys", () => {
  const body = { tagName: "BODY" };
  it("maps the desk keys", () => {
    expect(keyAction("y", body)).toEqual({ kind: "answer", yes: true });
    expect(keyAction("N", body)).toEqual({ kind: "answer", yes: false });
    expect(keyAction("a", body)).toEqual({ kind: "decide", decision: "approve" });
    expect(keyAction("f", body)).toEqual({ kind: "decide", decision: "fix" });
    expect(keyAction("r", body)).toEqual({ kind: "decide", decision: "reject" });
    expect(keyAction("s", body)).toEqual({ kind: "decide", decision: "skip" });
    expect(keyAction("e", body)).toEqual({ kind: "toggleAnswer" });
    for (const k of ["1", "2", "3", "4", "5", "6"]) expect(keyAction(k, body)).toEqual({ kind: "reason", code: k });
    for (const k of ["0", "7", "8", "9"]) expect(keyAction(k, body)).toBeNull();
    expect(keyAction("?", body)).toEqual({ kind: "help" });
    expect(keyAction("Escape", body)).toEqual({ kind: "escape" });
    expect(keyAction("Backspace", body)).toEqual({ kind: "undo" });
  });
  it("does nothing while typing or with a modifier", () => {
    expect(keyAction("y", { tagName: "TEXTAREA" })).toBeNull();
    expect(keyAction("a", { tagName: "INPUT" })).toBeNull();
    expect(keyAction("a", body, { ctrl: true })).toBeNull();
    expect(keyAction("Backspace", { tagName: "TEXTAREA" })).toBeNull();
  });
});

describe("server messages", () => {
  it("puts a fix_notes message on its question", () => {
    expect(placeServerErrors([{ field: "fix_notes", message: "question 3: say what to fix (at least 8 characters)" }, { field: "severity", message: "pick how serious it is" }])).toEqual([
      { field: "fix_notes", message: "question 3: say what to fix (at least 8 characters)", question: 2 },
      { field: "severity", message: "pick how serious it is", question: undefined },
    ]);
  });
});

describe("day meter", () => {
  it("shows hours and minutes", () => {
    expect(formatHours(42 * 60)).toBe("0:42");
    expect(formatHours(12600)).toBe("3:30");
    expect(formatHours(-5)).toBe("0:00");
    expect(dayFraction(6300, 12600)).toBe(0.5);
    expect(dayFraction(99999, 12600)).toBe(1);
    expect(dayFraction(5, 0)).toBe(0);
  });
});

describe("first-time tour memory", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
  });
  it("is unseen at first, then remembered", () => {
    expect(tourSeen()).toBe(false);
    rememberTour();
    expect(tourSeen()).toBe(true);
  });
  it("never throws when storage is blocked: it says unseen and forgets quietly", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(tourSeen()).toBe(false);
    expect(() => rememberTour()).not.toThrow();
  });
});
