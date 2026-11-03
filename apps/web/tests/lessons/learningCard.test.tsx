import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LESSON } from "./aiLesson";

vi.mock("@/lib/api", () => ({ explainChat: vi.fn() }));

import { LessonBlocks } from "@/components/chat/lesson/LessonBlocks";
import { usableBlocks } from "@/lib/lessons/ai-lesson";
import { loadSaved } from "@/lib/lessons/learning-map";

const blocks = usableBlocks(LESSON)!;
const cont = () => screen.getByTestId("lesson-continue");

beforeEach(() => window.localStorage.clear());
afterEach(cleanup);

type Plan = { predict: string; predictSure?: boolean; check: string; checkSure?: boolean };

/** Walk the lesson: answer the prediction and the check as planned, skipping the rest, to the end card. */
async function walk(plan: Plan) {
  render(
    <LessonBlocks blocks={blocks} prompt="what is quantum tunnelling?" language="en" footer={<span data-testid="footer">end</span>} />,
  );
  expect(screen.queryByTestId("footer")).toBeNull(); // nothing to leave by while the lesson is under way
  await userEvent.click(cont()); // hook -> predict
  if (plan.predictSure !== undefined) await userEvent.click(screen.getByTestId(plan.predictSure ? "confidence-sure" : "confidence-unsure"));
  await userEvent.click(screen.getByRole("button", { name: plan.predict }));
  await userEvent.click(cont()); // -> widget
  await userEvent.click(cont()); // -> explain
  await userEvent.click(cont()); // -> check
  if (plan.checkSure !== undefined) await userEvent.click(screen.getByTestId(plan.checkSure ? "confidence-sure" : "confidence-unsure"));
  await userEvent.click(screen.getByRole("button", { name: plan.check }));
  if (plan.check !== "It falls quickly") {
    await userEvent.click(screen.getByRole("button", { name: "It falls quickly" })); // work it out, as a student would
  }
  await userEvent.click(cont()); // -> transfer
  await userEvent.type(screen.getByLabelText("Type your answer"), "x");
  await userEvent.click(screen.getByRole("button", { name: "See a sample answer" }));
  await userEvent.click(cont()); // -> recap
}

describe("confidence and the idea behind a wrong answer, inside the lesson", () => {
  it("offers the tap before a prediction is made, and not after", async () => {
    render(<LessonBlocks blocks={blocks} prompt="q" language="en" />);
    await userEvent.click(cont());
    expect(screen.getByTestId("confidence")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "It rolls back" }));
    expect(screen.queryByTestId("confidence")).toBeNull();
  });

  it("names the idea behind a wrong prediction, and says so when the learner was sure", async () => {
    render(<LessonBlocks blocks={blocks} prompt="q" language="en" />);
    await userEvent.click(cont());
    await userEvent.click(screen.getByTestId("confidence-sure"));
    await userEvent.click(screen.getByRole("button", { name: "It appears on the other side" }));
    const note = screen.getByRole("status");
    expect(note).toHaveTextContent("The idea behind that: thinks a ball can pass through the hill");
    expect(note).toHaveTextContent("You were sure, so this one is worth fixing.");
  });

  it("does not say the learner was sure when they were not, or when they were right", async () => {
    render(<LessonBlocks blocks={blocks} prompt="q" language="en" />);
    await userEvent.click(cont());
    await userEvent.click(screen.getByTestId("confidence-unsure"));
    await userEvent.click(screen.getByRole("button", { name: "It appears on the other side" }));
    expect(screen.getByRole("status")).not.toHaveTextContent("You were sure");
    cleanup();

    render(<LessonBlocks blocks={blocks} prompt="q" language="en" />);
    await userEvent.click(cont());
    await userEvent.click(screen.getByTestId("confidence-sure"));
    await userEvent.click(screen.getByRole("button", { name: "It rolls back" }));
    expect(screen.getByRole("status")).not.toHaveTextContent("worth fixing");
    expect(screen.getByRole("status")).not.toHaveTextContent("The idea behind that");
  });

  it("names the idea behind a wrong check answer, and only blames confidence on the first try", async () => {
    render(<LessonBlocks blocks={blocks} prompt="q" language="en" />);
    await userEvent.click(cont());
    await userEvent.click(screen.getByRole("button", { name: "It rolls back" }));
    await userEvent.click(screen.getByTestId("lesson-skip"));
    await userEvent.click(screen.getByTestId("confidence-sure"));
    await userEvent.click(screen.getByRole("button", { name: "It rises" }));
    expect(screen.getByText(/thinks a thicker barrier helps/)).toBeInTheDocument();
    expect(screen.getByText(/You were sure, so this one is worth fixing/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "It stays the same" }));
    expect(screen.getByText(/thinks width does not matter/)).toBeInTheDocument();
    expect(screen.queryByText(/You were sure, so this one is worth fixing/)).toBeNull();
  });
});

