import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Reveal } from "@/components/chat/lesson/Reveal";
import { revealedPrefix, useReveal, wordCount, WORD_MS } from "@/lib/chat/reveal";

function stubMotion(reduce: boolean) {
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    value: (query: string) => ({ matches: reduce && query.includes("reduce"), addEventListener() {}, removeEventListener() {} }),
  });
}

beforeEach(() => vi.useFakeTimers());
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  // @ts-expect-error put the jsdom default (no matchMedia) back
  delete window.matchMedia;
});

describe("revealedPrefix", () => {
  it("returns the first n words with their original spacing", () => {
    expect(revealedPrefix("You have the direction right.", 3)).toBe("You have the");
    expect(revealedPrefix("one  two\nthree", 2)).toBe("one  two");
  });
  it("handles none, all and more than all", () => {
    expect(revealedPrefix("a b c", 0)).toBe("");
    expect(revealedPrefix("a b c", 3)).toBe("a b c");
    expect(revealedPrefix("a b c", 99)).toBe("a b c");
    expect(revealedPrefix("", 3)).toBe("");
  });
  it("keeps Hindi words whole", () => {
    expect(revealedPrefix("यह पहला वाक्य है।", 2)).toBe("यह पहला");
  });
  it("counts words", () => {
    expect(wordCount("  a  b\nc ")).toBe(3);
    expect(wordCount("")).toBe(0);
  });
});

function Probe({ text, animate }: { text: string; animate: boolean }) {
  const { shown, done } = useReveal(text, animate);
  return <p data-testid="p" data-done={String(done)}>{shown}</p>;
}

describe("useReveal", () => {
  it("shows the words one at a time and then stops", () => {
    stubMotion(false);
    render(<Probe text="one two three" animate />);
    expect(screen.getByTestId("p")).toHaveTextContent("");
    act(() => void vi.advanceTimersByTime(WORD_MS));
    expect(screen.getByTestId("p")).toHaveTextContent("one");
    act(() => void vi.advanceTimersByTime(WORD_MS));
    expect(screen.getByTestId("p").textContent).toBe("one two");
    act(() => void vi.advanceTimersByTime(WORD_MS * 5));
    expect(screen.getByTestId("p").textContent).toBe("one two three");
    expect(screen.getByTestId("p").dataset.done).toBe("true");
  });

  it("shows everything at once for someone who asks for reduced motion", () => {
    stubMotion(true);
    render(<Probe text="one two three" animate />);
    expect(screen.getByTestId("p").textContent).toBe("one two three");
    expect(screen.getByTestId("p").dataset.done).toBe("true");
  });

  it("shows everything at once when it is not asked to animate", () => {
    stubMotion(false);
    render(<Probe text="one two three" animate={false} />);
    expect(screen.getByTestId("p").textContent).toBe("one two three");
  });

  it("starts over when the text changes", () => {
    stubMotion(false);
    const { rerender } = render(<Probe text="one two" animate />);
    act(() => void vi.advanceTimersByTime(WORD_MS * 3));
    rerender(<Probe text="alpha beta gamma" animate />);
    expect(screen.getByTestId("p").textContent).toBe("");
    act(() => void vi.advanceTimersByTime(WORD_MS));
    expect(screen.getByTestId("p").textContent).toBe("alpha");
  });

  it("stops its timer when it is removed", () => {
    stubMotion(false);
    const { unmount } = render(<Probe text="one two three" animate />);
    unmount();
    expect(vi.getTimerCount()).toBe(0);
  });
});

describe("Reveal", () => {
  it("gives a screen reader the whole reply once while it appears, then plain text", () => {
    stubMotion(false);
    const { container } = render(<Reveal text="Think about the units." />);
    expect(container.querySelector(".sr-only")?.textContent).toBe("Think about the units.");
    expect(container.querySelector("[aria-hidden='true']")?.textContent).toBe("");
    act(() => void vi.advanceTimersByTime(WORD_MS * 10));
    expect(container.querySelector(".sr-only")).toBeNull();
    expect(container.textContent).toBe("Think about the units.");
  });
});
