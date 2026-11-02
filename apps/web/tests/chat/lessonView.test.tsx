import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const closeLesson = vi.fn();

vi.mock("@/components/chat/ChatProvider", () => ({
  useChatApi: () => ({ lesson: { id: 1, prompt: "what is quantum tunnelling?" }, closeLesson }),
}));

vi.mock("@/lib/api", () => ({
  explainQuestion: vi.fn(() => new Promise(() => {})),
  explainStory: vi.fn(() => new Promise(() => {})),
  createSourceVideoJob: vi.fn(),
  createStoryVideoJob: vi.fn(),
  getVideoJob: vi.fn(),
}));

import { LessonView } from "@/components/chat/LessonView";

beforeEach(() => closeLesson.mockClear());
afterEach(cleanup);

describe("LessonView leaving the lesson", () => {
  it("offers a new question at the top and at the end, and both return to the ask box", async () => {
    render(<LessonView />);
    const top = screen.getByTestId("lesson-new-top");
    const end = screen.getByTestId("lesson-new");
    expect(top).toHaveTextContent("New question");
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
