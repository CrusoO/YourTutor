import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LESSON } from "./aiLesson";

const explainChat = vi.fn();
vi.mock("@/lib/api", () => ({ explainChat: (...args: unknown[]) => explainChat(...args) }));

import { LessonBlocks } from "@/components/chat/lesson/LessonBlocks";
import { usableBlocks, usableOpening, usableRest, type AiBlock } from "@/lib/lessons/ai-lesson";

const blocks = usableBlocks(LESSON)!;
const cont = () => screen.getByTestId("lesson-continue");

beforeEach(() => explainChat.mockReset());
afterEach(cleanup);

describe("usableBlocks", () => {
  it("keeps a lesson whose widgets are safe", () => {
    expect(blocks).toHaveLength(7);
  });

  it("drops a widget whose formula does not parse or is not finite, and keeps the rest", () => {
    const withFormula = (formula: string): AiBlock => {
      const widget = LESSON.blocks[2] as Extract<AiBlock, { widget_kind: "slider_sim" }>;
      return { ...widget, spec: { ...widget.spec, formula } };
    };
    for (const bad of ["alert(1)", "constructor", "1 / (width - 2)", "width.length"]) {
      const lesson = { ...LESSON, blocks: LESSON.blocks.map((b, i) => (i === 2 ? withFormula(bad) : b)) };
      const kept = usableBlocks(lesson)!;
      expect(
        kept.some((b) => b.block.kind === "widget"),
        bad,
      ).toBe(false);
      expect(kept).toHaveLength(6);
    }
  });

  it("rejects a lesson with too little left to teach with", () => {
    expect(usableBlocks({ ...LESSON, blocks: LESSON.blocks.slice(0, 2) })).toBeNull();
  });
});

describe("LessonBlocks", () => {
  it("shows one block at a time and holds Continue until a guess is committed", async () => {
    render(<LessonBlocks blocks={blocks} prompt="quantum tunnelling" language="en" />);
    expect(screen.getByTestId("block-hook")).toBeInTheDocument();
    expect(screen.queryByTestId("block-predict")).toBeNull();
    await userEvent.click(cont());
    expect(screen.getByTestId("block-predict")).toBeInTheDocument();
    expect(cont()).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "It appears on the other side" }));
    expect(screen.getByText(/Lots of people guess that/)).toBeInTheDocument();
    expect(cont()).toBeEnabled();
  });

  it("offers to skip to the check only after a right prediction", async () => {
    render(<LessonBlocks blocks={blocks} prompt="q" language="en" />);
    await userEvent.click(cont());
    await userEvent.click(screen.getByRole("button", { name: "It rolls back" }));
    expect(screen.getByText(/Yep, you got it/)).toBeInTheDocument();
    await userEvent.click(screen.getByTestId("lesson-skip"));
    expect(screen.getByTestId("block-check")).toBeInTheDocument();
  });

  it("does not offer the skip after a wrong prediction", async () => {
    render(<LessonBlocks blocks={blocks} prompt="q" language="en" />);
    await userEvent.click(cont());
    await userEvent.click(screen.getByRole("button", { name: "It appears on the other side" }));
    expect(screen.queryByTestId("lesson-skip")).toBeNull();
  });

  it("does not offer the skip when a right prediction was marked not sure", async () => {
    render(<LessonBlocks blocks={blocks} prompt="q" language="en" />);
    await userEvent.click(cont());
    await userEvent.click(screen.getByRole("button", { name: "Not sure" }));
    await userEvent.click(screen.getByRole("button", { name: "It rolls back" }));
    expect(screen.getByText(/Yep, you got it/)).toBeInTheDocument();
    expect(screen.queryByTestId("lesson-skip")).toBeNull();
    expect(cont()).toBeEnabled();
  });

  it("moves the slider widget's output with the slider", async () => {
    render(<LessonBlocks blocks={blocks} prompt="q" language="en" />);
    await userEvent.click(cont());
    await userEvent.click(screen.getByRole("button", { name: "It rolls back" }));
    await userEvent.click(cont());
    const output = screen.getByTestId("widget-output");
    expect(output).toHaveTextContent("1");
    fireEvent.change(within(screen.getByTestId("widget-slider")).getAllByRole("slider")[0]!, { target: { value: "2" } });
    expect(output.textContent).toMatch(/0\.0183/);
  });

  it("gives feedback on a wrong check answer, reveals hints one at a time, and unlocks on the right answer", async () => {
    render(<LessonBlocks blocks={blocks} prompt="q" language="en" />);
    await userEvent.click(cont());
    await userEvent.click(screen.getByRole("button", { name: "It rolls back" }));
    await userEvent.click(screen.getByTestId("lesson-skip"));
    expect(cont()).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "It rises" }));
    expect(screen.getByText(/Thicker means less wave gets through/)).toBeInTheDocument();
    expect(cont()).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Help me" }));
    expect(screen.getByText(/Think about the wave inside the wall/)).toBeInTheDocument();
    expect(screen.queryByText(/The wave shrinks as it goes deeper/)).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "It falls quickly" }));
    expect(screen.getByText("Yes, exactly.")).toBeInTheDocument();
    expect(cont()).toBeEnabled();
  });

  it("reveals the answer after three wrong tries so nobody is stuck", async () => {
    render(<LessonBlocks blocks={blocks} prompt="q" language="en" />);
    await userEvent.click(cont());
    await userEvent.click(screen.getByRole("button", { name: "It rolls back" }));
    await userEvent.click(screen.getByTestId("lesson-skip"));
    for (const wrong of ["It rises", "It stays the same", "It becomes certain"]) {
      await userEvent.click(screen.getByRole("button", { name: wrong }));
    }
    expect(screen.getByText(/Here's the answer/)).toBeInTheDocument();
    expect(cont()).toBeEnabled();
  });

  async function toEnd() {
    render(<LessonBlocks blocks={blocks} prompt="quantum tunnelling" language="en" />);
    await userEvent.click(cont());
    await userEvent.click(screen.getByRole("button", { name: "It rolls back" }));
    await userEvent.click(screen.getByTestId("lesson-skip"));
    await userEvent.click(screen.getByRole("button", { name: "It falls quickly" }));
    await userEvent.click(cont());
    await userEvent.type(screen.getByLabelText("Type your answer"), "Nuclei tunnel");
    await userEvent.click(screen.getByRole("button", { name: "See a sample answer" }));
    await userEvent.click(cont());
  }

  it("ends on the recap and then offers follow-up questions", async () => {
    await toEnd();
    expect(screen.getByTestId("block-recap")).toBeInTheDocument();
    expect(screen.queryByTestId("lesson-continue")).toBeNull();
    expect(screen.getByTestId("ask-about")).toBeInTheDocument();
  });

  it("sends the topic and the last turns with each follow-up and shows the reply", async () => {
    explainChat.mockResolvedValueOnce({ kind: "reply", text: "What do you think shrinks inside the wall?" });
    await toEnd();
    await userEvent.type(screen.getByTestId("ask-about-input"), "why does width matter?");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));
    await waitFor(() => expect(screen.getByTestId("ask-about-tutor")).toHaveTextContent("What do you think shrinks"));
    expect(explainChat).toHaveBeenCalledWith(
      "why does width matter?",
      "en",
      [{ role: "user", content: "quantum tunnelling" }],
      expect.any(Function), // the reply is streamed
    );

    explainChat.mockResolvedValueOnce({ kind: "reply", text: "Right." });
    await userEvent.type(screen.getByTestId("ask-about-input"), "the wave?");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));
    await waitFor(() => expect(explainChat).toHaveBeenCalledTimes(2));
    expect(explainChat.mock.calls[1]![2]).toEqual([
      { role: "user", content: "quantum tunnelling" },
      { role: "user", content: "why does width matter?" },
      { role: "assistant", content: "What do you think shrinks inside the wall?" },
    ]);
  });

  it("says so when the tutor cannot answer", async () => {
    explainChat.mockRejectedValueOnce(new Error("down"));
    await toEnd();
    await userEvent.type(screen.getByTestId("ask-about-input"), "hello");
    await userEvent.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("I couldn't answer");
  });
});


