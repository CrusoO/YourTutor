import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import LessonPlayer from "@/components/lessons/LessonPlayer";
import type { Lesson } from "@/lib/lessons/types";

const FIXTURE = path.resolve(__dirname, "../../../../packages/shared/fixtures/lessons/valid_full_lesson.json");
const lesson = JSON.parse(readFileSync(FIXTURE, "utf-8")).lesson as Lesson;
const instant = () => Promise.resolve();

afterEach(cleanup);

const cont = () => screen.getByRole("button", { name: /^Continue$/ });
const pills = () => Array.from(document.querySelectorAll<HTMLButtonElement>(".lp-path button"));

describe("LessonPlayer", () => {
  it("starts on the predict beat and only unlocks later beats as they are reached", async () => {
    render(<LessonPlayer lesson={lesson} locale="en" mode="preview" reducedMotion delay={instant} />);
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("How heavy is one box?");
    expect(pills()[0]).not.toBeDisabled();
    expect(pills()[1]).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "4 kg" }));
    expect(screen.getByText("Hold on to that guess.")).toBeInTheDocument();
    await userEvent.click(cont());
    expect(pills()[1]).toHaveAttribute("aria-current", "step");
    expect(pills()[1]).not.toBeDisabled();
  });

  it("sends the guess once and completes through onComplete from the check beat", async () => {
    const onPredict = vi.fn().mockResolvedValue(undefined);
    const onComplete = vi.fn().mockResolvedValue(undefined);
    render(
      <LessonPlayer
        lesson={lesson}
        locale="en"
        mode="session"
        reducedMotion
        delay={instant}
        onPredict={onPredict}
        onComplete={onComplete}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "4 kg" }));
    await userEvent.click(cont());
    expect(onPredict).toHaveBeenCalledTimes(1);
    expect(onPredict).toHaveBeenCalledWith("4");
    for (let i = 0; i < 4; i++) {
      while (screen.queryByRole("button", { name: /^Next step$/ })) {
        await userEvent.click(screen.getByRole("button", { name: /^Next step$/ }));
      }
      await userEvent.click(cont());
    }
    expect(onPredict).toHaveBeenCalledTimes(1);
    expect(onComplete).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Start practice" }));
    await waitFor(() => expect(onComplete).toHaveBeenCalledTimes(1));
  });

  it("shows the source chips on the scene and worked-example beats only", () => {
    const sources = [{ id: "NOTE.X", title: "A note (authored)" }];
    const { unmount } = render(
      <LessonPlayer lesson={lesson} locale="en" mode="preview" reducedMotion delay={instant} sources={sources} />,
    );
    expect(screen.queryByText("A note (authored)")).not.toBeInTheDocument(); // predict beat
    unmount();
    const worked = lesson.beats.findIndex((b) => b.kind === "worked_example");
    render(
      <LessonPlayer lesson={lesson} locale="en" mode="preview" startAt={worked} reducedMotion delay={instant} sources={sources} />,
    );
    expect(screen.getByText("A note (authored)")).toBeInTheDocument();
  });

  it("has no practice button in preview mode", () => {
    render(<LessonPlayer lesson={lesson} locale="en" mode="preview" startAt={5} reducedMotion delay={instant} />);
    expect(screen.queryByRole("button", { name: "Start practice" })).not.toBeInTheDocument();
    expect(screen.getByText(/first practice item/)).toBeInTheDocument();
  });

  it("reports a solved widget and shows the server verdict", async () => {
    const onWidgetResult = vi.fn().mockResolvedValue(true);
    render(
      <LessonPlayer lesson={lesson} locale="en" mode="session" startAt={4} reducedMotion delay={instant} onWidgetResult={onWidgetResult} />,
    );
    fireEvent.change(screen.getByRole("slider"), { target: { value: "4" } });
    await waitFor(() => expect(onWidgetResult).toHaveBeenCalledTimes(1));
    expect(onWidgetResult.mock.calls[0][0]).toMatchObject({ final_state: { x: 4 } });
    expect(await screen.findByText(/Checked by the server/)).toBeInTheDocument();
  });

  it("tells the student when the server rejects the result", async () => {
    const onWidgetResult = vi.fn().mockResolvedValue(false);
    render(
      <LessonPlayer lesson={lesson} locale="en" mode="session" startAt={4} reducedMotion delay={instant} onWidgetResult={onWidgetResult} />,
    );
    fireEvent.change(screen.getByRole("slider"), { target: { value: "4" } });
    expect(await screen.findByText(/could not verify that/i)).toBeInTheDocument();
  });

  it("treats a failed request like a rejection", async () => {
    const onWidgetResult = vi.fn().mockRejectedValue(new Error("offline"));
    render(
      <LessonPlayer lesson={lesson} locale="en" mode="session" startAt={4} reducedMotion delay={instant} onWidgetResult={onWidgetResult} />,
    );
    fireEvent.change(screen.getByRole("slider"), { target: { value: "4" } });
    expect(await screen.findByText(/could not verify that/i)).toBeInTheDocument();
  });
});
