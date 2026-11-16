import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { checkAnswer, checkStep } from "@/lib/doubt/attempt";
import { detectMath } from "@/lib/doubt/detect";
import { guardCandidate, guardText, routesToPracticeHelp } from "@/lib/doubt/guard";
import { answerSetFor, hintLeaks } from "@/lib/doubt/leak";
import { buildLadder } from "@/lib/doubt/ladder";
import { detectPushback, finalReply, resolvePushback } from "@/lib/doubt/pushback";
import { solve } from "@/lib/doubt/solve";

const INPUTS = [
  "2x + 3 = 7",
  "x^2 - 5x + 6 = 0",
  "x^2 + x - 1 = 0",
  "2(3+4)*5",
  "(x+1)^2",
  "x + y = 5; x - y = 1",
  "solve 3x+2=x+10",
  "x ka value nikalo 2x+3=7",
  "call 9876543210",
  "I have 2 apples",
  "sin x = 1/2",
];

describe("the doubt solver is isolated from the network, storage and logs", () => {
  const calls: string[] = [];
  const saved: Record<string, unknown> = {};
  const names = ["fetch", "XMLHttpRequest", "WebSocket", "EventSource", "indexedDB", "localStorage", "sessionStorage", "BroadcastChannel"];

  beforeEach(() => {
    calls.length = 0;
    for (const n of names) saved[n] = (globalThis as Record<string, unknown>)[n];
    const trap = (n: string) =>
      new Proxy(function () {}, {
        apply: () => {
          calls.push(n);
          throw new Error(`${n} called`);
        },
        construct: () => {
          calls.push(`new ${n}`);
          throw new Error(`new ${n}`);
        },
        get: (_t, p) => {
          calls.push(`${n}.${String(p)}`);
          throw new Error(`${n}.${String(p)}`);
        },
      });
    for (const n of names) Object.defineProperty(globalThis, n, { value: trap(n), configurable: true, writable: true });
    Object.defineProperty(globalThis.navigator, "sendBeacon", { value: () => calls.push("sendBeacon"), configurable: true });
    for (const m of ["log", "info", "warn", "error", "debug", "trace"] as const) vi.spyOn(console, m).mockImplementation(() => calls.push(`console.${m}`));
  });
  afterEach(() => {
    for (const n of names) Object.defineProperty(globalThis, n, { value: saved[n], configurable: true, writable: true });
    vi.restoreAllMocks();
  });

  it("makes zero calls through detect, solve, ladder, attempt, leak, guard and pushback", () => {
    for (const text of INPUTS) {
      guardText(text);
      const d = detectMath(text);
      if (d.kind !== "candidate") continue;
      guardCandidate(d.candidate);
      const s = solve(d.candidate);
      const ladder = buildLadder(d.candidate, s);
      const answers = answerSetFor(d.candidate, s);
      for (const lv of ladder.levels) hintLeaks(lv.text, lv.level, answers);
      checkAnswer(d.candidate, s, "x = 2");
      checkStep(d.candidate, d.candidate.display, "x = 2");
      routesToPracticeHelp(d.candidate, ["Solve 2x + 3 = 7."]);
      const pb = detectPushback("that's wrong, my book says 3");
      finalReply(resolvePushback(d.candidate, s, pb.claim), "x = 9", answers);
    }
    expect(calls).toEqual([]);
  });

  it("the trap works (a fetch would be seen)", () => {
    expect(() => (globalThis as unknown as { fetch: () => void }).fetch()).toThrow();
    expect(calls).toContain("fetch");
  });
});
