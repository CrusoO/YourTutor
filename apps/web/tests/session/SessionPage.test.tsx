import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import SessionPage from "@/app/session/[id]/page";
import { getSession, postEvent } from "@/lib/api";
import { actionFixtures } from "./actionFixtures";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "sess-test" }),
  useRouter: () => ({ push }),
}));

vi.mock("@/lib/api", () => ({
  getSession: vi.fn(),
  postEvent: vi.fn(),
  locale: () => "en",
}));

function mockSession(action: typeof actionFixtures.show_item) {
  vi.mocked(getSession).mockResolvedValue({
    id: "sess-test",
    type: "practice",
    student_id: "stu-1",
    action,
    progress: { items_completed: 0, active_ms: 0, resumable: false },
  });
  vi.mocked(postEvent).mockImplementation(async (_id, event_type, payload) => ({
    id: "sess-test",
    session_id: "sess-test",
    type: "practice",
    student_id: "stu-1",
    action: { ...action, type: action.type },
    progress: { items_completed: 0, active_ms: 0, resumable: false },
  }));
}

async function renderAction(key: keyof typeof actionFixtures) {
  mockSession(actionFixtures[key]);
  render(<SessionPage />);
  await waitFor(() => expect(getSession).toHaveBeenCalled());
}

describe("SessionPage action rendering", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it.each(Object.keys(actionFixtures) as (keyof typeof actionFixtures)[])(
    "renders %s",
    async (key) => {
      await renderAction(key);
      expect(screen.getByRole("main")).toBeInTheDocument();
    },
  );

  it("predict sends predict_response yes", async () => {
    await renderAction("predict");
    await userEvent.click(screen.getByRole("button", { name: /^yes$/i }));
    expect(postEvent).toHaveBeenCalledWith(
      "sess-test",
      "predict_response",
      { response: "yes" },
      actionFixtures.predict.item_id,
    );
  });

  it("worked_example continue after steps", async () => {
    await renderAction("worked_example");
    await userEvent.click(screen.getByRole("button", { name: /show next step/i }));
    await userEvent.click(screen.getByRole("button", { name: /^continue$/i }));
    expect(postEvent).toHaveBeenCalledWith("sess-test", "continue", {}, actionFixtures.worked_example.item_id);
  });

  it("show_item sends answer on check", async () => {
    await renderAction("show_item");
    await userEvent.type(screen.getByPlaceholderText(/type your answer/i), "6");
    await userEvent.click(screen.getByRole("button", { name: /check/i }));
    expect(postEvent).toHaveBeenCalledWith(
      "sess-test",
      "answer",
      expect.objectContaining({ response: "6" }),
      actionFixtures.show_item.item_id,
    );
  });

  it("show_item sends i don't know when chosen", async () => {
    await renderAction("show_item");
    await userEvent.click(screen.getByRole("button", { name: /i don't know/i }));
    expect(postEvent).toHaveBeenCalledWith(
      "sess-test",
      "answer",
      expect.objectContaining({ response: "i don't know" }),
      actionFixtures.show_item.item_id,
    );
  });

  it("hint retry sends answer", async () => {
    await renderAction("hint");
    await userEvent.type(screen.getByPlaceholderText(/type your answer/i), "5");
    await userEvent.click(screen.getByRole("button", { name: /check/i }));
    expect(postEvent).toHaveBeenCalledWith("sess-test", "answer", expect.objectContaining({ response: "5" }), "ITEM.FIX.1");
  });

  it("feedback continue", async () => {
    await renderAction("feedback");
    expect(screen.getByText(/not yet/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /^continue$/i }));
    expect(postEvent).toHaveBeenCalledWith("sess-test", "continue", {}, actionFixtures.feedback.item_id);
  });

  it("reveal_solution continue", async () => {
    await renderAction("reveal_solution");
    await userEvent.click(screen.getByRole("button", { name: /try a similar one/i }));
    expect(postEvent).toHaveBeenCalledWith("sess-test", "continue", {}, actionFixtures.reveal_solution.item_id);
  });

  it("explain_back_prompt sends explain_back", async () => {
    await renderAction("explain_back_prompt");
    await userEvent.type(screen.getByPlaceholderText(/explain it in your own words/i), "Because I subtract.");
    await userEvent.click(screen.getByRole("button", { name: /^continue$/i }));
    expect(postEvent).toHaveBeenCalledWith(
      "sess-test",
      "explain_back",
      { text: "Because I subtract." },
      actionFixtures.explain_back_prompt.item_id,
    );
  });

  it("nudge continue", async () => {
    await renderAction("nudge");
    await userEvent.click(screen.getByRole("button", { name: /^continue$/i }));
    expect(postEvent).toHaveBeenCalledWith("sess-test", "continue", {}, actionFixtures.nudge.item_id);
  });

  it("end_session shows done", async () => {
    await renderAction("end_session");
    expect(screen.getByRole("heading", { name: /done for now/i })).toBeInTheDocument();
  });

  it("checkpoint_score shows score", async () => {
    await renderAction("checkpoint_score");
    expect(screen.getByText(/score:/i)).toBeInTheDocument();
  });

  it("warmup_item sends answer", async () => {
    await renderAction("warmup_item");
    expect(screen.getByText(/x \+ 4 = 10/i)).toBeInTheDocument();
    await userEvent.type(screen.getByPlaceholderText(/type your answer/i), "6");
    await userEvent.click(screen.getByRole("button", { name: /check/i }));
    expect(postEvent).toHaveBeenCalledWith(
      "sess-test",
      "answer",
      expect.objectContaining({ response: "6" }),
      actionFixtures.warmup_item.item_id,
    );
  });

  it("similar_item sends answer", async () => {
    await renderAction("similar_item");
    await userEvent.type(screen.getByPlaceholderText(/type your answer/i), "6");
    await userEvent.click(screen.getByRole("button", { name: /check/i }));
    expect(postEvent).toHaveBeenCalledWith(
      "sess-test",
      "answer",
      expect.objectContaining({ response: "6" }),
      actionFixtures.similar_item.item_id,
    );
  });

  it("content_gap navigates to today", async () => {
    await renderAction("content_gap");
    await userEvent.click(screen.getByRole("button", { name: /back to today/i }));
    expect(push).toHaveBeenCalledWith("/today");
  });

  it("explain_back_result continue", async () => {
    await renderAction("explain_back_result");
    expect(screen.getByText(/thanks for explaining/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /^continue$/i }));
    expect(postEvent).toHaveBeenCalledWith("sess-test", "continue", {}, actionFixtures.explain_back_result.item_id);
  });

  it("hint show_solution when hint level is 2", async () => {
    mockSession({ ...actionFixtures.hint, hint_level: 2, can_show_solution: true });
    render(<SessionPage />);
    await waitFor(() => expect(getSession).toHaveBeenCalled());
    await userEvent.click(screen.getByRole("button", { name: /show the solution/i }));
    expect(postEvent).toHaveBeenCalledWith("sess-test", "show_solution", {}, actionFixtures.hint.item_id);
  });

  it("idle nudge sends idle_nudge event", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    mockSession(actionFixtures.show_item);
    render(<SessionPage />);
    await waitFor(() => expect(getSession).toHaveBeenCalled());
    await vi.advanceTimersByTimeAsync(90_000);
    const nudge = await screen.findByRole("button", { name: /still there/i });
    await user.click(nudge);
    expect(postEvent).toHaveBeenCalledWith(
      "sess-test",
      "idle_nudge",
      expect.objectContaining({ idle_ms: expect.any(Number) }),
      actionFixtures.show_item.item_id,
    );
    vi.useRealTimers();
  });

  it("show_item request_hint after timer", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    mockSession(actionFixtures.show_item);
    render(<SessionPage />);
    await waitFor(() => expect(getSession).toHaveBeenCalled());
    await vi.advanceTimersByTimeAsync(60_000);
    const hintBtn = await screen.findByRole("button", { name: /^hint$/i });
    await user.click(hintBtn);
    expect(postEvent).toHaveBeenCalledWith("sess-test", "request_hint", {}, actionFixtures.show_item.item_id);
    vi.useRealTimers();
  });
});
