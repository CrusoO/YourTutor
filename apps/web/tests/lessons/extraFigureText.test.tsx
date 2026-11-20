import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, describe, expect, it } from "vitest";
import LessonPlayer from "@/components/lessons/LessonPlayer";
import { validateLesson } from "@/lib/lessons/schema";
import type { Lesson } from "@/lib/lessons/types";

const FIXTURE = path.resolve(__dirname, "../../../../packages/shared/fixtures/lessons/valid_number_line_lesson.json");
const base = JSON.parse(readFileSync(FIXTURE, "utf-8")).lesson as Lesson;
const noDelay = () => Promise.resolve();

afterEach(cleanup);

function withExtras(extras: Record<string, unknown>[]): Lesson {
  const lesson = structuredClone(base);
  const worked = lesson.beats.find((b) => b.kind === "worked_example");
  if (worked?.kind === "worked_example") worked.more_number_lines = extras as never;
  return lesson;
}

async function toSecondExample(lesson: Lesson) {
  render(<LessonPlayer lesson={lesson} locale="en" mode="preview" startAt={2} reducedMotion delay={noDelay} />);
  await screen.findByTestId("number-line");
  for (let i = 0; i < 5; i++) fireEvent.click(screen.getByRole("button", { name: "Hop right" }));
  fireEvent.click(document.querySelector(".lp-primary") as HTMLElement);
  await waitFor(() => expect(document.querySelector(".lp-primary")).toHaveTextContent("Another one"));
  fireEvent.click(document.querySelector(".lp-primary") as HTMLElement);
  await waitFor(() => expect(screen.getByTestId("example-count")).toHaveTextContent("Example 2 of 2"));
}

const fig = (over: Record<string, unknown> = {}) => ({ kind: "number_line", start: -2, delta: -4, answer: -6, ...over });

describe("extra example figures with authored text", () => {
  it("shows the authored problem and note for the extra example", async () => {
    await toSecondExample(withExtras([fig({ problem: "Work out -2 + (-4).", note: "Adding a negative number moves you left." })]));
    expect(screen.getByText("Work out -2 + (-4).")).toBeInTheDocument();
    expect(screen.getByTestId("sign-note")).toHaveTextContent("Adding a negative number moves you left.");
  });

  it("falls back to the generated text and the generic note without the new keys", async () => {
    await toSecondExample(withExtras([{ kind: "number_line", start: 3, delta: -7, answer: -4 }]));
    expect(screen.getByText(/^Work out 3 .+ 7\.$/)).toBeInTheDocument();
    expect(screen.getByTestId("sign-note")).toHaveTextContent("A minus sign moves you left.");
  });
});

describe("lesson validator for extra figure text", () => {
  const ok = (extras: Record<string, unknown>[]) => validateLesson(withExtras(extras)).length === 0;
  it("accepts old and new figures", () => {
    expect(ok([fig()])).toBe(true);
    expect(ok([fig({ problem: "x".repeat(160), note: "y".repeat(200) })])).toBe(true);
  });
  it("rejects text that is too long or empty", () => {
    expect(ok([fig({ problem: "x".repeat(161) })])).toBe(false);
    expect(ok([fig({ note: "y".repeat(201) })])).toBe(false);
    expect(ok([fig({ problem: "" })])).toBe(false);
  });
  it("allows 8 extra figures and rejects 9", () => {
    expect(ok(Array.from({ length: 8 }, () => fig()))).toBe(true);
    expect(ok(Array.from({ length: 9 }, () => fig()))).toBe(false);
  });
});
