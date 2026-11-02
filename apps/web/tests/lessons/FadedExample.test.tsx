import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import LessonPlayer from "@/components/lessons/LessonPlayer";
import type { Lesson } from "@/lib/lessons/types";

const FIXTURE = path.resolve(
  __dirname,
  "../../../../packages/shared/fixtures/lessons/valid_faded_example_lesson.json",
);
const lesson = JSON.parse(readFileSync(FIXTURE, "utf-8")).lesson as Lesson;
const FADED_AT = lesson.beats.findIndex((b) => b.kind === "faded_example");
const instant = () => Promise.resolve();

afterEach(cleanup);

function renderAtFaded(onFadedAnswer: (i: number, r: string) => Promise<boolean>) {
  render(
    <LessonPlayer
      lesson={lesson}
      locale="en"
      mode="session"
      startAt={FADED_AT}
      reducedMotion
      delay={instant}
      onFadedAnswer={onFadedAnswer}
    />,
  );
}

describe("faded example beat", () => {
  it("shows the worked steps and asks for the missing one", () => {
    renderAtFaded(vi.fn());
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("Now you finish it");
    expect(screen.getByText("Take 2 off both sides: 3x = 12.")).toBeInTheDocument();
    expect(screen.getByText("Split both sides by 3. What is x?")).toBeInTheDocument();
  });

  it("sends the typed answer to the server and shows success only on the server's yes", async () => {
    const onFadedAnswer = vi.fn().mockResolvedValue(true);
    renderAtFaded(onFadedAnswer);
    await userEvent.type(screen.getByRole("textbox"), "4");
    await userEvent.click(screen.getByRole("button", { name: /^Check$/ }));
    await waitFor(() => expect(onFadedAnswer).toHaveBeenCalledWith(0, "4"));
    expect(await screen.findByText("Yes, x = 4.")).toBeInTheDocument();
  });

  it("a wrong answer shows the hint, keeps the box, and lets the student try again", async () => {
    const onFadedAnswer = vi.fn().mockResolvedValueOnce(false).mockResolvedValueOnce(true);
    renderAtFaded(onFadedAnswer);
    await userEvent.type(screen.getByRole("textbox"), "7");
    await userEvent.click(screen.getByRole("button", { name: /^Check$/ }));
    expect(await screen.findByText("What is 12 split into 3 equal parts?")).toBeInTheDocument();
    expect(screen.queryByText("Yes, x = 4.")).not.toBeInTheDocument();
    await userEvent.clear(screen.getByRole("textbox"));
    await userEvent.type(screen.getByRole("textbox"), "4");
    await userEvent.click(screen.getByRole("button", { name: /^Check$/ }));
    expect(await screen.findByText("Yes, x = 4.")).toBeInTheDocument();
    expect(onFadedAnswer).toHaveBeenCalledTimes(2);
  });

  it("does not send an empty answer", async () => {
    const onFadedAnswer = vi.fn().mockResolvedValue(true);
    renderAtFaded(onFadedAnswer);
    expect(screen.getByRole("button", { name: /^Check$/ })).toBeDisabled();
    expect(onFadedAnswer).not.toHaveBeenCalled();
  });
});
