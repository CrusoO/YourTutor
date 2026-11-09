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


describe("AskAbout when the question is a cry for help", () => {
  it("shows the helplines under the support message", async () => {
    vi.mocked(api.explainChat).mockResolvedValue({
      kind: "distress",
      message: "Please talk to a grown-up you trust. The lines below can listen.",
      helplines: [{ id: "tele_manas", kind: "mental_health", name: "Tele-MANAS", number: "14416", hours: null, verified: true }],
    });
    render(<AskAbout prompt="slope" language="en" onPractice={onPractice} />);
    await ask("i want to die");
    expect(await screen.findByTestId("ask-about-tutor")).toHaveTextContent("The lines below can listen.");
    expect(screen.getByRole("link", { name: /Tele-MANAS/ })).toHaveAttribute("href", "tel:14416");
  });
});

describe("AskAbout while the reply is being written", () => {
  it("shows the text as it arrives, then keeps the final reply without revealing it again", async () => {
    let release: () => void = () => {};
    const gate = new Promise<void>((resolve) => (release = resolve));
    vi.mocked(api.explainChat).mockImplementation(async (_p, _l, _h, onDelta) => {
      onDelta?.("You are close.");
      await gate;
      return { kind: "reply", text: "You are close. What do you notice?" };
    });
    render(<AskAbout prompt="slope" language="en" />);
    await ask("why does it double");
    expect(await screen.findByTestId("ask-about-live")).toHaveTextContent("You are close.");
    release();
    await waitFor(() => expect(screen.queryByTestId("ask-about-live")).toBeNull());
    expect(screen.getByTestId("ask-about-tutor")).toHaveTextContent("You are close. What do you notice?");
  });

  it("replaces what was shown when the server's final reply differs (the guard stepped in)", async () => {
    vi.mocked(api.explainChat).mockImplementation(async (_p, _l, _h, onDelta) => {
      onDelta?.("Nice start.");
      return { kind: "reply", text: "What undoes the +5?" };
    });
    render(<AskAbout prompt="slope" language="en" />);
    await ask("what is x");
    expect(await screen.findByTestId("ask-about-tutor")).toHaveTextContent("What undoes the +5?");
    expect(screen.getByTestId("ask-about-tutor")).not.toHaveTextContent("Nice start.");
  });
});
