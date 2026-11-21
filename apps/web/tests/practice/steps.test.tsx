import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import StepEntry from "@/components/practice/StepEntry";
import { sessionEn, withSession } from "@/lib/session/copy";
import { t } from "@/lib/messages";
import {
  KEYS,
  MINUS,
  backspaceAt,
  equationFromStem,
  insertAt,
  lineView,
  readReport,
  refusalOf,
  stepRequest,
} from "@/lib/practice/steps";

afterEach(cleanup);

const copy = withSession(t("en"));
const QUAD = ["MATH.ALG.QUAD.CHECK_ROOT"];

describe("state mapping", () => {
  it("gives each state an icon, a tone and words", () => {
    expect(lineView("ok")).toEqual({ tone: "good", icon: "check", copyKey: "stepOk" });
    expect(lineView("wrong_step")).toEqual({ tone: "try", icon: "return", copyKey: "stepWrong" });
    expect(lineView("unreadable")).toEqual({ tone: "muted", icon: "question", copyKey: "stepUnreadable" });
  });

  it("never reads an unknown state as correct", () => {
    expect(lineView("great").copyKey).toBe("stepSkipped");
    expect(lineView("").tone).toBe("muted");
  });

  it("uses the agreed words, and amber (try), never red", () => {
    expect(sessionEn.stepWrong).toBe("Look at this step again");
    expect(sessionEn.stepUnreadable).toBe("I could not read this. Write it in full, like 3 + 2.");
    expect(JSON.stringify(["good", "try", "muted"])).not.toContain("red");
  });

  it("reads the server answer defensively", () => {
    const good = { supported: true, lines: [{ state: "ok" }, { state: "wrong_step", hint_key: "MC.X" }], verdict: "wrong" };
    expect(readReport(good)?.lines.map((l) => l.state)).toEqual(["ok", "wrong_step"]);
    expect(readReport({ lines: [{ state: "fine" }], verdict: "wrong" })).toBeNull();
    expect(readReport({ lines: [], verdict: "winner" })).toBeNull();
    expect(readReport(null)).toBeNull();
  });

  it("maps refusals", () => {
    expect(refusalOf(404, null)).toBe("disabled");
    expect(refusalOf(403, { detail: { code: "math_check_consent_required" } })).toBe("consent");
    expect(refusalOf(429, null)).toBe("rate");
    expect(refusalOf(422, null)).toBe("invalid");
    expect(refusalOf(500, null)).toBe("failed");
  });
});

describe("keypad editing", () => {
  it("has the agreed keys: digits, x, x squared, plus, minus U+2212, brackets, equals, or", () => {
    const labels = KEYS.map((k) => k.label);
    for (const need of ["0", "9", "x", "x²", "+", MINUS, "(", ")", "=", "or"]) expect(labels).toContain(need);
    expect(MINUS).toBe("−");
  });

  it("inserts at the caret and over a selection", () => {
    expect(insertAt("x^2", 1, 1, "7")).toEqual({ value: "x7^2", caret: 2 });
    expect(insertAt("abc", 0, 3, "x")).toEqual({ value: "x", caret: 1 });
    expect(insertAt("ab", 99, 99, "c").value).toBe("abc");
  });

  it("deletes before the caret, or the selection", () => {
    expect(backspaceAt("abc", 2, 2)).toEqual({ value: "ac", caret: 1 });
    expect(backspaceAt("abc", 0, 0)).toEqual({ value: "abc", caret: 0 });
    expect(backspaceAt("abcd", 1, 3)).toEqual({ value: "ad", caret: 1 });
  });
});

describe("equationFromStem", () => {
  it("finds the equation in a quadratics stem", () => {
    expect(equationFromStem("Which of these values of x satisfies the equation x² - 3x = 0?", QUAD)).toBe(
      "x² - 3x = 0",
    );
    expect(equationFromStem("Rearrange x² - 2x - 6 = -2x + 3 into the form ax² + bx + c = 0.", QUAD)).toBeNull();
    expect(equationFromStem("Solve: x^2 - 7x + 10 = 0.", QUAD)).toBe("x^2 - 7x + 10 = 0");
  });

  it("is offered only for a quadratics skill", () => {
    expect(equationFromStem("Solve x + 1 = 3", ["MATH.ALG.LINEAR"])).toBeNull();
    expect(equationFromStem("Solve x + 1 = 3", undefined)).toBeNull();
    expect(equationFromStem(undefined, QUAD)).toBeNull();
  });

  it("builds a request with the equation and the lines only", () => {
    expect(JSON.parse(stepRequest("x - 5 = 0", ["x = 5"]))).toEqual({
      schema: "step-check/1",
      question: "x - 5 = 0",
      lines: ["x = 5"],
    });
  });
});

