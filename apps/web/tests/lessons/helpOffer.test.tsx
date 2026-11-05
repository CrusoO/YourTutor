import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({ explainChat: vi.fn() }));

import { LessonBlocks } from "@/components/chat/lesson/LessonBlocks";
import type { AiCheck, UsableBlock } from "@/lib/lessons/ai-lesson";

afterEach(cleanup);

const check = (n: number, ideas: (string | null)[] = [null, "same slip", "same slip", "same slip"]): UsableBlock => ({
  block: {
    kind: "check",
    question: `Question ${n}?`,
    options: ["right one", "wrong A", "wrong B", "wrong C"],
    correct: 0,
    feedback_per_option: ["Yes.", "No A.", "No B.", "No C."],
    hint_ladder: ["a hint"],
    misconceptions: ideas,
  } satisfies AiCheck,
});
const lesson = [check(1), check(2), check(3)];
const wrong = async (which: string) => userEvent.click(screen.getAllByRole("button", { name: which }).at(-1)!); // the newest block is the last on the page
const render3 = (offer?: { ready: boolean; onWatch: () => void }) => render(<LessonBlocks blocks={lesson} prompt="a question" language="en" offer={offer} />);

describe("Brownie offers the video after the learner slips more than once", () => {
  it("says nothing after one wrong answer", async () => {
    render3({ ready: true, onWatch: vi.fn() });
    await wrong("wrong A");
    expect(screen.queryByTestId("help-offer")).toBeNull();
  });

  it("after the second wrong answer, says the video is ready and offers to watch it or carry on", async () => {
    const onWatch = vi.fn();
    render3({ ready: true, onWatch });
    await wrong("wrong A");
    await wrong("wrong B");
    const card = screen.getByTestId("help-offer");
    expect(card).toHaveTextContent("twice");
    expect(card).toHaveTextContent("same slip"); // both slips were the same idea, so Brownie says so
    expect(card).toHaveTextContent("Your video on this is ready");
    await userEvent.click(screen.getByRole("button", { name: "Watch the video" }));
    expect(onWatch).toHaveBeenCalledTimes(1);
    expect(screen.queryByTestId("help-offer")).toBeNull();
  });

  it("Keep going closes it, and it stays closed on the third wrong answer", async () => {
    render3({ ready: true, onWatch: vi.fn() });
    await wrong("wrong A");
    await wrong("wrong B");
    await userEvent.click(screen.getByRole("button", { name: "Keep going with the questions" }));
    expect(screen.queryByTestId("help-offer")).toBeNull();
    await wrong("wrong C"); // third wrong answer on the same question (the answer is then shown)
    expect(screen.queryByTestId("help-offer")).toBeNull();
  });

  it("asks once more if the learner keeps slipping (the fourth wrong answer), not before", async () => {
    render3({ ready: true, onWatch: vi.fn() });
    await wrong("wrong A");
    await wrong("wrong B");
    await userEvent.click(screen.getByRole("button", { name: "Keep going with the questions" }));
    await wrong("wrong C");
    await userEvent.click(screen.getByTestId("lesson-continue"));
    await wrong("wrong A"); // fourth wrong answer overall
    expect(screen.getByTestId("help-offer")).toHaveTextContent("4 times");
  });

  it("does not claim the video is ready when it is still being made, and offers no watch button", async () => {
    render3({ ready: false, onWatch: vi.fn() });
    await wrong("wrong A");
    await wrong("wrong B");
    const card = screen.getByTestId("help-offer");
    expect(card).toHaveTextContent("still putting your video together");
    expect(card).not.toHaveTextContent("is ready");
    expect(screen.queryByRole("button", { name: "Watch the video" })).toBeNull();
  });

  it("does not name an idea when the two slips were different", async () => {
    render(<LessonBlocks blocks={[check(1, [null, "idea one", "idea two", null])]} prompt="q" language="en" offer={{ ready: true, onWatch: vi.fn() }} />);
    await wrong("wrong A");
    await wrong("wrong B");
    expect(screen.getByTestId("help-offer")).not.toHaveTextContent("idea one");
  });

  it("without an offer prop, nothing changes", async () => {
    render3(undefined);
    await wrong("wrong A");
    await wrong("wrong B");
    expect(screen.queryByTestId("help-offer")).toBeNull();
  });
});
