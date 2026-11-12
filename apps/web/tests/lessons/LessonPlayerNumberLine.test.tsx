import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import LessonPlayer from "@/components/lessons/LessonPlayer";
import type { Lesson } from "@/lib/lessons/types";

const FIXTURE = path.resolve(__dirname, "../../../../packages/shared/fixtures/lessons/valid_number_line_lesson.json");
const lesson = JSON.parse(readFileSync(FIXTURE, "utf-8")).lesson as Lesson;
const noDelay = () => Promise.resolve();
const MINUS = "−";

afterEach(cleanup);

const btn = (name: string | RegExp) => screen.getByRole("button", { name });
const slider = () => screen.findByRole("slider");

describe("LessonPlayer with number-line figures", () => {
  it("Guess step: the learner places the dot and the guess goes to the server as the matching choice", async () => {
    const onPredict = vi.fn().mockResolvedValue(undefined);
    render(<LessonPlayer lesson={lesson} locale="en" mode="session" reducedMotion delay={noDelay} onPredict={onPredict} />);
    const dot = await slider();
    expect(dot).toHaveAttribute("aria-valuenow", "-6");
    for (let i = 0; i < 15; i++) fireEvent.click(btn("+1 step"));
    await waitFor(() => expect(screen.getByRole("slider")).toHaveAttribute("aria-valuenow", "9"));
    await userEvent.click(btn(/^Continue$/));
    expect(onPredict).toHaveBeenCalledWith("9");
  });

  it("Guess step: tapping a choice moves the dot to it, and the choice buttons still work alone", async () => {
    const onPredict = vi.fn().mockResolvedValue(undefined);
    render(<LessonPlayer lesson={lesson} locale="en" mode="session" reducedMotion delay={noDelay} onPredict={onPredict} />);
    await slider();
    await userEvent.click(screen.getByRole("button", { name: `${MINUS}9` }));
    await waitFor(() => expect(screen.getByRole("slider")).toHaveAttribute("aria-valuenow", "-9"));
    await userEvent.click(btn(/^Continue$/));
    expect(onPredict).toHaveBeenCalledWith(`${MINUS}9`);
  });

  it("Watch step: shows the same figure again with the learner's guess against the answer", async () => {
    render(<LessonPlayer lesson={lesson} locale="en" mode="session" reducedMotion delay={noDelay} onPredict={vi.fn()} />);
    await slider();
    await userEvent.click(screen.getByRole("button", { name: "21" }));
    await userEvent.click(btn(/^Continue$/));
    await userEvent.click(await screen.findByRole("button", { name: "Jump to the answer" }));
    expect(screen.getByTestId("nl-reason")).toHaveTextContent("You picked 21");
    expect(screen.getByTestId("nl-reason")).toHaveTextContent("lands on 9");
  });

  it("Example step: predict first, then hops; the written steps stay below once the guess is in", async () => {
    render(<LessonPlayer lesson={lesson} locale="en" mode="preview" startAt={2} reducedMotion delay={noDelay} />);
    await slider();
    expect(screen.queryByText(/Start at .8\. Adding 5 moves/)).toBeNull();
    for (let i = 0; i < 5; i++) fireEvent.click(btn("+1 step"));
    fireEvent.click(btn("That is my guess"));
    fireEvent.click(await screen.findByRole("button", { name: "Jump to the answer" }));
    expect(screen.getByTestId("nl-result")).toHaveTextContent(`${MINUS}3`);
    expect(screen.getByText(/Adding 5 moves 5 steps to the right/)).toBeInTheDocument();
  });

  it("Example step: another example (a subtraction) flips the sign of the move", async () => {
    render(<LessonPlayer lesson={lesson} locale="en" mode="preview" startAt={2} reducedMotion delay={noDelay} />);
    await slider();
    const other = screen.getByRole("button", { name: `3 ${MINUS} 7` });
    await userEvent.click(other);
    expect(other).toHaveAttribute("aria-pressed", "true");
    await waitFor(() => expect(screen.getByTestId("nl-move")).toHaveTextContent(`${MINUS}7`));
    expect(screen.getByTestId("nl-start")).toHaveTextContent("3");
  });

  it("Finish it: a correct placement is checked at once and sent to the server as the typed answer", async () => {
    const onFadedAnswer = vi.fn().mockResolvedValue(true);
    render(
      <LessonPlayer lesson={lesson} locale="en" mode="session" startAt={3} reducedMotion delay={noDelay} onFadedAnswer={onFadedAnswer} />,
    );
    await slider();
    for (let i = 0; i < 4; i++) fireEvent.click(btn("+1 step"));
    fireEvent.click(btn("That is my guess"));
    expect(screen.getByTestId("nl-reason")).toHaveTextContent(`Yes. ${MINUS}9 + 4 lands on ${MINUS}5.`);
    await waitFor(() => expect(onFadedAnswer).toHaveBeenCalledWith(0, "-5"));
  });

  it("a lesson without a figure keeps today's screen (no number line, no slider)", async () => {
    const plain = JSON.parse(
      readFileSync(path.resolve(__dirname, "../../../../packages/shared/fixtures/lessons/valid_faded_example_lesson.json"), "utf-8"),
    ).lesson as Lesson;
    render(<LessonPlayer lesson={plain} locale="en" mode="preview" reducedMotion delay={noDelay} />);
    expect(screen.queryByTestId("number-line")).toBeNull();
    expect(screen.queryByRole("slider")).toBeNull();
  });
});