function ok(json: unknown, status = 200) {
  return vi.fn().mockResolvedValue({ status, json });
}

const press = (id: string) => fireEvent.click(screen.getByTestId(`key-${id}`));

describe("StepEntry", () => {
  it("types with the keypad and shows each line's state with icon and words", async () => {
    const send = ok({
      supported: true,
      lines: [{ state: "ok" }, { state: "wrong_step" }],
      verdict: "wrong",
    });
    render(<StepEntry copy={copy} equation="x^2 - 7x + 10 = 0" send={send} />);
    expect(screen.getByTestId("step-equation")).toHaveTextContent("x^2 - 7x + 10 = 0");
    const first = screen.getByTestId("step-line-0") as HTMLInputElement;
    first.focus();
    press("open");
    press("x");
    press("minus");
    press("d2");
    press("close");
    press("eq");
    press("d0");
    expect(first.value).toBe(`(x ${MINUS} 2) = 0`);
    fireEvent.click(screen.getByTestId("step-check"));
    await waitFor(() => expect(screen.getByTestId("step-state-0")).toBeInTheDocument());
    expect(send).toHaveBeenCalledTimes(1);
    expect(JSON.parse(send.mock.calls[0][0] as string).lines).toEqual([`(x ${MINUS} 2) = 0`]);
    expect(screen.getByTestId("step-state-0")).toHaveTextContent("Correct step");
    // a new empty line is ready for the next step
    const second = screen.getByTestId("step-line-1") as HTMLInputElement;
    second.focus();
    fireEvent.change(second, { target: { value: `x = ${MINUS}2` } });
    fireEvent.click(screen.getByTestId("step-check"));
    await waitFor(() => expect(screen.getByTestId("step-state-1")).toBeInTheDocument());
    expect(screen.getByTestId("step-state-1")).toHaveTextContent("Look at this step again");
    expect(screen.getByTestId("step-state-1").dataset.state).toBe("stepWrong");
    expect(screen.getByTestId("step-verdict")).toHaveTextContent("not the answer yet");
  });

  it("an unreadable line says so, with no penalty wording", async () => {
    const send = ok({ supported: true, lines: [{ state: "unreadable" }, { state: "skipped" }], verdict: "unreadable" });
    render(<StepEntry copy={copy} equation="x^2 - 7x + 10 = 0" send={send} />);
    fireEvent.change(screen.getByTestId("step-line-0"), { target: { value: "3 +" } });
    fireEvent.click(screen.getByTestId("step-check"));
    await waitFor(() => expect(screen.getByTestId("step-state-0")).toBeInTheDocument());
    expect(screen.getByTestId("step-state-0")).toHaveTextContent("I could not read this. Write it in full, like 3 + 2.");
    expect(screen.queryByTestId("step-verdict")).toBeNull();
    expect(screen.queryByText(/wrong|mistake|incorrect/i)).toBeNull();
  });

  it("editing a line hides its stale state", async () => {
    const send = ok({ supported: true, lines: [{ state: "ok" }], verdict: "not_final" });
    render(<StepEntry copy={copy} equation="x - 5 = 0" send={send} />);
    fireEvent.change(screen.getByTestId("step-line-0"), { target: { value: "x = 5" } });
    fireEvent.click(screen.getByTestId("step-check"));
    await waitFor(() => expect(screen.getByTestId("step-state-0")).toBeInTheDocument());
    fireEvent.change(screen.getByTestId("step-line-0"), { target: { value: "x = 6" } });
    expect(screen.queryByTestId("step-state-0")).toBeNull();
  });

  it("does nothing for empty lines, and shows a plain note when refused", async () => {
    const send = ok({ detail: { code: "math_check_consent_required" } }, 403);
    render(<StepEntry copy={copy} equation="x - 5 = 0" send={send} />);
    fireEvent.click(screen.getByTestId("step-check"));
    expect(send).not.toHaveBeenCalled();
    fireEvent.change(screen.getByTestId("step-line-0"), { target: { value: "x = 5" } });
    fireEvent.click(screen.getByTestId("step-check"));
    await waitFor(() => expect(screen.getByTestId("step-note")).toBeInTheDocument());
    expect(screen.getByTestId("step-note")).toHaveTextContent("guardian");
  });

  it("keeps every key at least 48 px by style and names the keypad", () => {
    render(<StepEntry copy={copy} equation="x - 5 = 0" send={ok({})} />);
    expect(screen.getByRole("group", { name: "Maths keys" })).toBeInTheDocument();
    expect(document.querySelector("style")?.textContent).toContain("min-height: 48px");
  });
});
