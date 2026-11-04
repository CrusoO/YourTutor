import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { memoryLine } from "@/lib/chat/memory";
import { t } from "@/lib/messages";

vi.mock("@/components/chat/ChatProvider", () => ({
  useChatApi: () => ({ copy: t("en") }),
}));

import { WelcomeBack } from "@/components/chat/WelcomeBack";

const copy = t("en");
const chapter = { id: "ch1", title: "Linear equations" } as never;
const base = { resume: null, due: 0, started: true, current: { chapter, skill: "Moving a term across" } };

afterEach(cleanup);

describe("memoryLine", () => {
  it("says nothing on a first visit", () => {
    expect(memoryLine(copy, { ...base, started: false, current: null }, "Mina")).toBeNull();
    expect(memoryLine(copy, { ...base, started: false }, "Mina")).toBeNull();
  });

  it("an open session comes first, even when reviews are due", () => {
    const m = memoryLine(copy, { ...base, resume: { session_id: "s1" }, due: 4 }, "Mina");
    expect(m?.kind).toBe("resume");
    expect(m?.text).toBe("Welcome back, Mina. You left something open. Want to pick up where you left off?");
    expect(m?.button).toBe("Resume");
  });

  it("then reviews that are due, with the right plural", () => {
    expect(memoryLine(copy, { ...base, due: 1 }, "Mina")?.text).toBe(
      "Welcome back, Mina. One thing is ready to review. A few minutes now helps it stick.",
    );
    const many = memoryLine(copy, { ...base, due: 3 }, "Mina");
    expect(many?.kind).toBe("review");
    expect(many?.text).toBe("Welcome back, Mina. 3 things are ready to review. A few minutes now helps them stick.");
  });

  it("then the topic they were on, by skill name, else chapter", () => {
    const m = memoryLine(copy, base, "Mina");
    expect(m?.kind).toBe("continue");
    expect(m?.text).toBe("Welcome back, Mina. Last time you were on Moving a term across. Want to carry on?");
    expect(memoryLine(copy, { ...base, current: { chapter } }, null)?.text).toBe(
      "Welcome back. Last time you were on Linear equations. Want to carry on?",
    );
  });

  it("works without a name and never leaves a placeholder behind", () => {
    for (const seen of [{ ...base, resume: { session_id: "s" } }, { ...base, due: 2 }, base]) {
      for (const name of [undefined, null, "", "   "]) {
        const text = memoryLine(copy, seen, name)?.text ?? "";
        expect(text.startsWith("Welcome back.")).toBe(true);
        expect(text).not.toMatch(/[{}]/);
      }
    }
  });

  it("never offers a review to someone who cannot review (a guest)", () => {
    const m = memoryLine(copy, { ...base, due: 5 }, "Mina", false);
    expect(m?.kind).toBe("continue");
  });

  it("uses no streak, loss or pressure language", () => {
    const lines = [
      memoryLine(copy, { ...base, resume: { session_id: "s" } })?.text,
      memoryLine(copy, { ...base, due: 9 })?.text,
      memoryLine(copy, base)?.text,
    ].join(" ");
    expect(lines).not.toMatch(/streak|missed|lost|behind|haven't|days? (since|in a row)|don't break|hurry|exam/i);
  });
});

describe("WelcomeBack", () => {
  it("shows Brownie's line with one button that reports what it is for", async () => {
    const onGo = vi.fn();
    render(<WelcomeBack memory={{ kind: "review", text: "Welcome back. Two things are ready.", button: "Start the review" }} onGo={onGo} />);
    expect(screen.getByTestId("welcome-back")).toHaveTextContent("Welcome back. Two things are ready.");
    await userEvent.click(screen.getByTestId("welcome-review"));
    expect(onGo).toHaveBeenCalledWith("review");
  });
});
