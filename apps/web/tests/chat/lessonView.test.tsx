import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LESSON } from "../lessons/aiLesson";

const closeLesson = vi.fn();

vi.mock("@/components/chat/ChatProvider", () => ({
  useChatApi: () => ({ lesson: { id: 1, prompt: "what is quantum tunnelling?" }, closeLesson }),
}));

vi.mock("@/lib/api", () => ({
  explainLesson: vi.fn(),
  explainLessonOpening: vi.fn(),
  explainLessonRest: vi.fn(),
  explainQuestion: vi.fn(),
  explainStory: vi.fn(),
  explainChat: vi.fn(),
  createSourceVideoJob: vi.fn(),
  createStoryVideoJob: vi.fn(),
  getVideoJob: vi.fn(),
}));

import { LessonView } from "@/components/chat/LessonView";
import * as api from "@/lib/api";

const never = () => new Promise<never>(() => {});

beforeEach(() => {
  closeLesson.mockClear();
  vi.mocked(api.explainLesson).mockImplementation(never);
  vi.mocked(api.explainLessonOpening).mockImplementation(never);
  vi.mocked(api.explainLessonRest).mockImplementation(never);
  vi.mocked(api.explainQuestion).mockImplementation(never);
  vi.mocked(api.explainStory).mockImplementation(never);
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("LessonView leaving the lesson", () => {
  it("offers a new question at the top and at the end, and both return to the ask box", async () => {
    render(<LessonView />);
    const top = screen.getByTestId("lesson-new-top");
    const end = screen.getByTestId("lesson-new");
    expect(top).toHaveTextContent("Try another question");
    expect(end).toHaveTextContent("Ask something else");
    await userEvent.click(top);
    await userEvent.click(end);
    expect(closeLesson).toHaveBeenCalledTimes(2);
  });

  it("moves focus to the question when the lesson opens", () => {
    render(<LessonView />);
    expect(screen.getByTestId("lesson-prompt")).toHaveFocus();
  });

  it("puts the cursor back in the ask box when the lesson is closed", async () => {
    const box = document.createElement("textarea");
    box.setAttribute("data-testid", "composer-input");
    document.body.append(box);
    render(<LessonView />);
    await userEvent.click(screen.getByTestId("lesson-new"));
    await new Promise((resolve) => requestAnimationFrame(() => resolve(null)));
    expect(box).toHaveFocus();
    box.remove();
  });
});

describe("LessonView content (the one-call path, when the fast opening is not available)", () => {
  beforeEach(() => {
    vi.mocked(api.explainLessonOpening).mockResolvedValue({ kind: "unavailable", reason: "checks" });
  });

  it("shows the interactive lesson, labels it as an AI draft, and does not ask for the written page", async () => {
    vi.mocked(api.explainLesson).mockResolvedValue(LESSON);
    render(<LessonView />);
    expect(await screen.findByTestId("lesson-blocks")).toBeInTheDocument();
    expect(screen.getByTestId("block-hook")).toBeInTheDocument();
    expect(screen.getByTestId("lesson-draft-note")).toHaveTextContent("Brownie is an AI and wrote this");
    expect(screen.getByTestId("lesson-video-card")).toBeInTheDocument();
    expect(api.explainQuestion).not.toHaveBeenCalled();
  });

  it("falls back to the written explanation when the lesson is not available", async () => {
    vi.mocked(api.explainLesson).mockResolvedValue({ kind: "unavailable", reason: "checks" });
    vi.mocked(api.explainQuestion).mockResolvedValue({
      kind: "explanation",
      title: "Quantum tunnelling",
      sections: [{ heading: "The idea in one line", body: "A particle can pass a barrier." }],
    });
    render(<LessonView />);
    expect(await screen.findByText("A particle can pass a barrier.")).toBeInTheDocument();
    expect(screen.queryByTestId("lesson-blocks")).toBeNull();
    expect(api.explainQuestion).toHaveBeenCalledTimes(1);
  });

  it("falls back when the lesson call itself fails", async () => {
    vi.mocked(api.explainLesson).mockRejectedValue(new Error("network"));
    vi.mocked(api.explainQuestion).mockResolvedValue({
      kind: "explanation",
      title: "T",
      sections: [{ heading: "H", body: "Body text." }],
    });
    render(<LessonView />);
    expect(await screen.findByText("Body text.")).toBeInTheDocument();
  });

  it("falls back when every widget is unusable and too little of the lesson is left", async () => {
    vi.mocked(api.explainLesson).mockResolvedValue({ ...LESSON, blocks: LESSON.blocks.slice(0, 2) });
    vi.mocked(api.explainQuestion).mockResolvedValue({ kind: "explanation", title: "T", sections: [{ heading: "H", body: "Fallback body." }] });
    render(<LessonView />);
    expect(await screen.findByText("Fallback body.")).toBeInTheDocument();
  });

  it("shows a refusal's message and neither asks for the written page nor starts a video", async () => {
    vi.mocked(api.explainLesson).mockResolvedValue({ kind: "refused", message: "I cannot help with that one." });
    render(<LessonView />);
    expect(await screen.findByText("I cannot help with that one.")).toBeInTheDocument();
    expect(api.explainQuestion).not.toHaveBeenCalled();
    expect(screen.queryByTestId("lesson-video")).toBeNull();
  });

  it("asks for the written page to make a video when the story fails but the lesson worked", async () => {
    vi.mocked(api.explainLesson).mockResolvedValue(LESSON);
    vi.mocked(api.explainStory).mockResolvedValue({ kind: "unavailable", reason: "checks" });
    vi.mocked(api.explainQuestion).mockResolvedValue({ kind: "unavailable", reason: "checks" });
    render(<LessonView />);
    await waitFor(() => expect(api.explainQuestion).toHaveBeenCalledTimes(1));
    expect(await screen.findByTestId("lesson-blocks")).toBeInTheDocument();
  });
});

describe("LessonView in two parts", () => {
  const opening = { kind: "opening" as const, level: "school", objectives: [], blocks: LESSON.blocks.slice(0, 2) };
  const rest = { kind: "rest" as const, blocks: LESSON.blocks.slice(2) };

  it("shows the opening at once, asks for the rest with it, and adds the rest when it arrives", async () => {
    let finish: (value: typeof rest) => void = () => {};
    vi.mocked(api.explainLessonOpening).mockResolvedValue(opening);
    vi.mocked(api.explainLessonRest).mockImplementation(() => new Promise((resolve) => (finish = resolve)));
    render(<LessonView />);

    expect(await screen.findByTestId("block-hook")).toBeInTheDocument();
    // mid-lesson the way out is the small link at the top, not a big button under Continue
    expect(screen.getByTestId("lesson-new-top")).toBeInTheDocument();
    expect(screen.queryByTestId("lesson-new")).toBeNull();
    expect(api.explainLesson).not.toHaveBeenCalled();
    expect(api.explainLessonRest).toHaveBeenCalledWith("what is quantum tunnelling?", "en", opening.blocks);

    await userEvent.click(screen.getByTestId("lesson-continue"));
    await userEvent.click(screen.getByRole("button", { name: "It rolls back" }));
    // the student has done what was asked and the rest is not here yet: wait, do not dead-end
    expect(await screen.findByTestId("lesson-preparing")).toHaveTextContent("Getting the next part ready");
    expect(screen.queryByTestId("lesson-continue")).toBeNull();
    expect(screen.queryByTestId("ask-about")).toBeNull();

    finish(rest);
    await userEvent.click(await screen.findByTestId("lesson-continue"));
    expect(screen.getByTestId("block-widget")).toBeInTheDocument();
    expect(screen.queryByTestId("lesson-preparing")).toBeNull();
  });

  it("keeps the opening and fills in with the written explanation when the rest cannot be built", async () => {
    vi.mocked(api.explainLessonOpening).mockResolvedValue(opening);
    vi.mocked(api.explainLessonRest).mockResolvedValue({ kind: "unavailable", reason: "checks" });
    vi.mocked(api.explainQuestion).mockResolvedValue({
      kind: "explanation",
      title: "T",
      sections: [{ heading: "H", body: "Written version." }],
    });
    render(<LessonView />);
    await screen.findByTestId("block-hook");
    await userEvent.click(screen.getByTestId("lesson-continue"));
    await userEvent.click(screen.getByRole("button", { name: "It rolls back" }));
    expect(await screen.findByTestId("lesson-rest-failed")).toBeInTheDocument();
    expect(await screen.findByText("Written version.")).toBeInTheDocument();
    expect(screen.getByTestId("block-hook")).toBeInTheDocument();
    expect(screen.getByTestId("ask-about")).toBeInTheDocument();
  });

  it("treats a rest with too little in it, or a request that throws, as a failure", async () => {
    for (const reply of [{ kind: "rest" as const, blocks: LESSON.blocks.slice(2, 4) }, "throw" as const]) {
      vi.clearAllMocks();
      vi.mocked(api.explainLessonOpening).mockResolvedValue(opening);
      vi.mocked(api.explainQuestion).mockImplementation(never);
      if (reply === "throw") vi.mocked(api.explainLessonRest).mockRejectedValue(new Error("network"));
      else vi.mocked(api.explainLessonRest).mockResolvedValue(reply);
      vi.mocked(api.explainLesson).mockImplementation(never);
      vi.mocked(api.explainStory).mockImplementation(never);
      render(<LessonView />);
      await screen.findByTestId("block-hook");
      await userEvent.click(screen.getByTestId("lesson-continue"));
      await userEvent.click(screen.getByRole("button", { name: "It rolls back" }));
      expect(await screen.findByTestId("lesson-rest-failed")).toBeInTheDocument();
      cleanup();
    }
  });

  it("falls back to the one-call lesson when the opening fails or throws or is the wrong shape", async () => {
    const wrongShape = { ...opening, blocks: LESSON.blocks.slice(1, 3) };
    for (const first of ["unavailable", "throw", "wrong"] as const) {
      vi.clearAllMocks();
      if (first === "unavailable") vi.mocked(api.explainLessonOpening).mockResolvedValue({ kind: "unavailable", reason: "checks" });
      else if (first === "throw") vi.mocked(api.explainLessonOpening).mockRejectedValue(new Error("network"));
      else vi.mocked(api.explainLessonOpening).mockResolvedValue(wrongShape);
      vi.mocked(api.explainLesson).mockResolvedValue(LESSON);
      vi.mocked(api.explainStory).mockImplementation(never);
      render(<LessonView />);
      expect(await screen.findByTestId("lesson-blocks")).toBeInTheDocument();
      expect(api.explainLesson).toHaveBeenCalledTimes(1);
      expect(api.explainLessonRest).not.toHaveBeenCalled();
      cleanup();
    }
  });

  it("shows a refusal from the opening and asks for nothing more", async () => {
    vi.mocked(api.explainLessonOpening).mockResolvedValue({ kind: "refused", message: "I cannot help with that one." });
    render(<LessonView />);
    expect(await screen.findByText("I cannot help with that one.")).toBeInTheDocument();
    expect(api.explainLesson).not.toHaveBeenCalled();
    expect(api.explainLessonRest).not.toHaveBeenCalled();
    expect(api.explainQuestion).not.toHaveBeenCalled();
  });
});
