import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
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
  const tap = (name: string | RegExp, n: number) => {
    for (let i = 0; i < n; i++) fireEvent.click(screen.getByRole("button", { name }));
  };

  it("one big Hop button in the direction the move needs, a quiet progress line, Check only after the last hop", async () => {
    const onLocked = vi.fn();
    render(<NumberLine start={3} delta={4} mode="predict" after="check" countOn reducedMotion narrate={false} onLocked={onLocked} />);
    expect(screen.getByTestId("nl-progress")).toHaveTextContent("Start on 3. Make 4 hops to the right.");
    expect(screen.getByRole("img", { name: "Now at three" })).toBeInTheDocument();
    // one main action, no direction choice, no Undo before a hop, no counter boxes
    expect(screen.getByRole("button", { name: /Hop right/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Hop left/ })).toBeNull();
    expect(screen.queryByRole("button", { name: "Undo" })).toBeNull();
    expect(screen.queryByTestId("nl-result")).toBeNull();
    expect(screen.queryByRole("button", { name: "Check" })).toBeNull();
    expect(screen.queryByRole("slider")).toBeNull();
    tap(/Hop right/, 3);
    expect(screen.getByTestId("nl-progress")).toHaveTextContent("Hop 3 of 4");
    expect(screen.getByRole("img", { name: "Now at six" })).toBeInTheDocument();
    expect(screen.getByTestId("nl-live")).toHaveTextContent("Now at six. Hop 3 of 4.");
    expect(screen.getByRole("button", { name: "Undo" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Check" })).toBeNull();
    tap(/Hop right/, 1);
    expect(screen.queryByRole("button", { name: /Hop right/ })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Check" }));
    await waitFor(() => expect(onLocked).toHaveBeenCalledWith(expect.objectContaining({ correct: true, guess: 7 })));
    expect(screen.getByTestId("nl-reason")).toHaveTextContent("Yes. 3 + 4 lands on 7.");
  });

  it("a subtraction offers Hop left", () => {
    render(<NumberLine start={3} delta={-4} mode="predict" after="check" countOn reducedMotion narrate={false} />);
    expect(screen.getByRole("button", { name: /Hop left/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Hop right/ })).toBeNull();
    expect(screen.getByTestId("nl-progress")).toHaveTextContent("Make 4 hops to the left.");
  });

  it("Undo takes back the last hop", () => {
    render(<NumberLine start={3} delta={4} mode="predict" after="check" countOn reducedMotion narrate={false} />);
    tap(/Hop right/, 2);
    fireEvent.click(screen.getByRole("button", { name: "Undo" }));
    expect(screen.getByTestId("nl-progress")).toHaveTextContent("Hop 1 of 4");
    fireEvent.click(screen.getByRole("button", { name: "Undo" }));
    expect(screen.getByTestId("nl-progress")).toHaveTextContent("Start on 3");
    expect(screen.queryByRole("button", { name: "Undo" })).toBeNull();
  });

  it("Hint is a quiet link that reveals one rung per ask and never the answer", () => {
    render(<NumberLine start={3} delta={4} mode="predict" after="check" countOn reducedMotion narrate={false} />);
    expect(screen.queryByTestId("nl-tell")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Hint" }));
    expect(screen.getByTestId("nl-tell")).toHaveTextContent(/Which way does this move go/);
    fireEvent.click(screen.getByRole("button", { name: "Another hint" }));
    expect(screen.getByTestId("nl-tell")).toHaveTextContent(/Count 4 hops to the right/);
    fireEvent.click(screen.getByRole("button", { name: "Another hint" }));
    expect(screen.getByTestId("nl-tell")).toHaveTextContent(/Press the hop button 4 times/);
    expect(screen.getByTestId("nl-tell").textContent).not.toMatch(/\b7\b/);
    expect(screen.queryByRole("button", { name: /hint/i })).toBeNull();
  });

  it("opens the first hint rung by itself after the idle time, and only that rung", () => {
    vi.useFakeTimers();
    render(<NumberLine start={3} delta={4} mode="predict" after="check" countOn reducedMotion narrate={false} idleHintMs={5000} />);
    act(() => void vi.advanceTimersByTime(4900));
    expect(screen.queryByTestId("nl-tell")).toBeNull();
    act(() => void vi.advanceTimersByTime(200));
    expect(screen.getByTestId("nl-tell")).toHaveTextContent(/Which way does this move go/);
    act(() => void vi.advanceTimersByTime(60000));
    expect(screen.getByTestId("nl-tell")).toHaveTextContent(/Which way does this move go/);
    vi.useRealTimers();
  });

  it("a hop restarts the idle clock", () => {
    vi.useFakeTimers();
    render(<NumberLine start={3} delta={4} mode="predict" after="check" countOn reducedMotion narrate={false} idleHintMs={5000} />);
    act(() => void vi.advanceTimersByTime(4000));
    fireEvent.click(screen.getByRole("button", { name: /Hop right/ }));
    act(() => void vi.advanceTimersByTime(4000));
    expect(screen.queryByTestId("nl-tell")).toBeNull();
    vi.useRealTimers();
  });
});
