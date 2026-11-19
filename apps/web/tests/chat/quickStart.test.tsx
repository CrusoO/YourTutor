import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SetupChips } from "@/components/chat/SetupChips";
import { initialState, nextStep, reduce, stepOptions, tapsToIdentity, type ChatState, type ContextLike } from "@/lib/chat/machine";
import { messageText } from "@/lib/chat/labels";
import { quickStartEnabled } from "@/lib/flags";
import { QUICK_START_DEFAULT_BOARD, quickBoard } from "@/lib/quick-start";
import { t } from "@/lib/messages";

const en = t("en");

// The default board teaches Class 9 and 10 Maths; a test board teaches Class 8 Science and must never be offered.
const registry: ContextLike = {
  grades: [6, 7, 8, 9, 10, 11, 12],
  states: [{ id: "state_x" }, { id: "state_y" }],
  curricula: [
    {
      id: QUICK_START_DEFAULT_BOARD,
      grades: [
        { grade: 9, subjects: [{ id: "math", books: [{ id: "d9", medium: "m1" }, { id: "d9b", medium: "m2" }] }] },
        { grade: 10, subjects: [{ id: "math", books: [{ id: "d10", medium: "m1" }] }, { id: "science", books: [{ id: "s10", medium: "m1" }] }] },
      ],
    },
    { id: "sample_board", grades: [{ grade: 8, subjects: [{ id: "sample_subject", books: [{ id: "x", medium: null }] }] }] },
  ],
};

const start = (quick: boolean) => reduce(initialState(), { type: "start_setup", intent: "lesson", quick }, registry);
const pick = (s: ChatState, step: "grade" | "subject", value: string) => reduce(s, { type: "pick", step, value }, registry);

describe("quick start flow machine", () => {
  it("asks only class, then subject, and never state, board or medium", () => {
    let s = start(true);
    expect(s.messages.at(-1)?.key).toBe("ask_grade");
    s = pick(s, "grade", "10");
    expect(s.messages.at(-1)?.key).toBe("ask_subject");
    expect(nextStep(registry, s.setup, true)).toBe("subject");
  });

  it("fills the board from the single internal default and then starts, with no identity question", () => {
    let s = start(true);
    s = pick(pick(s, "grade", "10"), "subject", "math");
    expect(s.setup).toMatchObject({ grade: 10, subject: "math", board: QUICK_START_DEFAULT_BOARD });
    expect(s.messages.at(-1)?.key).toBe("quick_start");
    expect(s.messages.some((m) => m.key === "identity_intro")).toBe(false);
  });

  it("offers only what the default board has, not test boards or other states", () => {
    expect(stepOptions(registry, {}, "grade", true).filter((o) => o.available).map((o) => o.value)).toEqual(["9", "10", "adult"]);
    expect(stepOptions(registry, { grade: 10 }, "subject", true).map((o) => o.value)).toEqual(["math", "science"]);
    expect(stepOptions(registry, { grade: 8 }, "subject", true)).toEqual([]);
  });

  it("falls back to the first board that has the class when the default is missing", () => {
    const noDefault: ContextLike = { curricula: [registry.curricula[1]!] };
    expect(quickBoard(noDefault, { grade: 8, subject: "sample_subject" })).toBe("sample_board");
  });

  it("takes two taps after the first card, three in all", () => {
    let s = start(true);
    let taps = 1;
    while (s.phase === "context") {
      const step = nextStep(registry, s.setup, true)!;
      s = reduce(s, { type: "pick", step, value: stepOptions(registry, s.setup, step, true).find((o) => o.available)!.value }, registry);
      taps += 1;
    }
    expect(taps).toBe(3);
  });

  it("falls back to the usual choices when the first question cannot start", () => {
    let s = pick(pick(start(true), "grade", "10"), "subject", "math");
    s = reduce(s, { type: "quick_failed" }, registry);
    expect(s.messages.at(-1)?.key).toBe("identity_intro");
  });

  it("keeps the old flow untouched when quick is off", () => {
    const s = start(false);
    expect(s.quick).toBe(false);
    expect(tapsToIdentity(registry, {} as never)).toBeGreaterThan(3);
    expect(nextStep(registry, { grade: 10 })).toBe("state");
  });
});

describe("the kill switch", () => {
  afterEach(() => vi.unstubAllEnvs());
  it("is on by default and off only for exactly false", () => {
    vi.stubEnv("NEXT_PUBLIC_QUICK_START_ENABLED", "");
    expect(quickStartEnabled()).toBe(true);
    vi.stubEnv("NEXT_PUBLIC_QUICK_START_ENABLED", "false");
    expect(quickStartEnabled()).toBe(false);
  });
});

let chat: ChatState;
const dispatch = vi.fn();
vi.mock("@/components/chat/ChatProvider", () => ({
  useChatApi: () => ({ chat, ctx: registry, copy: en, dispatch }),
}));

describe("SetupChips in quick start", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("shows class chips first, with no board or state words on screen", async () => {
    chat = start(true);
    render(<SetupChips />);
    expect(screen.getByTestId("setup-grade")).toHaveAccessibleName(en.chatAskGrade);
    expect(screen.queryByText(/board|sample/i)).toBeNull();
    // Classes without lessons are not shown as a wall of "coming soon" chips: one line says so.
    expect(screen.queryByTestId("choice-grade-6")).toBeNull();
    expect(screen.getByTestId("classes-soon")).toHaveTextContent(en.quickOtherClassesSoon);
    await userEvent.click(screen.getByTestId("choice-grade-10"));
    expect(dispatch).toHaveBeenCalledWith({ type: "pick", step: "grade", value: "10" });
  });

  it("shows only the default board's subjects after a class", () => {
    chat = pick(start(true), "grade", "10");
    render(<SetupChips />);
    expect(screen.getByTestId("setup-subject")).toBeInTheDocument();
    expect(screen.getByTestId("choice-subject-math")).toBeInTheDocument();
    expect(screen.queryByTestId("choice-subject-sample_subject")).toBeNull();
  });
});

/** Copy lint: nothing a student reads on the quick-start path may name a board or a publisher. */
describe("quick-start copy", () => {
  const keys = Object.keys(en).filter((k) => k.startsWith("quick")) as (keyof typeof en)[];
  const shown = [...keys.map((k) => en[k]), en.chatAskGrade, en.chatAskSubject, en.chatClassN, en.startTitle, en.chatSoon];

  it("has new keys", () => expect(keys.length).toBeGreaterThanOrEqual(6));
  it.each(shown)("does not name a board or publisher: %s", (text) => {
    expect(String(text)).not.toMatch(/cbse|ncert|icse|board|curriculum/i);
  });
  it("says nothing about a board in the started message either", () => {
    expect(messageText(en, registry, { id: 1, from: "tutor", key: "quick_start" }, "en")).not.toMatch(/cbse|ncert|board/i);
  });
});
