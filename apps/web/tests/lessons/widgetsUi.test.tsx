import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import BalanceScale from "@/components/lessons/BalanceScale";
import FunctionGraph from "@/components/lessons/FunctionGraph";
import type { BalanceScaleWidget, FunctionGraphWidget } from "@/lib/lessons/types";

const DIR = path.resolve(__dirname, "../../../../packages/shared/fixtures/widgets");
const balance = JSON.parse(readFileSync(path.join(DIR, "balance_scale.json"), "utf-8")).widget as BalanceScaleWidget;
const graph = JSON.parse(readFileSync(path.join(DIR, "function_graph.json"), "utf-8")).widget as FunctionGraphWidget;

afterEach(cleanup);

const left = () => screen.getAllByRole("button", { name: "Take one weight off the left" });
const right = () => screen.getAllByRole("button", { name: "Take one weight off the right" });
const equation = () => document.querySelector(".lp-eq")!.textContent;

describe("BalanceScale", () => {
  it("starts level with the equation written out", () => {
    render(<BalanceScale widget={balance} locale="en" reducedMotion />);
    expect(equation()).toBe("2x + 3=11");
    expect(left()).toHaveLength(3);
    expect(right()).toHaveLength(11);
    expect(screen.getByRole("img")).toHaveAccessibleName(/Left pan: 2 boxes and 3 weights.*Level\./);
    expect(screen.getByRole("button", { name: /split both sides in half/i })).toBeDisabled();
  });

  it("tilts when only one side changes, and Undo puts it back", async () => {
    render(<BalanceScale widget={balance} locale="en" reducedMotion />);
    await userEvent.click(left()[0]);
    expect(equation()).toBe("2x + 2≠11");
    expect(screen.getByText(/Tilted\./)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Undo" }));
    expect(equation()).toBe("2x + 3=11");
  });

  it("is solved by taking 3 off both sides and splitting in half; the goal is reported once", async () => {
    const onSolved = vi.fn();
    render(<BalanceScale widget={balance} locale="en" reducedMotion onSolved={onSolved} />);
    for (let i = 0; i < 3; i++) {
      await userEvent.click(left()[0]);
      await userEvent.click(right()[0]);
    }
    expect(equation()).toBe("2x=8");
    expect(screen.getByText(/Only boxes on the left now/)).toBeInTheDocument();
    expect(onSolved).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: /split both sides in half/i }));
    expect(equation()).toBe("x=4");
    expect(screen.getByText("One box balances 4 weights.")).toBeInTheDocument();
    expect(onSolved).toHaveBeenCalledTimes(1);
    expect(onSolved).toHaveBeenCalledWith({ lb: 1, lw: 0, rb: 0, rw: 4 }, 7);
  });

  it("can be started over and used with the keyboard", async () => {
    render(<BalanceScale widget={balance} locale="en" reducedMotion />);
    left()[0].focus();
    await userEvent.keyboard("{Enter}");
    expect(equation()).toBe("2x + 2≠11");
    await userEvent.click(screen.getByRole("button", { name: "Start over" }));
    expect(equation()).toBe("2x + 3=11");
  });
});

describe("FunctionGraph", () => {
  const slider = () => screen.getByRole("slider") as HTMLInputElement;

  it("shows the line, the target and a readout", () => {
    render(<FunctionGraph widget={graph} locale="en" />);
    expect(slider().value).toBe("1");
    expect(screen.getByText("target = 11")).toBeInTheDocument();
    expect(screen.getByText(/x = 1, the line is at 5/)).toBeInTheDocument();
    expect(screen.getByRole("img")).toHaveAccessibleName(/target line at 11/);
  });

  it("guides the student towards the target", () => {
    render(<FunctionGraph widget={graph} locale="en" />);
    expect(screen.getByText(/lower than the target\. Slide to the right/)).toBeInTheDocument();
    fireEvent.change(slider(), { target: { value: "6" } });
    expect(screen.getByText(/higher than the target\. Slide to the left/)).toBeInTheDocument();
  });

  it("is solved at x = 4 (near drags snap onto it) and reports it once", () => {
    const onSolved = vi.fn();
    render(<FunctionGraph widget={graph} locale="en" onSolved={onSolved} />);
    fireEvent.change(slider(), { target: { value: "3" } });
    expect(onSolved).not.toHaveBeenCalled();
    fireEvent.change(slider(), { target: { value: "4" } });
    expect(screen.getByText("The line reaches 11 at x = 4.")).toBeInTheDocument();
    expect(onSolved).toHaveBeenCalledTimes(1);
    expect(onSolved.mock.calls[0][0]).toEqual({ x: 4 });
  });
});
