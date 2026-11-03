import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { StepPicture, describePicture, drawable } from "@/components/chat/lesson/StepPicture";
import { WidgetBlock } from "@/components/chat/lesson/widgets";
import { runWidget, type AiPicture, type AiWidget } from "@/lib/lessons/ai-lesson";

afterEach(cleanup);

const coins = (n: number, out = 0) => ({ n, what: "coins", unknown: false, out });
const unknownX = { n: 0, what: "x", unknown: true, out: 0 };

const start: AiPicture = { kind: "balance", left: [unknownX, coins(4)], right: [coins(10)] };
const taken: AiPicture = { kind: "balance", left: [unknownX, coins(4, 4)], right: [coins(10, 4)] };

describe("StepPicture", () => {
  it("draws a level balance with the words for a screen reader", () => {
    render(<StepPicture picture={start} />);
    const svg = screen.getByTestId("step-picture");
    expect(svg).toHaveAttribute("data-kind", "balance");
    expect(svg).toHaveAccessibleName("A balance that stays level. On the left: x and 4 coins. On the right: 10 coins.");
  });

  it("says what is left once items are taken away from both sides", () => {
    expect(describePicture(taken)).toContain("On the left: x and 0 coins. On the right: 6 coins.");
  });

  it("draws pieces, groups and a number line", () => {
    const pictures: AiPicture[] = [
      { kind: "pieces", parts: 6, shaded: 3, what: "pizza" },
      { kind: "groups", groups: 3, each: 4, what: "apples" },
      { kind: "line", min: 0, max: 10, marks: [{ at: 4, label: "start" }], jump: { from: 4, to: 10 } },
    ];
    for (const picture of pictures) {
      render(<StepPicture picture={picture} />);
      expect(screen.getByTestId("step-picture")).toHaveAttribute("data-kind", picture.kind);
      cleanup();
    }
    expect(describePicture(pictures[1]!)).toBe("3 groups of 4 apples.");
  });

  it("draws nothing for a picture that does not make sense, so the step reads as words", () => {
    const bad = [
      null,
      undefined,
      { kind: "pieces", parts: 1, shaded: 0, what: "" },
      { kind: "pieces", parts: 6, shaded: 9, what: "" },
      { kind: "groups", groups: 0, each: 3, what: "" },
      { kind: "balance", left: [], right: [coins(1)] },
      { kind: "balance", left: [coins(99)], right: [coins(1)] },
      { kind: "line", min: 5, max: 5, marks: [], jump: null },
      { kind: "spiral" },
    ] as unknown as AiPicture[];
    for (const picture of bad) expect(drawable(picture)).toBe(false);
    render(<StepPicture picture={bad[2]} />);
    expect(screen.queryByTestId("step-picture")).toBeNull();
  });
});

describe("a step-through widget with pictures", () => {
  const widget: AiWidget = {
    kind: "widget",
    widget_kind: "step_through",
    controls: [],
    what_to_notice: "Both sides change together.",
    spec: {
      steps: [
        { label: "Start", description: "Write the equation x + 4 = 10.", picture: start },
        { label: "Take 4 from both sides", description: "Both pans lose 4 coins.", picture: taken },
        { label: "Read it off", description: "x is 6." },
      ],
    },
  };

  it("shows each step's picture and none for a step without one", async () => {
    const run = runWidget(widget)!;
    render(<WidgetBlock run={run} />);
    expect(screen.getByTestId("step-picture")).toHaveAccessibleName(describePicture(start));
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByTestId("step-picture")).toHaveAccessibleName(describePicture(taken));
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.queryByTestId("step-picture")).toBeNull();
  });
});
