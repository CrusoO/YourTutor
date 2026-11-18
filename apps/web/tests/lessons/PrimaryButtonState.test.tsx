import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import LessonPlayer from "@/components/lessons/LessonPlayer";
import { labelledTicks } from "@/lib/lessons/numberline";
import type { Lesson } from "@/lib/lessons/types";

const FIXTURE = path.resolve(__dirname, "../../../../packages/shared/fixtures/lessons/valid_number_line_lesson.json");
const lesson = JSON.parse(readFileSync(FIXTURE, "utf-8")).lesson as Lesson;
const noDelay = () => Promise.resolve();
afterEach(cleanup);

const primary = () => document.querySelector(".lp-primary") as HTMLButtonElement;

describe("the sticky primary button never silently does nothing", () => {
  it("Example step: switched off with a reason before the dot is placed", async () => {
    render(<LessonPlayer lesson={lesson} locale="en" mode="preview" startAt={2} reducedMotion delay={noDelay} />);
    await screen.findByTestId("number-line");
    expect(primary()).toHaveAttribute("aria-disabled", "true");
    expect(primary()).toHaveAccessibleDescription(/Count the hops first/);
    expect(screen.getByTestId("primary-why")).toHaveAttribute("role", "status");
    fireEvent.click(primary());
    expect(screen.getByTestId("primary-why")).toHaveClass("nudge");
    expect(screen.getByRole("heading", { level: 2 })).toBeInTheDocument();
  });

  it("Example step: Check appears only when every hop is counted, then Continue after the check", async () => {
    render(<LessonPlayer lesson={lesson} locale="en" mode="preview" startAt={2} reducedMotion delay={noDelay} />);
    await screen.findByTestId("number-line");
    for (let i = 0; i < 4; i++) fireEvent.click(screen.getByRole("button", { name: "Up 1 →" }));
    expect(primary()).toHaveAttribute("aria-disabled", "true");
    fireEvent.click(screen.getByRole("button", { name: "Up 1 →" }));
    await waitFor(() => expect(primary()).toHaveTextContent("Check"));
    expect(primary()).not.toHaveAttribute("aria-disabled");
    fireEvent.click(primary());
    await waitFor(() => expect(primary()).toHaveTextContent("Continue"));
    expect(screen.getByTestId("number-line")).toHaveAttribute("data-phase", "hops");
  });

  it("Finish it: same rule, and a locked guess lets the learner continue", async () => {
    const onFadedAnswer = vi.fn().mockResolvedValue(true);
    render(<LessonPlayer lesson={lesson} locale="en" mode="session" startAt={3} reducedMotion delay={noDelay} onFadedAnswer={onFadedAnswer} />);
    await screen.findByRole("slider");
    expect(primary()).toHaveAttribute("aria-disabled", "true");
    fireEvent.click(screen.getByRole("button", { name: "+1 step" }));
    await waitFor(() => expect(primary()).toHaveTextContent("That is my guess"));
    fireEvent.click(primary());
    await waitFor(() => expect(primary()).toHaveTextContent("Continue"));
  });

  it("Guess step: needs an answer first", async () => {
    render(<LessonPlayer lesson={lesson} locale="en" mode="session" reducedMotion delay={noDelay} onPredict={vi.fn()} />);
    await screen.findByRole("slider");
    expect(primary()).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByTestId("primary-why")).toHaveTextContent(/Pick an answer/);
  });

  it("keeps the content clear of the fixed bar", async () => {
    render(<LessonPlayer lesson={lesson} locale="en" mode="preview" reducedMotion delay={noDelay} />);
    const root = screen.getByTestId("lesson-player");
    expect(root.style.getPropertyValue("--lp-bar-h")).toMatch(/^\d+px$/);
    const css = readFileSync(path.resolve(__dirname, "../../app/globals.css"), "utf-8");
    expect(css).toMatch(/\.lp \{[^}]*padding: 0 var\(--pad-x\) calc\(var\(--lp-bar-h, 96px\)/);
  });
});

describe("labelledTicks", () => {
  it("never labels two neighbours that would touch (dot at -9 next to -10)", () => {
    const set = labelledTicks(-10, 10, 15, -9, 2);
    expect(set.has(-9)).toBe(true);
    expect(set.has(-10)).toBe(false);
    expect(set.has(0)).toBe(true);
  });
  it("keeps every label when there is room", () => {
    const set = labelledTicks(-3, 3, 40, 1, 1);
    expect([...set].sort((a, b) => a - b)).toEqual([-3, -2, -1, 0, 1, 2, 3]);
  });
  it("labels never overlap on a crowded 360px-wide line", () => {
    const min = -20;
    const max = 20;
    const unit = 300 / (max - min);
    const set = [...labelledTicks(min, max, unit, 13, 5)].sort((a, b) => a - b);
    for (let i = 1; i < set.length; i++) expect((set[i] - set[i - 1]) * unit).toBeGreaterThanOrEqual(18);
  });
});
