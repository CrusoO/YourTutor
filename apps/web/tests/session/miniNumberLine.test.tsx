import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { SESSION_CSS } from "@/components/session/sessionStyles";
import MiniNumberLine, { labelledTicks, lineDescription, lineWindow } from "@/components/session/MiniNumberLine";
import { SignExplanation, SignHint } from "@/components/session/SignExplain";
import ProgressHeader, { FeedbackBlock } from "@/components/session/Progress";
import { parseIntegerStem } from "@/lib/session/integer-stem";
import { t } from "@/lib/messages";
import { withSession } from "@/lib/session/copy";

const copy = withSession(t("en"));
afterEach(cleanup);

describe("window", () => {
  it("always includes 0 and the start with one tick of padding", () => {
    expect(lineWindow(10, -7)).toEqual({ min: -1, max: 18 });
    expect(lineWindow(-3, 5)).toEqual({ min: -9, max: 3 });
    const w = lineWindow(4, 2);
    expect(w.min).toBe(-1);
    expect(w.max).toBe(7);
  });
  it("is symmetric about the start so it does not leak the direction", () => {
    expect(lineWindow(10, -7)).toEqual(lineWindow(10, 7));
  });
  it("labels 0 and the start even on a wide line, and never crowds labels", () => {
    const { min, max } = lineWindow(300, -250);
    const labels = labelledTicks(min, max, [0, 300]);
    expect(labels).toContain(0);
    expect(labels).toContain(300);
    expect(labels.length).toBeLessThan(20);
  });
});

describe("MiniNumberLine", () => {
  it("shows the landing in the explanation", () => {
    render(<MiniNumberLine copy={copy} start={10} delta={-7} showLanding />);
    const svg = screen.getByRole("img");
    expect(svg.getAttribute("aria-label")).toContain("Start at 10.");
    expect(svg.getAttribute("aria-label")).toContain("Move 7 steps left.");
    expect(svg.getAttribute("aria-label")).toContain("You land on 3.");
    expect(screen.getByTestId("mini-number-line")).toHaveAttribute("data-landing", "shown");
    expect(svg.querySelector(".mnl-land")).not.toBeNull();
    expect(svg.querySelector(".mnl-zero")).not.toBeNull();
  });
  it("hides the landing for the hint", () => {
    render(<MiniNumberLine copy={copy} start={10} delta={-7} showLanding={false} />);
    const svg = screen.getByRole("img");
    expect(svg.getAttribute("aria-label")).not.toMatch(/land/i);
    expect(svg.querySelector(".mnl-land")).toBeNull();
    expect(screen.getByTestId("mini-number-line")).toHaveAttribute("data-landing", "hidden");
    expect(screen.getByTestId("mini-number-line").textContent).not.toMatch(/you land here/);
  });
  it("uses a real minus sign and the singular step", () => {
    expect(lineDescription(copy, -2, 1, true)).toContain("Start at −2.");
    expect(lineDescription(copy, -2, 1, true)).toContain("Move 1 step right.");
  });
});

describe("panels", () => {
  const parse = parseIntegerStem("Compute 10 + (-7).")!;
  it("the explanation shows rule, line and three steps", () => {
    render(<SignExplanation copy={copy} parse={parse} />);
    expect(screen.getByText("What does the sign mean?")).toBeInTheDocument();
    expect(screen.getByText(/Adding a negative number moves you left/)).toBeInTheDocument();
    expect(screen.getByText("You land on 3.")).toBeInTheDocument();
  });
  it("the hint is closed first, then shows the line without the result", async () => {
    render(<SignHint copy={copy} parse={parse} />);
    expect(screen.queryByTestId("sign-hint-body")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Show me on a number line" }));
    const body = screen.getByTestId("sign-hint-body");
    expect(body.textContent).not.toMatch(/land/i);
    expect(body.querySelector("p.muted")?.textContent).not.toMatch(/\b3\b/);
    expect(screen.getByTestId("mini-number-line")).toHaveAttribute("data-landing", "hidden");
    expect(screen.getByRole("button", { name: "Hide the number line" })).toHaveAttribute("aria-expanded", "true");
  });
});

describe("progress and feedback", () => {
  it("counts questions without a percentage", () => {
    render(<ProgressHeader copy={copy} done={2} />);
    expect(screen.getByTestId("progress-count")).toHaveTextContent("Question 3");
    expect(screen.getByTestId("progress").textContent).not.toMatch(/%/);
  });
  it("caps the dots", () => {
    const { container } = render(<ProgressHeader copy={copy} done={40} />);
    expect(container.querySelectorAll(".prog-dot").length).toBe(11);
  });
  it("feedback has an icon and words for both outcomes", () => {
    const { container, rerender } = render(<FeedbackBlock copy={copy} correct />);
    expect(screen.getByTestId("feedback")).toHaveTextContent("Nice, that is right.");
    expect(container.querySelector("svg")).not.toBeNull();
    rerender(<FeedbackBlock copy={copy} correct={false} />);
    expect(screen.getByTestId("feedback")).toHaveTextContent("Not quite. Let's try a hint.");
    expect(container.querySelector("svg")).not.toBeNull();
  });
});

describe("a11y of the new styles", () => {
  const block = SESSION_CSS;
  it("uses tokens only (no hard-coded colours except neutral shadows)", () => {
    expect(block.match(/#[0-9a-fA-F]{3,8}\b/g) ?? []).toEqual([]);
    const colours = block.match(/rgba?\([^)]*\)/g) ?? [];
    expect(colours.every((c) => /^rgba\((15, 23, 42|0, 0, 0),/.test(c))).toBe(true);
  });
  it("turns the entrance motion off for reduced motion", () => {
    expect(block).toMatch(/prefers-reduced-motion: no-preference/);
    expect(block).toMatch(/:not\(\[data-motion="reduce"\]\)/);
  });
  it("keeps 44 px targets and a visible focus ring", () => {
    expect(block).toMatch(/min-height: var\(--s-control-min\)/);
    expect(block).toMatch(/focus-visible/);
  });
});
