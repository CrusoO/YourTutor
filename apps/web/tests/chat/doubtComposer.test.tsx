import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

const submitText = vi.fn();
let draft: { n: number; text: string } | null = null;
vi.mock("@/components/chat/ChatProvider", () => ({
  MODES_BY_ROLE: { visitor: ["learn"] },
  useChatApi: () => ({
    copy: new Proxy({}, { get: (_t, k) => String(k) }),
    role: "visitor",
    mode: "learn",
    setMode: vi.fn(),
    busy: false,
    ctx: null,
    draft,
    submitText: (text: string) => submitText(text),
  }),
}));

import { Composer } from "@/components/chat/Composer";

afterEach(() => {
  cleanup();
  submitText.mockReset();
  draft = null;
  vi.unstubAllEnvs();
});

async function openKeypad() {
  await userEvent.click(screen.getByTestId("composer-keypad"));
  return screen.findByTestId("doubt-keypad");
}

describe("the equation keypad", () => {
  it("is not there when the flag is off (production default)", () => {
    vi.stubEnv("NEXT_PUBLIC_DOUBT_DEVICE", "false");
    render(<Composer />);
    expect(screen.queryByTestId("composer-keypad")).toBeNull();
    expect(screen.getByTestId("composer-send")).toBeTruthy();
  });

  it("is not there when the variable is unset outside development", () => {
    render(<Composer />);
    expect(screen.queryByTestId("composer-keypad")).toBeNull();
  });

  it("is on in development by default", () => {
    vi.stubEnv("NODE_ENV", "development");
    render(<Composer />);
    expect(screen.getByTestId("composer-keypad")).toBeInTheDocument();
  });

  it("opens only on a tap, is labelled, and every key is a 44 px named button", async () => {
    vi.stubEnv("NEXT_PUBLIC_DOUBT_DEVICE", "true");
    render(<Composer />);
    expect(screen.queryByTestId("doubt-keypad")).toBeNull();
    const toggle = screen.getByTestId("composer-keypad");
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    const pad = await openKeypad();
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(pad).toHaveAttribute("aria-label", "Equation keypad");
    for (const name of ["x", "y", "plus", "minus", "times", "divided by", "power", "open bracket", "close bracket", "equals", "fraction", "square root", "0", "9"]) {
      expect(screen.getByRole("button", { name })).toBeInTheDocument();
    }
    for (const b of pad.querySelectorAll("button")) {
      expect(b.className).toContain("min-h-11");
      expect(b.className).toContain("min-w-11");
      expect(b.className).not.toMatch(/text-\[(?:[0-9]|10|11)px\]/);
    }
  });

  it("fills the composer at the cursor and sends nothing", async () => {
    vi.stubEnv("NEXT_PUBLIC_DOUBT_DEVICE", "true");
    render(<Composer />);
    await openKeypad();
    const box = screen.getByTestId("composer-input") as HTMLTextAreaElement;
    for (const name of ["2", "x", "plus", "3", "equals", "1", "1"]) await userEvent.click(screen.getByRole("button", { name }));
    expect(box.value).toBe("2x + 3 = 11");
    expect(submitText).not.toHaveBeenCalled();
    await userEvent.click(screen.getByTestId("key-backspace"));
    expect(box.value).toBe("2x + 3 = 1");
    await userEvent.click(screen.getByTestId("key-clear"));
    expect(box.value).toBe("");
  });

  it("fraction and square root leave the cursor inside the brackets", async () => {
    vi.stubEnv("NEXT_PUBLIC_DOUBT_DEVICE", "true");
    render(<Composer />);
    await openKeypad();
    const box = screen.getByTestId("composer-input") as HTMLTextAreaElement;
    await userEvent.click(screen.getByRole("button", { name: "fraction" }));
    expect(box.value).toBe("()/()");
    expect(box.selectionStart).toBe(1);
    await userEvent.click(screen.getByRole("button", { name: "9" }));
    expect(box.value).toBe("(9)/()");
    box.value = "";
    await userEvent.click(screen.getByRole("button", { name: "square root" }));
    expect(box.value).toBe("√()");
    expect(box.selectionStart).toBe(2);
  });

  it("what the keypad fills is sent through the same submit as typed text", async () => {
    vi.stubEnv("NEXT_PUBLIC_DOUBT_DEVICE", "true");
    render(<Composer />);
    await openKeypad();
    for (const name of ["x", "equals", "4"]) await userEvent.click(screen.getByRole("button", { name }));
    fireEvent.keyDown(screen.getByTestId("composer-input"), { key: "Enter" });
    expect(submitText).toHaveBeenCalledWith("x = 4");
  });
});

describe("Edit on a doubt card", () => {
  it("puts the text back in the box when the flag is on", () => {
    vi.stubEnv("NEXT_PUBLIC_DOUBT_DEVICE", "true");
    draft = { n: 1, text: "2x + 3 = 11" };
    render(<Composer />);
    expect((screen.getByTestId("composer-input") as HTMLTextAreaElement).value).toBe("2x + 3 = 11");
  });
});
