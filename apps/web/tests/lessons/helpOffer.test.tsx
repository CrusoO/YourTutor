import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({ explainChat: vi.fn() }));

import { LessonBlocks } from "@/components/chat/lesson/LessonBlocks";
import type { AiCheck, UsableBlock } from "@/lib/lessons/ai-lesson";

afterEach(cleanup);

const check = (n: number): UsableBlock => ({
  block: {
    kind: "check",
    question: `Question ${n}?`,
    options: ["right one", "wrong A", "wrong B", "wrong C"],
    correct: 0,
    feedback_per_option: ["Yes.", "No A.", "No B.", "No C."],
    hint_ladder: ["a hint"],
    misconceptions: [null, "a slip", "a slip", "a slip"],
  } satisfies AiCheck,
});
const lesson = [check(1), check(2)];
const click = async (name: string) => userEvent.click(screen.getAllByRole("button", { name }).at(-1)!); // the newest block is the last on the page
const render2 = (offer?: { ready: boolean; onWatch: (blockIndex: number) => void }) => render(<LessonBlocks blocks={lesson} prompt="a question" language="en" offer={offer} />);

describe("Brownie suggests the video right after a wrong guess", () => {
  it("shows nothing before any wrong guess, and nothing after a right one", async () => {
    render2({ ready: true, onWatch: vi.fn() });
    expect(screen.queryByTestId("video-suggest")).toBeNull();
    await click("right one");
    expect(screen.queryByTestId("video-suggest")).toBeNull();
  });

  it("after one wrong guess, asks if the learner wants to understand it better, and offers the video", async () => {
    const onWatch = vi.fn();
    render2({ ready: true, onWatch });
    await click("wrong A");
    const card = screen.getByTestId("video-suggest");
    expect(card).toHaveTextContent("Do you want to understand this better?");
    await userEvent.click(screen.getByRole("button", { name: "Watch the video" }));
    expect(onWatch).toHaveBeenCalledWith(0); // the first block, so the video can open at the right place
  });

  it("stays under the block that was wrong, and the next wrong block gets its own", async () => {
    const onWatch = vi.fn();
    render2({ ready: true, onWatch });
    await click("wrong A");
    await click("right one");
    await userEvent.click(screen.getByTestId("lesson-continue"));
    await click("wrong B");
    expect(screen.getAllByTestId("video-suggest")).toHaveLength(2);
    await userEvent.click(screen.getAllByRole("button", { name: "Watch the video" }).at(-1)!);
    expect(onWatch).toHaveBeenLastCalledWith(1);
  });

  it("does not say the video is ready when it is still being made, and offers no watch button", async () => {
    render2({ ready: false, onWatch: vi.fn() });
    await click("wrong A");
    const card = screen.getByTestId("video-suggest");
    expect(card).toHaveTextContent("still putting your video together");
    expect(screen.queryByRole("button", { name: "Watch the video" })).toBeNull();
  });

  it("without an offer prop, nothing changes", async () => {
    render2(undefined);
    await click("wrong A");
    expect(screen.queryByTestId("video-suggest")).toBeNull();
  });
});
