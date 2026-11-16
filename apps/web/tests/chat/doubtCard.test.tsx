import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import DoubtCard from "@/components/chat/doubt/DoubtCard";
import { readDoubt, readPushback } from "@/components/chat/doubt/pipeline";
import type { DoubtPayload } from "@/components/chat/doubt/types";
import { LABEL_DEVICE } from "@/lib/doubt/copy.en";

afterEach(cleanup);

function payload(text: string): DoubtPayload {
  const p = readDoubt(text);
  if (!p) throw new Error(`not a doubt: ${text}`);
  return p;
}
function mount(p: DoubtPayload, over: Partial<{ onEdit: (t: string) => void; onClose: () => void; onExplain: (t: string) => void }> = {}) {
  const fns = { onEdit: vi.fn(), onClose: vi.fn(), onExplain: vi.fn(), ...over };
  const view = render(<DoubtCard doubt={p} {...fns} />);
  return { ...view, ...fns };
}
async function confirm() {
  await userEvent.click(screen.getByTestId("doubt-confirm"));
}

const WRONG_WORDS = /\b(across|flip|transpose)\b|change (the )?sign|switch (the )?sign|move\b[^.]*\bto the other side/i;

describe("the confirm step", () => {
  it("asks 'Did we read this right?', shows the expression, and solves nothing before the student confirms", () => {
    mount(payload("2x + 3 = 11"));
    expect(screen.getByRole("heading", { name: "Did we read this right?" })).toBeInTheDocument();
    expect(screen.getByTestId("doubt-expression")).toHaveTextContent("2 × x + 3 = 11");
    expect(screen.getByTestId("doubt-confirm")).toHaveTextContent("Looks right");
    expect(screen.getByTestId("doubt-edit")).toHaveTextContent("Edit");
    expect(screen.queryByTestId("doubt-label")).toBeNull();
    expect(screen.queryByTestId("hint-next")).toBeNull();
    expect(screen.queryByTestId("doubt-tried")).toBeNull();
    expect(screen.getByTestId("doubt-card").textContent).not.toMatch(/\bx = 4\b/);
  });

  it("moves focus to the card heading when it appears", () => {
    mount(payload("2x + 3 = 11"));
    expect(screen.getByRole("heading", { name: "Did we read this right?" })).toHaveFocus();
  });

  it("Edit hands the typed text back and solves nothing", async () => {
    const { onEdit } = mount(payload("2x + 3 = 11"));
    await userEvent.click(screen.getByTestId("doubt-edit"));
    expect(onEdit).toHaveBeenCalledWith("2x + 3 = 11");
  });

  it("Looks right shows the device label, moves focus, and opens no hint by itself", async () => {
    mount(payload("2x + 3 = 11"));
    await confirm();
    expect(screen.getByTestId("doubt-label")).toHaveTextContent(LABEL_DEVICE);
    expect(screen.getByTestId("doubt-label")).toHaveTextContent("Worked out on your device");
    expect(screen.getByRole("heading", { level: 3 })).toHaveFocus();
    expect(screen.getByTestId("hint-next")).toHaveTextContent("Show a hint");
    expect(screen.queryByText(/Hint 1 of/)).toBeNull();
  });
});

describe("the hint ladder", () => {
  it("opens one hint at a time, and the full steps only after a hint is open", async () => {
    mount(payload("2x + 3 = 11"));
    await confirm();
    expect(screen.getByTestId("hint-steps")).toBeDisabled();
    expect(screen.getByText("Open a hint first")).toBeInTheDocument();
    await userEvent.click(screen.getByTestId("hint-next"));
    expect(screen.getByText(/Hint 1 of 3/)).toBeInTheDocument();
    expect(screen.queryByText(/Hint 2 of 3/)).toBeNull();
    expect(screen.getByTestId("hint-steps")).toBeEnabled();
    expect(screen.queryByTestId("full-steps")).toBeNull();
    await userEvent.click(screen.getByTestId("hint-next"));
    expect(screen.getByText(/Hint 2 of 3/)).toBeInTheDocument();
    await userEvent.click(screen.getByTestId("hint-steps"));
    const steps = screen.getByTestId("full-steps");
    expect(steps).toHaveTextContent("Here are all the steps.");
    expect(steps).toHaveTextContent(/x = 4/);
  });

  it("announces each revealed level in a polite live region", async () => {
    mount(payload("2x + 3 = 11"));
    await confirm();
    expect(screen.getByTestId("hint-list")).toHaveAttribute("aria-live", "polite");
  });

  it("keeps the level in the card: a second card starts again at no hints", async () => {
    const a = mount(payload("2x + 3 = 11"));
    await confirm();
    await userEvent.click(screen.getByTestId("hint-next"));
    a.unmount();
    mount(payload("3x - 1 = 8"));
    await confirm();
    expect(screen.queryByText(/Hint 1 of/)).toBeNull();
  });
});

