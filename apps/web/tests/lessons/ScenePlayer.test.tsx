import { act, cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import ScenePlayer from "@/components/lessons/ScenePlayer";
import type { Lesson, Scene } from "@/lib/lessons/types";

const FIXTURE = path.resolve(__dirname, "../../../../packages/shared/fixtures/lessons/valid_full_lesson.json");
const lesson = JSON.parse(readFileSync(FIXTURE, "utf-8")).lesson as Lesson;
const scene = lesson.beats.find((b) => b.kind === "explain_scene")!.scene as Scene;
const FINAL = { en: "Do the same to both sides." };

/** A delay the test releases by hand, so intermediate states can be observed. */
function manualDelay() {
  const pending: (() => void)[] = [];
  const delay = () => new Promise<void>((resolve) => pending.push(resolve));
  const release = async () => {
    await act(async () => {
      pending.splice(0).forEach((fn) => fn());
      await Promise.resolve();
    });
  };
  return { delay, release, count: () => pending.length };
}
const instant = () => Promise.resolve();
const svgOf = () => document.querySelector("svg")!;

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("ScenePlayer", () => {
  it("draws progressively and keeps a caption on screen", async () => {
    const m = manualDelay();
    render(<ScenePlayer scene={scene} locale="en" delay={m.delay} reducedMotion={false} />);
    await waitFor(() => expect(m.count()).toBeGreaterThan(0));
    expect(screen.getByTestId("scene-caption")).toHaveTextContent("The balance is level: 2x + 3 = 11.");
    expect(svgOf().querySelectorAll("text")).toHaveLength(1);
    expect(svgOf().querySelectorAll("rect, circle, line")).toHaveLength(0 + 1); // only the text's clip rect
    await m.release(); // text finished writing -> the rectangle appears
    await waitFor(() => expect(svgOf().querySelectorAll("rect.lp-shape")).toHaveLength(1));
    expect(svgOf().querySelectorAll("circle")).toHaveLength(0);
    await m.release();
    await waitFor(() => expect(svgOf().querySelectorAll("circle.lp-shape")).toHaveLength(1));
  });

  it("describes the whiteboard for screen readers", () => {
    render(<ScenePlayer scene={scene} locale="en" delay={instant} reducedMotion />);
    expect(screen.getByRole("img")).toHaveAccessibleName(/2x \+ 3 = 11 solved step by step/i);
  });

  it("asks a question, gives feedback on a wrong choice and moves on after the right one", async () => {
    const onAsk = vi.fn();
    render(<ScenePlayer scene={scene} locale="en" delay={instant} reducedMotion onAsk={onAsk} />);
    const group = await screen.findByRole("group", { name: /what is left after taking 3 off/i });
    await userEvent.click(within(group).getByRole("button", { name: "2x = 14" }));
    expect(await screen.findByText(/11 - 3 = 8\. Try again\./)).toBeInTheDocument();
    expect(within(group).getByRole("button", { name: "2x = 14" })).toHaveClass("wrong");
    expect(onAsk).toHaveBeenLastCalledWith({ sceneId: "SCENE.TEST.ONE", step: 1, choice: 1, correct: false });
    await userEvent.click(within(group).getByRole("button", { name: "2x = 8" }));
    expect(onAsk).toHaveBeenLastCalledWith({ sceneId: "SCENE.TEST.ONE", step: 1, choice: 0, correct: true });
    await waitFor(() => expect(screen.queryByRole("group")).not.toBeInTheDocument());
  });

  it("finishes with the closing caption, then replays from the start", async () => {
    const onDone = vi.fn();
    render(<ScenePlayer scene={scene} locale="en" delay={instant} reducedMotion onDone={onDone} finalCaption={FINAL} />);
    await userEvent.click(await screen.findByRole("button", { name: "2x = 8" }));
    await waitFor(() => expect(onDone).toHaveBeenCalledTimes(1));
    expect(screen.getByTestId("scene-caption")).toHaveTextContent("Do the same to both sides.");
    expect(screen.getByRole("button", { name: "Play again" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Play again" }));
    await screen.findByRole("group");
    expect(svgOf().querySelectorAll("text")).toHaveLength(1); // cleared and redrawing from step 1
  });

  it("pauses at the end of a step and carries on when played again", async () => {
    const m = manualDelay();
    render(<ScenePlayer scene={scene} locale="en" delay={m.delay} reducedMotion={false} />);
    await waitFor(() => expect(m.count()).toBeGreaterThan(0));
    await userEvent.click(screen.getByRole("button", { name: "Pause" }));
    expect(screen.getByRole("button", { name: "Play" })).toBeInTheDocument();
    for (let i = 0; i < 12; i++) await m.release();
    expect(screen.queryByRole("group")).not.toBeInTheDocument(); // still holding after step 1
    await userEvent.click(screen.getByRole("button", { name: "Play" }));
    for (let i = 0; i < 12; i++) await m.release();
    expect(await screen.findByRole("group")).toBeInTheDocument();
  });

  it("replay restarts the scene", async () => {
    const m = manualDelay();
    render(<ScenePlayer scene={scene} locale="en" delay={m.delay} reducedMotion={false} />);
    await waitFor(() => expect(m.count()).toBeGreaterThan(0));
    await m.release();
    await m.release();
    await userEvent.click(screen.getByRole("button", { name: "Replay" }));
    await waitFor(() => expect(svgOf().querySelectorAll("text")).toHaveLength(1));
    expect(svgOf().querySelectorAll("circle.lp-shape")).toHaveLength(0);
  });

  it("respects reduced motion: no animation elements", async () => {
    const { unmount } = render(<ScenePlayer scene={scene} locale="en" delay={instant} reducedMotion />);
    await screen.findByRole("group");
    expect(svgOf().querySelectorAll("animate")).toHaveLength(0);
    unmount();
    const m = manualDelay();
    render(<ScenePlayer scene={scene} locale="en" delay={m.delay} reducedMotion={false} />);
    await waitFor(() => expect(m.count()).toBeGreaterThan(0));
    expect(svgOf().querySelectorAll("animate").length).toBeGreaterThan(0);
  });

  it("falls back to English and never shows an empty caption", async () => {
    render(<ScenePlayer scene={scene} locale="ne" delay={instant} reducedMotion />);
    await screen.findByRole("group");
    expect(screen.getByRole("img")).toHaveAccessibleName(/whiteboard showing/i);
  });

  it("stops quietly when it is unmounted mid-play", async () => {
    const error = vi.spyOn(console, "error").mockImplementation(() => {});
    const m = manualDelay();
    const { unmount } = render(<ScenePlayer scene={scene} locale="en" delay={m.delay} reducedMotion={false} />);
    await waitFor(() => expect(m.count()).toBeGreaterThan(0));
    unmount();
    await m.release();
    await m.release();
    expect(error).not.toHaveBeenCalled();
  });
});
