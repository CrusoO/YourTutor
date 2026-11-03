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

describe("LessonView content", () => {
  it("shows the interactive lesson, labels it as an AI draft, and does not ask for the written page", async () => {
    vi.mocked(api.explainLesson).mockResolvedValue(LESSON);
    render(<LessonView />);
    expect(await screen.findByTestId("lesson-blocks")).toBeInTheDocument();
    expect(screen.getByTestId("block-hook")).toBeInTheDocument();
    expect(screen.getByTestId("lesson-draft-note")).toHaveTextContent("An AI wrote this");
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