describe("usableOpening and usableRest", () => {
  const [hook, predict, widget, explain, check, transfer, recap] = LESSON.blocks as [
    AiBlock, AiBlock, AiBlock, AiBlock, AiBlock, AiBlock, AiBlock,
  ];

  it("accepts exactly a hook then a prediction as an opening", () => {
    expect(usableOpening({ blocks: [hook, predict] })?.map((b) => b.block.kind)).toEqual(["hook", "predict"]);
    for (const blocks of [[hook], [predict, hook], [hook, predict, explain], [explain, check]]) {
      expect(usableOpening({ blocks })).toBeNull();
    }
  });

  it("accepts a rest of at least three drawable blocks that includes a check, and drops a second hook", () => {
    const usable = usableRest([hook, widget, explain, check, transfer, recap]);
    expect(usable?.map((b) => b.block.kind)).toEqual(["widget", "explain", "check", "transfer", "recap"]);
  });

  it("rejects a rest that is too short, has no check, or loses its widget and falls below three", () => {
    expect(usableRest([explain, check])).toBeNull();
    expect(usableRest([widget, explain, transfer, recap])).toBeNull();
    const broken = { ...(widget as Extract<AiBlock, { widget_kind: "slider_sim" }>) };
    broken.spec = { ...broken.spec, formula: "alert(1)" };
    expect(usableRest([broken, check, recap])).toBeNull(); // the widget is dropped, two are left
    expect(usableRest([broken, explain, check, recap])?.map((b) => b.block.kind)).toEqual(["explain", "check", "recap"]);
  });
});

describe("the not-checked label", () => {
  const withVerified = (verified: boolean | undefined) =>
    blocks.map((entry) => (entry.block.kind === "predict" ? { ...entry, block: { ...entry.block, verified } } : entry));

  it("says so on a quiz the maths verifier could not read, and only then", async () => {
    for (const [verified, shown] of [[false, true], [true, false], [undefined, false]] as const) {
      render(<LessonBlocks blocks={withVerified(verified)} prompt="q" language="en" />);
      await userEvent.click(cont());
      expect(screen.getByTestId("block-predict")).toBeInTheDocument();
      expect(screen.queryByTestId("not-checked") !== null, String(verified)).toBe(shown);
      cleanup();
    }
  });
});
