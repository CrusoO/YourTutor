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

  it("Guess step: no multiple-choice row beside the figure", async () => {
    render(<LessonPlayer lesson={lesson} locale="en" mode="session" reducedMotion delay={noDelay} onPredict={vi.fn()} />);
    await slider();
    expect(screen.queryByRole("button", { name: `${MINUS}9` })).toBeNull();
    expect(document.querySelector(".lp-choices")).toBeNull();
  });

  it("Watch step: shows the same figure again with the learner's guess against the answer", async () => {
    render(<LessonPlayer lesson={lesson} locale="en" mode="session" reducedMotion delay={noDelay} onPredict={vi.fn()} />);
    await slider();
    for (let i = 0; i < 6; i++) fireEvent.click(btn("+1 step"));
    await waitFor(() => expect(screen.getByRole("slider")).toHaveAttribute("aria-valuenow", "0"));
    await userEvent.click(btn(/^Continue$/));
    await userEvent.click(await screen.findByRole("button", { name: "Jump to the answer" }));
    expect(screen.getByTestId("nl-reason")).toHaveTextContent("You picked 0");
    expect(screen.getByTestId("nl-reason")).toHaveTextContent("lands on 9");
  });

  it("Example step: predict first, then hops; the written steps stay below once the guess is in", async () => {
    render(<LessonPlayer lesson={lesson} locale="en" mode="preview" startAt={2} reducedMotion delay={noDelay} />);
    await screen.findByTestId("number-line");
    expect(screen.queryByText(/Start at .8\. Adding 5 moves/)).toBeNull();
    for (let i = 0; i < 5; i++) fireEvent.click(btn("Hop right"));
    fireEvent.click(document.querySelector(".lp-primary") as HTMLElement);
    // the student made every hop themselves, so the finished line shows at once (no replay to sit through)
    await waitFor(() => expect(screen.getByTestId("nl-reason")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: "Jump to the answer" })).toBeNull();
    expect(screen.getByRole("img", { name: "Now at minus three" })).toBeInTheDocument();
    expect(screen.getByText(/Adding 5 moves 5 steps to the right/)).toBeInTheDocument();
  });

  it("Example step: ONE example at a time, no picker; Another one moves on to the subtraction", async () => {
    render(<LessonPlayer lesson={lesson} locale="en" mode="preview" startAt={2} reducedMotion delay={noDelay} />);
    await screen.findByTestId("number-line");
    expect(screen.queryByRole("button", { name: `3 ${MINUS} 7` })).toBeNull();
    expect(screen.queryByRole("group", { name: "Try another" })).toBeNull();
    expect(screen.getByTestId("example-count")).toHaveTextContent("Example 1 of 2");
    expect(document.querySelector(".lp-primary")).toHaveTextContent("Continue");
    for (let i = 0; i < 5; i++) fireEvent.click(btn("Hop right"));
    fireEvent.click(document.querySelector(".lp-primary") as HTMLElement); // Check
    await waitFor(() => expect(document.querySelector(".lp-primary")).toHaveTextContent("Another one"));
    fireEvent.click(document.querySelector(".lp-primary") as HTMLElement);
    await waitFor(() => expect(screen.getByTestId("example-count")).toHaveTextContent("Example 2 of 2"));
    expect(screen.getByRole("button", { name: "Hop left" })).toBeInTheDocument();
    expect(screen.getByTestId("nl-progress")).toHaveTextContent("Start on 3. Make 7 hops to the left.");
    expect(document.querySelector(".lp-primary")).toHaveAttribute("aria-disabled", "true");
  });

  it("Example step: the sign note shows once, at the first example that needs it; the link is always there", async () => {
    render(<LessonPlayer lesson={lesson} locale="en" mode="preview" startAt={2} reducedMotion delay={noDelay} />);
    await screen.findByTestId("number-line");
    // the lesson's Guess step (start below zero) already used the "below zero" note, so Example 1 has none
    expect(screen.queryByTestId("sign-note")).toBeNull();
    for (let i = 0; i < 5; i++) fireEvent.click(btn("Hop right"));
    fireEvent.click(document.querySelector(".lp-primary") as HTMLElement);
    await waitFor(() => expect(document.querySelector(".lp-primary")).toHaveTextContent("Another one"));
    fireEvent.click(document.querySelector(".lp-primary") as HTMLElement);
    await waitFor(() => expect(screen.getByTestId("sign-note")).toHaveTextContent("A minus sign moves you left."));
    expect(screen.queryByText(/Add \(\+\): move right/)).toBeNull(); // no permanent chips
    const link = screen.getByRole("button", { name: "What do + and \u2212 mean?" });
    expect(link).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(link);
    expect(screen.getByText("Plus (+) moves right.")).toBeInTheDocument();
    expect(screen.getByText("Minus (\u2212) moves left.")).toBeInTheDocument();
    expect(screen.getByText("Adding a negative number moves left too.")).toBeInTheDocument();
    expect(link).toHaveAttribute("aria-expanded", "true");
  });

  it("Example step: the lesson's own wording is kept for the first example", async () => {
    render(<LessonPlayer lesson={lesson} locale="en" mode="preview" startAt={2} reducedMotion delay={noDelay} />);
    await screen.findByTestId("number-line");
    expect(screen.getByText("Work out -8 + 5.")).toBeInTheDocument();
  });

  it("Finish it: a correct placement is checked at once and sent to the server as the typed answer", async () => {
    const onFadedAnswer = vi.fn().mockResolvedValue(true);
    render(
      <LessonPlayer lesson={lesson} locale="en" mode="session" startAt={3} reducedMotion delay={noDelay} onFadedAnswer={onFadedAnswer} />,
    );
    await slider();
    for (let i = 0; i < 4; i++) fireEvent.click(btn("+1 step"));
    expect(document.querySelector(".lp-primary")).toHaveTextContent("Check");
    fireEvent.click(document.querySelector(".lp-primary") as HTMLElement);
    expect(screen.getByTestId("nl-reason")).toHaveTextContent(`Yes. ${MINUS}9 + 4 lands on ${MINUS}5.`);
    await waitFor(() => expect(onFadedAnswer).toHaveBeenCalledWith(0, "-5"));
  });

  it("Finish it: a wrong placement names the way back; Hint opens one rung per ask, never the answer; typing is a small link", async () => {
    const onFadedAnswer = vi.fn().mockResolvedValue(false);
    render(
      <LessonPlayer lesson={lesson} locale="en" mode="session" startAt={3} reducedMotion delay={noDelay} onFadedAnswer={onFadedAnswer} />,
    );
    await slider();
    expect(screen.queryByRole("textbox")).toBeNull();
    for (let i = 0; i < 3; i++) fireEvent.click(btn("+1 step"));
    fireEvent.click(document.querySelector(".lp-primary") as HTMLElement);
    await waitFor(() => expect(onFadedAnswer).toHaveBeenCalledWith(0, "-6"));
    await waitFor(() => expect(document.querySelector(".lp-why")).toHaveTextContent("Try again: move the dot, then press Check."));
    expect(document.querySelector(".lp-primary")).toHaveAttribute("aria-disabled", "true");
    expect(screen.queryByTestId("faded-hint")).toBeNull();
    fireEvent.click(btn("Hint"));
    expect(screen.getByTestId("faded-hint")).toHaveTextContent(/Which way does this move go/);
    fireEvent.click(btn("Another hint"));
    expect(screen.getByTestId("faded-hint")).toHaveTextContent(/Count 4 hops to the right/);
    expect(screen.getByTestId("faded-hint").textContent).not.toMatch(/5/);
    fireEvent.click(btn("Type the answer instead"));
    expect(screen.getByRole("textbox")).toBeInTheDocument();
    expect(btn("Use the number line")).toBeInTheDocument();
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
