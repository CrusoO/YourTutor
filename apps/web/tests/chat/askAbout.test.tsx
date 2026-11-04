import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const onPractice = vi.fn();

vi.mock("@/lib/api", () => ({
  explainChat: vi.fn(),
}));

import { AskAbout } from "@/components/chat/lesson/AskAbout";
import * as api from "@/lib/api";

const FALLBACK = {
  reason: "unavailable",
  text: "I couldn't get an answer for that just now. It isn't anything you did.",
  offers: [
    { id: "ask_again", label: "Ask it another way" },
    { id: "practice", label: "Try a practice question" },
  ],
};

async function ask(text: string) {
  await userEvent.type(screen.getByTestId("ask-about-input"), text);
  await userEvent.click(screen.getByRole("button", { name: "Ask" }));
}

beforeEach(() => onPractice.mockClear());
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("AskAbout when Brownie cannot answer", () => {
  it("shows the authored line as Brownie's turn, not an error", async () => {
    vi.mocked(api.explainChat).mockResolvedValue({ kind: "unavailable", reason: "provider_error", fallback: FALLBACK });
    render(<AskAbout prompt="slope" language="en" onPractice={onPractice} />);
    await ask("why does it double");
    expect(await screen.findByTestId("ask-about-tutor")).toHaveTextContent("It isn't anything you did.");
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("offers the choices the server named", async () => {
    vi.mocked(api.explainChat).mockResolvedValue({ kind: "unavailable", reason: "provider_error", fallback: FALLBACK });
    render(<AskAbout prompt="slope" language="en" onPractice={onPractice} />);
    await ask("why does it double");
    expect(await screen.findByTestId("offer-ask_again")).toHaveTextContent("Ask it another way");
    expect(screen.getByTestId("offer-practice")).toHaveTextContent("Try a practice question");
  });

  it("'ask it another way' brings the question back into the box", async () => {
    vi.mocked(api.explainChat).mockResolvedValue({ kind: "unavailable", reason: "provider_error", fallback: FALLBACK });
    render(<AskAbout prompt="slope" language="en" onPractice={onPractice} />);
    await ask("why does it double");
    await userEvent.click(await screen.findByTestId("offer-ask_again"));
    expect(screen.getByTestId("ask-about-input")).toHaveValue("why does it double");
    expect(screen.queryByTestId("ask-about-offers")).toBeNull();
  });

  it("'practice' starts practice through the chat", async () => {
    vi.mocked(api.explainChat).mockResolvedValue({ kind: "unavailable", reason: "provider_error", fallback: FALLBACK });
    render(<AskAbout prompt="slope" language="en" onPractice={onPractice} />);
    await ask("why does it double");
    await userEvent.click(await screen.findByTestId("offer-practice"));
    expect(onPractice).toHaveBeenCalledTimes(1);
  });

  it("does not offer practice where nothing can start it", async () => {
    vi.mocked(api.explainChat).mockResolvedValue({ kind: "unavailable", reason: "provider_error", fallback: FALLBACK });
    render(<AskAbout prompt="slope" language="en" />);
    await ask("why does it double");
    expect(await screen.findByTestId("offer-ask_again")).toBeInTheDocument();
    expect(screen.queryByTestId("offer-practice")).toBeNull();
  });

  it("ignores an offer id it does not know", async () => {
    vi.mocked(api.explainChat).mockResolvedValue({
      kind: "unavailable",
      reason: "provider_error",
      fallback: { ...FALLBACK, offers: [{ id: "launch", label: "Do the thing" }] },
    });
    render(<AskAbout prompt="slope" language="en" onPractice={onPractice} />);
    await ask("why does it double");
    await userEvent.click(await screen.findByTestId("offer-launch"));
    expect(onPractice).not.toHaveBeenCalled();
    expect(screen.getByTestId("ask-about-input")).toHaveValue("");
  });

  it("clears the choices when the learner asks again", async () => {
    vi.mocked(api.explainChat)
      .mockResolvedValueOnce({ kind: "unavailable", reason: "provider_error", fallback: FALLBACK })
      .mockResolvedValueOnce({ kind: "reply", text: "Think about the units." });
    render(<AskAbout prompt="slope" language="en" onPractice={onPractice} />);
    await ask("why does it double");
    await screen.findByTestId("ask-about-offers");
    await ask("what about the units");
    await waitFor(() => expect(screen.queryByTestId("ask-about-offers")).toBeNull());
    expect(await screen.findByText("Think about the units.")).toBeInTheDocument();
  });

  it("falls back to the old warning when the server sent no fallback or the call itself failed", async () => {
    vi.mocked(api.explainChat).mockResolvedValueOnce({ kind: "unavailable", reason: "off" });
    render(<AskAbout prompt="slope" language="en" onPractice={onPractice} />);
    await ask("hello");
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    cleanup();
    vi.mocked(api.explainChat).mockRejectedValueOnce(new Error("network"));
    render(<AskAbout prompt="slope" language="en" onPractice={onPractice} />);
    await ask("hello again");
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });
});
