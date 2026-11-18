import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import NumberLine from "@/components/lessons/NumberLine";
import { countComplete, countOnFeedback, countOnHint, countOnWindow, shouldCountOn } from "@/lib/lessons/numberline";

afterEach(cleanup);

describe("count-on pure functions", () => {
  it("window: start and end with one of room, zero always on the line", () => {
    expect(countOnWindow(3, 4)).toEqual({ min: 0, max: 8 });
    expect(countOnWindow(2, -5)).toEqual({ min: -4, max: 3 });
    expect(countOnWindow(-5, 2)).toEqual({ min: -6, max: 1 });
    expect(countOnWindow(4, -6)).toEqual({ min: -3, max: 5 });
    expect(countOnWindow(-6, 15)).toEqual({ min: -7, max: 10 });
  });
  it("complete exactly when the hops equal the move length", () => {
    expect(countComplete(3, 4)).toBe(false);
    expect(countComplete(4, 4)).toBe(true);
    expect(countComplete(6, -6)).toBe(true);
  });
  it("small moves are counted, big ones dragged", () => {
    expect(shouldCountOn(4)).toBe(true);
    expect(shouldCountOn(-9)).toBe(true);
    expect(shouldCountOn(15)).toBe(false);
  });
  it("wrong-count messages point at the mistake and never give the answer", () => {
    const wrongWay = countOnFeedback(3, 4, [-1, -1, -1, -1]);
    expect(wrongWay.kind).toBe("wrong_way");
    const mixed = countOnFeedback(3, 4, [1, 1, -1, 1]);
    expect(mixed.kind).toBe("mixed");
    for (const level of [1, 2, 3]) expect(countOnHint(3, 4, level)).not.toMatch(/\b7\b/);
    expect(wrongWay.message).not.toMatch(/\b7\b/);
  });
});

describe("count-on figure", () => {
  const tap = (name: string, n: number) => {
    for (let i = 0; i < n; i++) fireEvent.click(screen.getByRole("button", { name }));
  };

  it("dot waits on the start, only Up/Down and Hint show, Check only after the last hop", async () => {
    const onLocked = vi.fn();
    render(<NumberLine start={3} delta={4} mode="predict" after="check" countOn reducedMotion narrate={false} onLocked={onLocked} />);
    expect(screen.getByTestId("nl-result")).toHaveTextContent("3");
    expect(screen.getByTestId("nl-move")).toHaveTextContent("0 of 4");
    expect(screen.queryByRole("button", { name: "Check" })).toBeNull();
    expect(screen.queryByRole("button", { name: "+1 step" })).toBeNull();
    expect(screen.queryByRole("slider")).toBeNull();
    tap("Up 1 →", 3);
    expect(screen.getByTestId("nl-result")).toHaveTextContent("6");
    expect(screen.getByTestId("nl-live")).toHaveTextContent("Now at six. Hop 3 of 4.");
    expect(screen.queryByRole("button", { name: "Check" })).toBeNull();
    tap("Up 1 →", 1);
    fireEvent.click(screen.getByRole("button", { name: "Check" }));
    await waitFor(() => expect(onLocked).toHaveBeenCalledWith(expect.objectContaining({ correct: true, guess: 7 })));
    expect(screen.getByTestId("nl-reason")).toHaveTextContent("Yes. 3 + 4 lands on 7.");
  });

  it("a wrong count resets the dot to the start with a targeted message and a hint", async () => {
    const onLocked = vi.fn();
    render(<NumberLine start={3} delta={4} mode="predict" after="check" countOn reducedMotion narrate={false} onLocked={onLocked} />);
    tap("← Down 1", 3);
    tap("Up 1 →", 1);
    fireEvent.click(screen.getByRole("button", { name: "Check" }));
    expect(onLocked).not.toHaveBeenCalled();
    expect(screen.getByTestId("nl-result")).toHaveTextContent("3");
    expect(screen.getByTestId("nl-move")).toHaveTextContent("0 of 4");
    expect(screen.getByTestId("nl-tell")).toHaveTextContent(/wrong way/);
    expect(screen.getByTestId("nl-tell")).toHaveTextContent(/Which way/);
  });

  it("Start again and Hint work; the hint is a guided action by the third ask", () => {
    render(<NumberLine start={3} delta={4} mode="predict" after="check" countOn reducedMotion narrate={false} />);
    tap("Up 1 →", 2);
    fireEvent.click(screen.getByRole("button", { name: "Start again" }));
    expect(screen.getByTestId("nl-move")).toHaveTextContent("0 of 4");
    tap("Hint", 3);
    expect(screen.getByTestId("nl-tell")).toHaveTextContent(/Tap "Up 1" 4 times/);
  });
});
