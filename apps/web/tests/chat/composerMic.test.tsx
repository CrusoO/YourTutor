import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const submitText = vi.fn();
vi.mock("@/components/chat/ChatProvider", () => ({
  MODES_BY_ROLE: { visitor: ["learn"] },
  useChatApi: () => ({
    copy: new Proxy({}, { get: (_t, k) => String(k) }),
    role: "visitor",
    mode: "learn",
    setMode: vi.fn(),
    busy: false,
    ctx: null,
    submitText: (text: string) => submitText(text),
  }),
}));

import { Composer } from "@/components/chat/Composer";

afterEach(() => {
  cleanup();
  submitText.mockReset();
  vi.unstubAllEnvs();
});

describe("the composer mic", () => {
  it("is not rendered by default", () => {
    render(<Composer />);
    expect(screen.queryByTestId("composer-mic")).toBeNull();
    expect(screen.getByTestId("composer-send")).toBeTruthy();
  });

  it("is not rendered when the flag is anything but true", () => {
    vi.stubEnv("NEXT_PUBLIC_VOICE_ENABLED", "1");
    render(<Composer />);
    expect(screen.queryByTestId("composer-mic")).toBeNull();
  });

  it("appears only when NEXT_PUBLIC_VOICE_ENABLED is true", () => {
    vi.stubEnv("NEXT_PUBLIC_VOICE_ENABLED", "true");
    render(<Composer />);
    expect(screen.getByTestId("composer-mic")).toBeTruthy();
  });
});

describe("the composer without the chat runtime", () => {
  it("sends the trimmed text once on Enter, clears the box and keeps Shift+Enter for a new line", () => {
    render(<Composer />);
    const box = screen.getByTestId("composer-input") as HTMLTextAreaElement;
    fireEvent.change(box, { target: { value: "  what is a quadratic  " } });
    fireEvent.keyDown(box, { key: "Enter", shiftKey: true });
    expect(submitText).not.toHaveBeenCalled();
    fireEvent.keyDown(box, { key: "Enter" });
    expect(submitText).toHaveBeenCalledTimes(1);
    expect(submitText).toHaveBeenCalledWith("what is a quadratic");
    expect(box.value).toBe("");
  });

  it("says what to do on an empty send instead of sending", () => {
    render(<Composer />);
    fireEvent.click(screen.getByTestId("composer-send"));
    expect(submitText).not.toHaveBeenCalled();
    expect(screen.getByTestId("composer-hint").textContent).toBe("chatSendEmptyHint");
  });
});
