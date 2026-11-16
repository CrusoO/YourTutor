import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async (orig) => ({
  ...(await orig<typeof import("@/lib/api")>()),
  getFinderRules: vi.fn(),
  getActionRules: vi.fn(),
  getContextOptions: vi.fn(),
  guestStart: vi.fn(),
  today: vi.fn(),
  answerOnboarding: vi.fn(),
  getChapters: vi.fn(),
  explainChat: vi.fn(),
}));
vi.mock("@/lib/chat/identity", () => ({ currentIdentity: vi.fn() }));

import { Replies } from "@/components/chat/Bubbles";
import { ChatProvider, useChatApi } from "@/components/chat/ChatProvider";
import { Composer } from "@/components/chat/Composer";
import * as api from "@/lib/api";
import { currentIdentity } from "@/lib/chat/identity";

const RULES = {
  max_chars: 300,
  pii: { email: "[^\\s]+@[^\\s]+", phone: "\\d{10,}", url: "https?://\\S+" },
  distress_terms: ["hopeless"],
  blocked_patterns: [],
  blocked_terms: [],
};
const CTX = { grades: [], curricula: [{ id: "cbse", grades: [{ grade: 10, subjects: [{ id: "math", books: [] }] }] }] };

function Peek() {
  const { lesson, role } = useChatApi();
  return (
    <p data-testid="peek">
      {role}|{lesson ? lesson.prompt : "no-lesson"}
    </p>
  );
}
function Harness() {
  return (
    <ChatProvider>
      <Composer />
      <Replies />
      <Peek />
    </ChatProvider>
  );
}

async function ask(text: string) {
  await userEvent.type(await screen.findByTestId("composer-input"), text);
  await userEvent.keyboard("{Enter}");
}

beforeEach(() => {
  vi.mocked(api.getFinderRules).mockResolvedValue(RULES as never);
  vi.mocked(api.getActionRules).mockRejectedValue(new Error("no rules"));
  vi.mocked(api.getContextOptions).mockResolvedValue(CTX as never);
  vi.mocked(api.guestStart).mockResolvedValue(undefined as never);
  vi.mocked(currentIdentity).mockResolvedValue(null);
});
afterEach(() => {
  cleanup();
  vi.unstubAllEnvs();
  vi.clearAllMocks();
});

describe("the doubt card in the chat (signed out and guest)", () => {
  it("a signed-out visitor typing an equation gets the confirm card, with no guest started and nothing sent", async () => {
    vi.stubEnv("NEXT_PUBLIC_DOUBT_DEVICE", "true");
    render(<Harness />);
    await ask("2x + 3 = 11");
    expect(await screen.findByTestId("doubt-card", {}, { timeout: 10_000 })).toHaveAttribute("data-stage", "confirm");
    expect(screen.getByTestId("doubt-expression")).toHaveTextContent("2 × x + 3 = 11");
    expect(screen.getByTestId("peek")).toHaveTextContent("visitor|no-lesson");
    expect(api.guestStart).not.toHaveBeenCalled();
    expect(api.explainChat).not.toHaveBeenCalled();
  });

  it("a guest gets the same card, and the 'looks right' step works", async () => {
    vi.stubEnv("NEXT_PUBLIC_DOUBT_DEVICE", "true");
    vi.mocked(currentIdentity).mockResolvedValue({ role: "guest" });
    render(<Harness />);
    await waitFor(() => expect(screen.getByTestId("peek")).toHaveTextContent("guest|"));
    await ask("x^2 - 5x + 6 = 0");
    await userEvent.click(await screen.findByTestId("doubt-confirm", {}, { timeout: 10_000 }));
    expect(screen.getByTestId("doubt-label")).toHaveTextContent("Worked out on your device");
  });

  it("pushback on the card is answered by putting the value back in the equation", async () => {
    vi.stubEnv("NEXT_PUBLIC_DOUBT_DEVICE", "true");
    render(<Harness />);
    await ask("2x + 3 = 11");
    await userEvent.click(await screen.findByTestId("doubt-confirm", {}, { timeout: 10_000 }));
    await ask("my book says x = 3");
    expect(await screen.findByTestId("doubt-pushback", {}, { timeout: 10_000 })).toHaveTextContent(/left side is 9 and the right side is 11/);
    expect(screen.getByTestId("doubt-label")).toBeInTheDocument(); // the same card, state kept
  });

  it("an unsupported but maths-looking question: calm card, and the explain hand-off waits for a tap", async () => {
    vi.stubEnv("NEXT_PUBLIC_DOUBT_DEVICE", "true");
    render(<Harness />);
    await ask("sin x = 1/2");
    expect(await screen.findByRole("heading", { name: "I can't solve this one yet" }, { timeout: 10_000 })).toBeInTheDocument();
    expect(screen.getByTestId("peek")).toHaveTextContent("visitor|no-lesson");
    expect(api.guestStart).not.toHaveBeenCalled();
    await userEvent.click(screen.getByTestId("doubt-explain"));
    await waitFor(() => expect(screen.getByTestId("peek")).toHaveTextContent("guest|sin x = 1/2"));
    expect(screen.queryByTestId("doubt-card")).toBeNull();
  });

  it("Edit puts the text back in the composer", async () => {
    vi.stubEnv("NEXT_PUBLIC_DOUBT_DEVICE", "true");
    render(<Harness />);
    await ask("2x + 3 = 11");
    await userEvent.click(await screen.findByTestId("doubt-edit", {}, { timeout: 10_000 }));
    expect((screen.getByTestId("composer-input") as HTMLTextAreaElement).value).toBe("2x + 3 = 11");
    expect(screen.queryByTestId("doubt-card")).toBeNull();
  });

  it("text that is not maths keeps today's route", async () => {
    vi.stubEnv("NEXT_PUBLIC_DOUBT_DEVICE", "true");
    render(<Harness />);
    await ask("why is the sky blue");
    await waitFor(() => expect(screen.getByTestId("peek")).toHaveTextContent("guest|why is the sky blue"));
    expect(screen.queryByTestId("doubt-card")).toBeNull();
  });

  it("distress text is never read as maths: the usual route runs", async () => {
    vi.stubEnv("NEXT_PUBLIC_DOUBT_DEVICE", "true");
    render(<Harness />);
    await ask("it is hopeless 2x + 3 = 11");
    await waitFor(() => expect(screen.getByTestId("peek")).toHaveTextContent("hopeless"));
    expect(screen.queryByTestId("doubt-card")).toBeNull();
  });
});

describe("with the flag off the composer behaves as it did before", () => {
  it("an equation goes the usual way and there is no keypad or card", async () => {
    vi.stubEnv("NEXT_PUBLIC_DOUBT_DEVICE", "false");
    render(<Harness />);
    expect(screen.queryByTestId("composer-keypad")).toBeNull();
    await ask("2x + 3 = 11");
    await waitFor(() => expect(screen.getByTestId("peek")).toHaveTextContent("guest|2x + 3 = 11"));
    expect(screen.queryByTestId("doubt-card")).toBeNull();
  });

  it("makes no extra rules request: a flag-off submit never reaches the maths step", async () => {
    vi.stubEnv("NEXT_PUBLIC_DOUBT_DEVICE", "false");
    render(<Harness />);
    await ask("2x + 3 = 11");
    await waitFor(() => expect(api.guestStart).toHaveBeenCalled());
    expect(api.getFinderRules).not.toHaveBeenCalled();
  });
});
