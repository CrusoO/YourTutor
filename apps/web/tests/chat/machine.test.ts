import { describe, expect, it } from "vitest";
import {
  initialState,
  nextStep,
  reduce,
  stepOptions,
  tapsToIdentity,
  type ChatState,
  type ContextLike,
} from "@/lib/chat/machine";

// A registry shaped like GET /context/options: three boards with Maths for one class, twelve known classes.
const registry: ContextLike = {
  grades: Array.from({ length: 12 }, (_, i) => i + 1),
  curricula: ["board_a", "board_b", "board_c"].map((id) => ({
    id,
    titles: {},
    grades: [{ grade: 9, subjects: [{ id: "math", books: [{ id: `${id}_9`, medium: null }] }] }],
  })),
};

const withStates: ContextLike = {
  ...registry,
  states: [
    { id: "state_x", titles: {} },
    { id: "state_y", titles: {} },
  ],
  curricula: [
    { ...registry.curricula[0]!, states: ["state_x"] },
    { ...registry.curricula[1]!, states: ["state_y"] },
  ],
};

const twoMedia: ContextLike = {
  curricula: [
    {
      id: "board_a",
      grades: [
        {
          grade: 10,
          subjects: [
            {
              id: "math",
              books: [
                { id: "a_en", medium: "med_one" },
                { id: "a_xx", medium: "med_two" },
              ],
            },
          ],
        },
      ],
    },
  ],
};

const run = (state: ChatState, ctx: ContextLike, ...steps: [string, string][]) =>
  steps.reduce(
    (s, [step, value]) => reduce(s, { type: "pick", step: step as never, value }, ctx),
    state,
  );

describe("the chat conversation state machine", () => {
  it("starts on the welcome phase with no role and no messages", () => {
    const s = initialState();
    expect([s.phase, s.role, s.messages.length]).toEqual(["welcome", null, 0]);
  });

  it("asks class, board, subject in order, then moves to identity", () => {
    let s = reduce(initialState(), { type: "start_setup", intent: "lesson" }, registry);
    expect([s.phase, s.messages.at(-1)?.key]).toEqual(["context", "ask_grade"]);
    s = run(s, registry, ["grade", "9"]);
    expect(s.messages.at(-1)?.key).toBe("ask_board");
    s = run(s, registry, ["board", "board_b"]);
    expect(s.messages.at(-1)?.key).toBe("ask_subject");
    s = run(s, registry, ["subject", "math"]);
    expect([s.phase, s.messages.at(-1)?.key]).toEqual(["identity", "identity_intro"]);
    expect(s.setup).toEqual({ grade: 9, board: "board_b", subject: "math" });
  });

  it("a class without live content is offered as coming soon and cannot be started", () => {
    const options = stepOptions(registry, {}, "grade");
    expect(options).toHaveLength(12);
    expect(options.find((o) => o.value === "9")?.available).toBe(true);
    expect(options.find((o) => o.value === "10")?.available).toBe(false);
    let s = reduce(initialState(), { type: "start_setup", intent: null }, registry);
    s = run(s, registry, ["grade", "10"]);
    expect(s.setup.grade).toBeUndefined();
    expect(s.messages.at(-1)?.key).toBe("ask_grade"); // still waiting for a real choice
  });

  it("ignores a choice for a step that is not being asked, and unknown values", () => {
    let s = reduce(initialState(), { type: "start_setup", intent: null }, registry);
    expect(run(s, registry, ["subject", "math"])).toEqual(s);
    expect(run(s, registry, ["grade", "banana"])).toEqual(s);
  });

  it("skips the state and medium questions when the registry has no real choice", () => {
    expect(nextStep(registry, { grade: 9, board: "board_a" })).toBe("subject");
    expect(stepOptions(registry, {}, "state")).toEqual([]);
  });

  it("asks for a state when the registry lists several, and narrows the boards by it", () => {
    let s = reduce(initialState(), { type: "start_setup", intent: null }, withStates);
    s = run(s, withStates, ["grade", "9"]);
    expect(s.messages.at(-1)?.key).toBe("ask_state");
    s = run(s, withStates, ["state", "state_y"]);
    expect(stepOptions(withStates, s.setup, "board").map((o) => o.value)).toEqual(["board_b"]);
  });

  it("asks for a medium only when a board has more than one", () => {
    let s = reduce(initialState(), { type: "start_setup", intent: null }, twoMedia);
    s = run(s, twoMedia, ["grade", "10"], ["board", "board_a"]);
    expect(s.messages.at(-1)?.key).toBe("ask_medium");
    s = run(s, twoMedia, ["medium", "med_two"], ["subject", "math"]);
    expect(s.phase).toBe("identity");
    expect(s.setup.medium).toBe("med_two");
  });

  it("changing an earlier answer clears the later ones", () => {
    let s = reduce(initialState(), { type: "start_setup", intent: null }, registry);
    s = run(s, registry, ["grade", "9"], ["board", "board_a"], ["subject", "math"]);
    s = run(s, registry, ["board", "board_c"]);
    expect(s.setup).toEqual({ grade: 9, board: "board_c" });
    expect(s.phase).toBe("context");
    expect(s.messages.at(-1)?.key).toBe("ask_subject");
  });

  it("identity views are chosen by the visitor and never skip ahead to home", () => {
    let s = reduce(initialState(), { type: "identity", view: "sign_in" }, registry);
    expect([s.phase, s.identity]).toEqual(["identity", "sign_in"]);
    s = reduce(s, { type: "signed_in", role: "student", name: "Mina" }, registry);
    expect([s.phase, s.role]).toEqual(["home", "student"]);
    expect(s.messages.at(-1)).toMatchObject({ key: "signed_in", data: { name: "Mina" } });
  });

  it("a guest start lands on the guest home", () => {
    const s = reduce(initialState(), { type: "guest_started" }, registry);
    expect([s.phase, s.role]).toEqual(["home", "guest"]);
  });

  it("restart returns to the welcome phase and forgets the choices", () => {
    let s = reduce(initialState(), { type: "start_setup", intent: "practice" }, registry);
    s = run(s, registry, ["grade", "9"]);
    s = reduce(s, { type: "restart" }, registry);
    expect([s.phase, s.setup, s.intent]).toEqual(["welcome", {}, null]);
  });

  it("is pure: it never changes the state it is given", () => {
    const frozen = Object.freeze(initialState());
    expect(() => reduce(frozen, { type: "start_setup", intent: null }, registry)).not.toThrow();
    expect(frozen.messages).toHaveLength(0);
  });

  it("messages hold choices and keys only, never free text", () => {
    let s = reduce(initialState(), { type: "start_setup", intent: "lesson" }, registry);
    s = run(s, registry, ["grade", "9"], ["board", "board_a"], ["subject", "math"]);
    for (const m of s.messages) {
      expect(Object.keys(m).sort()).toEqual(m.data ? ["data", "from", "id", "key"] : ["from", "id", "key"]);
      for (const v of Object.values(m.data ?? {})) expect(["string", "number", "undefined"]).toContain(typeof v);
    }
  });

  it("reaches the identity step in four taps, so a first activity needs five or fewer", () => {
    const taps = tapsToIdentity(registry, { grade: "9", state: undefined, board: undefined, medium: undefined, subject: undefined });
    expect(taps).toBe(4); // start card, class, board, subject; "just try it" is the fifth
    expect(taps + 1).toBeLessThanOrEqual(5);
  });
});