describe("the end-of-lesson card", () => {
  it("lists each judged answer by its first try, says how the learner read themselves, and keeps it on the device", async () => {
    await walk({ predict: "It rolls back", predictSure: true, check: "It falls quickly", checkSure: true });
    expect(screen.getByTestId("footer")).toBeInTheDocument(); // the way out appears at the very end
    const card = screen.getByTestId("learning-card");
    const rows = within(card).getAllByTestId("learning-row");
    expect(rows.map((r) => r.getAttribute("data-state"))).toEqual(["right", "right"]);
    expect(within(card).getByTestId("calibration")).toHaveTextContent("When you were sure, you were right");
    expect(within(card).queryByTestId("retest")).toBeNull();
    const saved = loadSaved();
    expect(saved).toHaveLength(1);
    expect(saved[0]!.topic).toBe("what is quantum tunnelling?");
    expect(saved[0]!.items.map((i) => i.right)).toEqual([true, true]);
  });

  it("counts a check by its first pick even when the learner then works it out", async () => {
    await walk({ predict: "It rolls back", check: "It rises" });
    const rows = within(screen.getByTestId("learning-card")).getAllByTestId("learning-row");
    expect(rows.map((r) => r.getAttribute("data-state"))).toEqual(["right", "shaky"]);
    expect(rows[1]).toHaveTextContent("thinks a thicker barrier helps");
  });

  it("marks a sure-but-wrong answer, says how many, and offers it again with the options in a new order", async () => {
    await walk({ predict: "It rolls back", check: "It rises", checkSure: true });
    const card = screen.getByTestId("learning-card");
    expect(within(card).getAllByTestId("learning-row")[1]).toHaveAttribute("data-state", "sure-wrong");
    expect(within(card).getByTestId("calibration")).toHaveTextContent("You were sure about 1 that turned out wrong");
    const retest = within(card).getByTestId("retest");
    const buttons = within(retest).getAllByRole("button").map((b) => b.textContent);
    expect(buttons).not.toEqual(["It rises", "It falls quickly", "It stays the same", "It becomes certain"]);
    expect([...buttons].sort()).toEqual(["It becomes certain", "It falls quickly", "It rises", "It stays the same"]);
  });

  it("tells the learner whether the second go was right", async () => {
    await walk({ predict: "It rolls back", check: "It rises", checkSure: true });
    const retest = within(screen.getByTestId("learning-card")).getByTestId("retest");
    await userEvent.click(within(retest).getByRole("button", { name: "It falls quickly" }));
    expect(within(retest).getByText("Now you've got it.")).toBeInTheDocument();
    expect(within(retest).getAllByRole("button").every((b) => (b as HTMLButtonElement).disabled)).toBe(true);
    cleanup();
    window.localStorage.clear();

    await walk({ predict: "It rolls back", check: "It rises", checkSure: true });
    const again = within(screen.getByTestId("learning-card")).getByTestId("retest");
    await userEvent.click(within(again).getByRole("button", { name: "It stays the same" }));
    expect(within(again).getByText(/Still not it/)).toBeInTheDocument();
  });

  it("clears the record from the device on request", async () => {
    await walk({ predict: "It rolls back", check: "It falls quickly" });
    expect(loadSaved()).toHaveLength(1);
    await userEvent.click(screen.getByTestId("learning-clear"));
    expect(loadSaved()).toEqual([]);
    expect(screen.getByText("Cleared from this device.")).toBeInTheDocument();
    expect(screen.queryByTestId("learning-clear")).toBeNull();
  });

  it("shows nothing and saves nothing when no answer was judged", () => {
    const noAnswers = blocks.filter((b) => b.block.kind === "hook" || b.block.kind === "explain" || b.block.kind === "recap");
    render(<LessonBlocks blocks={noAnswers} prompt="q" language="en" />);
    expect(screen.queryByTestId("learning-card")).toBeNull();
    expect(loadSaved()).toEqual([]);
  });
});