describe("'I tried'", () => {
  it("a wrong answer gets amber 'look again' feedback and does not reveal the answer", async () => {
    mount(payload("2x + 3 = 11"));
    await confirm();
    await userEvent.type(screen.getByTestId("doubt-tried-input"), "x = 5");
    await userEvent.click(screen.getByTestId("doubt-tried-check"));
    const fb = screen.getByTestId("doubt-feedback").closest("[data-variant]") as HTMLElement;
    expect(fb).toHaveAttribute("data-variant", "look-again");
    expect(within(fb).getByText("Not quite, let's look again")).toBeInTheDocument();
    expect(fb.textContent).toMatch(/not a solution|does not work/);
    expect(fb.textContent).not.toMatch(/\bx = 4\b|is 4\b/);
    expect(screen.getByTestId("doubt-card").textContent).not.toMatch(/\bx = 4\b/);
  });

  it("a right answer gets the quiet green card", async () => {
    mount(payload("2x + 3 = 11"));
    await confirm();
    await userEvent.type(screen.getByTestId("doubt-tried-input"), "x = 4");
    await userEvent.click(screen.getByTestId("doubt-tried-check"));
    expect(screen.getByTestId("doubt-feedback").closest("[data-variant]")).toHaveAttribute("data-variant", "correct");
  });

  it("checks a next step: a balanced step is accepted, a wrong one gets 'look again'", async () => {
    mount(payload("2x + 3 = 11"));
    await confirm();
    await userEvent.click(screen.getByRole("button", { name: "My next step" }));
    await userEvent.type(screen.getByTestId("doubt-tried-input"), "2x = 8");
    await userEvent.click(screen.getByTestId("doubt-tried-check"));
    expect(screen.getByTestId("doubt-feedback").closest("[data-variant]")).toHaveAttribute("data-variant", "correct");
    await userEvent.clear(screen.getByTestId("doubt-tried-input"));
    await userEvent.type(screen.getByTestId("doubt-tried-input"), "2x = 9");
    await userEvent.click(screen.getByTestId("doubt-tried-check"));
    expect(screen.getByTestId("doubt-feedback").closest("[data-variant]")).toHaveAttribute("data-variant", "look-again");
  });
});

describe("a quadratic with surd roots", () => {
  it("is worked out exactly and the full steps show the surd form", async () => {
    mount(payload("x^2 + x - 1 = 0"));
    await confirm();
    await userEvent.click(screen.getByTestId("hint-next"));
    await userEvent.click(screen.getByTestId("hint-steps"));
    expect(screen.getByTestId("full-steps").textContent).toMatch(/√5/);
  });
});

describe("pushback", () => {
  it("puts the claimed value back into the equation and shows that check on the card", async () => {
    const p = payload("2x + 3 = 11");
    const said = readPushback(p, "that's wrong, my book says x = 3");
    expect(said).toMatch(/does not work/);
    mount({ ...p, pushback: said ?? undefined });
    await confirm();
    expect(screen.getByTestId("doubt-pushback")).toHaveTextContent(/left side is 9 and the right side is 11/);
  });

  it("is not a pushback when the text is not one", () => {
    expect(readPushback(payload("2x + 3 = 11"), "3x - 1 = 8")).toBeNull();
  });
});

describe("what is not solved here", () => {
  it("shows a calm 'I can't solve this one yet' card and sends nothing until the student taps", async () => {
    const { onExplain, onClose } = mount(payload("sin x = 1/2"));
    expect(screen.getByRole("heading", { name: "I can't solve this one yet" })).toBeInTheDocument();
    expect(onExplain).not.toHaveBeenCalled();
    await userEvent.click(screen.getByTestId("doubt-explain"));
    expect(onExplain).toHaveBeenCalledWith("sin x = 1/2");
    await userEvent.click(screen.getByTestId("doubt-close"));
    expect(onClose).toHaveBeenCalled();
  });

  it("non-maths text is not a doubt at all", () => {
    expect(readDoubt("why is the sky blue")).toBeNull();
    expect(readDoubt("I have 2 apples")).toBeNull();
  });
});

describe("honesty and wording", () => {
  const CASES = ["2x + 3 = 11", "x^2 - 5x + 6 = 0", "x^2 + x - 1 = 0", "3(x - 2) = 12", "x + y = 5; x - y = 1", "2(3+4)*5", "(x+1)^2", "sin x = 1/2"];

  it("never renders across/flip/transpose wording on any card, at any level", async () => {
    for (const text of CASES) {
      const p = readDoubt(text);
      if (!p) continue;
      const view = mount(p);
      if (p.outcome === "candidate") {
        await confirm();
        const next = screen.queryByTestId("hint-next");
        for (let i = 0; i < 4 && screen.queryByTestId("hint-next"); i++) await userEvent.click(screen.getByTestId("hint-next"));
        if (next || screen.queryByTestId("hint-steps")) await userEvent.click(screen.getByTestId("hint-steps"));
      }
      expect(view.container.textContent ?? "", text).not.toMatch(WRONG_WORDS);
      view.unmount();
    }
  });

  it("teaches 'the same ... to both sides'", async () => {
    mount(payload("2x + 3 = 11"));
    await confirm();
    await userEvent.click(screen.getByTestId("hint-next"));
    await userEvent.click(screen.getByTestId("hint-next"));
    expect(screen.getByTestId("hint-list").textContent).toMatch(/both sides/);
  });

  it("never uses the words reserved for server-verified results, on any card", async () => {
    for (const text of CASES) {
      const p = readDoubt(text);
      if (!p) continue;
      const view = mount(p);
      if (p.outcome === "candidate") await confirm();
      expect(view.container.textContent ?? "").not.toMatch(/checked by code/i);
      view.unmount();
    }
  });
});
