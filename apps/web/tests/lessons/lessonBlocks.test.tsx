import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LESSON } from "./aiLesson";

const explainChat = vi.fn();
vi.mock("@/lib/api", () => ({ explainChat: (...args: unknown[]) => explainChat(...args) }));

import { LessonBlocks } from "@/components/chat/lesson/LessonBlocks";
import { usableBlocks, type AiBlock } from "@/lib/lessons/ai-lesson";

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
    expect(screen.getByText(/Not what most people expect/)).toBeInTheDocument();
    expect(cont()).toBeEnabled();
  });

  it("offers to skip to the check only after a right prediction", async () => {
    render(<LessonBlocks blocks={blocks} prompt="q" language="en" />);
    await userEvent.click(cont());
    await userEvent.click(screen.getByRole("button", { name: "It rolls back" }));
    expect(screen.getByText(/Your guess matched/)).toBeInTheDocument();
    await userEvent.click(screen.getByTestId("lesson-skip"));
    expect(screen.getByTestId("block-check")).toBeInTheDocument();
  });

  it("does not offer the skip after a wrong prediction", async () => {
    render(<LessonBlocks blocks={blocks} prompt="q" language="en" />);
    await userEvent.click(cont());
    await userEvent.click(screen.getByRole("button", { name: "It appears on the other side" }));
    expect(screen.queryByTestId("lesson-skip")).toBeNull();
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
    await userEvent.click(screen.getByRole("button", { name: "Give me a hint" }));
    expect(screen.getByText(/Think about the wave inside the wall/)).toBeInTheDocument();
    expect(screen.queryByText(/The wave shrinks as it goes deeper/)).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "It falls quickly" }));
    expect(screen.getByText("That is right.")).toBeInTheDocument();
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
    expect(screen.getByText(/Here is the answer/)).toBeInTheDocument();
    expect(cont()).toBeEnabled();
  });

  async function toEnd() {
    render(<LessonBlocks blocks={blocks} prompt="quantum tunnelling" language="en" />);
    await userEvent.click(cont());
    await userEvent.click(screen.getByRole("button", { name: "It rolls back" }));
    await userEvent.click(screen.getByTestId("lesson-skip"));
    await userEvent.click(screen.getByRole("button", { name: "It falls quickly" }));
    await userEvent.click(cont());
    await userEvent.type(screen.getByLabelText("Write your answer"), "Nuclei tunnel");
    await userEvent.click(screen.getByRole("button", { name: "Show a model answer" }));
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
    expect(explainChat).toHaveBeenCalledWith("why does width matter?", "en", [{ role: "user", content: "quantum tunnelling" }]);

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
    expect(await screen.findByRole("alert")).toHaveTextContent("could not answer");
  });
});
