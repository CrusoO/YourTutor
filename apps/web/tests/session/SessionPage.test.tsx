import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
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

  it("end_session shows the Done screen in plain words (S1b: no raw reason code)", async () => {
    await renderAction("end_session");
    expect(screen.getByRole("heading", { name: /nice work/i })).toBeInTheDocument();
    expect(screen.getByText(/good amount for now/i)).toBeInTheDocument();
    expect(screen.queryByText("soft_cap")).not.toBeInTheDocument();
  });

  it("an idle end is explained without the word idle", async () => {
    mockSession({ ...actionFixtures.end_session, ended_reason: "idle", reason: "idle" });
    render(<SessionPage />);
    expect(await screen.findByText(/you were away for a while/i)).toBeInTheDocument();
    expect(screen.queryByText(/^idle$/)).not.toBeInTheDocument();
  });

  it("no screen shows the raw session type", async () => {
    await renderAction("show_item");
    expect(screen.queryByText(/^practice$/)).not.toBeInTheDocument();
  });

  it("warm-up items say what they are", async () => {
    await renderAction("warmup_item");
    expect(screen.getByRole("heading", { name: /quick warm-up/i })).toBeInTheDocument();
    expect(screen.getByText(/questions from before/i)).toBeInTheDocument();
  });

  it("skip ahead shows its progress, never a hint button", async () => {
    mockSession({
      ...actionFixtures.show_item,
      session_type: "test_out",
      extras: { assessment: true, test_out: { index: 2, of: 2 } },
    });
    render(<SessionPage />);
    expect(await screen.findByRole("heading", { name: /show what you know/i })).toBeInTheDocument();
    expect(screen.getByText(/question 2 of 2/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^hint$/i })).not.toBeInTheDocument();
  });

  it.each([
    [true, /already know this/i],
    [false, /let's practise it together/i],
  ])("skip ahead result (passed=%s) never uses penalty wording", async (passed, words) => {
    mockSession({
      ...actionFixtures.show_item,
      type: "test_out_result",
      item: null,
      extras: { passed, level: passed ? 4 : 0 },
    });
    render(<SessionPage />);
    const result = await screen.findByTestId("test-out-result");
    expect(result).toHaveTextContent(words);
    expect(result.textContent).not.toMatch(/fail|wrong|lost|penalt|score/i);
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

  it("show_item offers Help straight away and sends request_help (G2: the picker asks first)", async () => {
    await renderAction("show_item");
    await userEvent.click(await screen.findByRole("button", { name: /^help$/i }));
    expect(postEvent).toHaveBeenCalledWith("sess-test", "request_help", {}, actionFixtures.show_item.item_id);
  });

  it("Help is hidden when the server does not allow it, and the old flag still works", async () => {
    mockSession({ ...actionFixtures.show_item, can_request_help: undefined, can_request_hint: false, allow_hint: false });
    render(<SessionPage />);
    await waitFor(() => expect(getSession).toHaveBeenCalled());
    expect(screen.queryByRole("button", { name: /^help$/i })).not.toBeInTheDocument();
    cleanup();
    mockSession({ ...actionFixtures.show_item, can_request_help: undefined, can_request_hint: true });
    render(<SessionPage />);
    expect(await screen.findByRole("button", { name: /^help$/i })).toBeInTheDocument();
  });

  it("the stuck-point picker offers the four choices and sends the pick", async () => {
    await renderAction("ask_stuck_point");
    expect(screen.getByRole("heading", { name: /where are you stuck/i })).toBeInTheDocument();
    for (const label of [/don't know how to start/i, /stuck at a step/i, /don't understand the question/i, /answer might be right/i]) {
      expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
    }
    await userEvent.click(screen.getByRole("button", { name: /don't understand the question/i }));
    expect(postEvent).toHaveBeenCalledWith("sess-test", "stuck_choice", { choice: "restate" }, actionFixtures.ask_stuck_point.item_id);
  });

  it("the picker only shows the choices the server offers", async () => {
    mockSession({ ...actionFixtures.ask_stuck_point, extras: { choices: ["start", "might_be_right"], step_count: 0 } });
    render(<SessionPage />);
    await screen.findByRole("heading", { name: /where are you stuck/i });
    expect(screen.queryByRole("button", { name: /stuck at a step/i })).not.toBeInTheDocument();
    expect(screen.getAllByRole("button")).toHaveLength(2);
  });

  it("the step picker shows numbered steps, never the solution steps", async () => {
    await renderAction("ask_stuck_step");
    const buttons = screen.getAllByRole("button");
    expect(buttons.map((b) => b.textContent)).toEqual(["Step 1", "Step 2", "Step 3"]);
    expect(screen.queryByText(/Subtract 4/)).not.toBeInTheDocument();
    await userEvent.click(buttons[1]);
    expect(postEvent).toHaveBeenCalledWith("sess-test", "stuck_step", { index: 1 }, actionFixtures.ask_stuck_step.item_id);
  });

  it.each([
    ["sign_flip", /signs in each line/i],
    ["off_by", /arithmetic, line by line/i],
    ["values", /last step again/i],
    ["recheck", /one at a time/i],
    ["something_else", /look over your work once more/i],
  ])("check_your_work (%s) says what to look at, never the answer", async (kind, words) => {
    mockSession({ ...actionFixtures.check_your_work, extras: { check_kind: kind } });
    render(<SessionPage />);
    const box = await screen.findByTestId("check-your-work");
    expect(within(box).getByText(words)).toBeInTheDocument();
    expect(box.textContent).not.toContain(actionFixtures.check_your_work.item?.answer ?? "@@none@@");
    cleanup();
  });

  it("check_your_work lets the student try again and still offers Help", async () => {
    await renderAction("check_your_work");
    await userEvent.type(screen.getByPlaceholderText(/type your answer/i), "6");
    await userEvent.click(screen.getByRole("button", { name: /check/i }));
    expect(postEvent).toHaveBeenCalledWith("sess-test", "answer", expect.objectContaining({ response: "6" }), actionFixtures.check_your_work.item_id);
  });

  it("a restated question or a step hint is labelled as such", async () => {
    mockSession({ ...actionFixtures.hint, text: "Read it again.", extras: { kind: "restate" } });
    render(<SessionPage />);
    expect(await screen.findByText(/the question again/i)).toBeInTheDocument();
    cleanup();
    mockSession({ ...actionFixtures.hint, text: "Undo the plus.", extras: { kind: "step", step: 0 } });
    render(<SessionPage />);
    expect(await screen.findByText(/hint for that step/i)).toBeInTheDocument();
  });

  it("a hint screen offers Help while the server allows it and hides it after two hints", async () => {
    mockSession({ ...actionFixtures.hint, can_request_help: true, extras: { kind: "restate" } });
    render(<SessionPage />);
    await userEvent.click(await screen.findByRole("button", { name: /^help$/i }));
    expect(postEvent).toHaveBeenCalledWith("sess-test", "request_help", {}, actionFixtures.hint.item_id);
    cleanup();
    mockSession({ ...actionFixtures.hint, can_request_help: false, can_show_solution: true });
    render(<SessionPage />);
    await screen.findByTestId("hint-text");
    expect(screen.queryByRole("button", { name: /^help$/i })).not.toBeInTheDocument();
  });

  it("break_or_switch offers a break, something different, or carrying on, in calm words", async () => {
    await renderAction("break_or_switch");
    expect(screen.getByRole("heading", { name: /want a short break/i })).toBeInTheDocument();
    for (const label of [/take a short break/i, /try something different/i, /keep going/i]) {
      expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
    }
    const box = screen.getByTestId("break-or-switch");
    expect(box.textContent).not.toMatch(/rushing|guess|careless|lazy|too fast/i);
    await userEvent.click(screen.getByRole("button", { name: /try something different/i }));
    expect(postEvent).toHaveBeenCalledWith("sess-test", "break_choice", { choice: "switch" }, actionFixtures.break_or_switch.item_id);
  });

  it("a probe question is labelled as a quick check and offers no Help", async () => {
    mockSession({
      ...actionFixtures.show_item,
      can_request_help: false,
      can_request_hint: false,
      extras: { probe: true, for_skill: "S1" },
    });
    render(<SessionPage />);
    expect(await screen.findByTestId("probe")).toHaveTextContent(/quick check/i);
    expect(screen.queryByRole("button", { name: /^help$/i })).not.toBeInTheDocument();
  });

  it("a challenge question and a closing win are labelled", async () => {
    mockSession({ ...actionFixtures.show_item, extras: { challenge: true } });
    render(<SessionPage />);
    expect(await screen.findByTestId("challenge")).toHaveTextContent(/challenge/i);
    cleanup();
    mockSession({ ...actionFixtures.show_item, extras: { win: true } });
    render(<SessionPage />);
    expect(await screen.findByTestId("win")).toHaveTextContent(/quick one to finish/i);
  });

  it("a representation change says it is another way of looking at the skill", async () => {
    mockSession({ ...actionFixtures.worked_example, extras: { representation_change: true } });
    render(<SessionPage />);
    expect(await screen.findByTestId("other-view")).toHaveTextContent(/another way/i);
  });

  it("shows authored encouragement above the next screen, and a short note after a step-down", async () => {
    mockSession({
      ...actionFixtures.show_item,
      extras: {
        support: "step_down",
        encouragement: { trigger: "recovery", variant: "kept_trying", text: "You kept going and it paid off." },
      },
    });
    render(<SessionPage />);
    expect(await screen.findByTestId("encouragement")).toHaveTextContent("You kept going and it paid off.");
    expect(screen.getByTestId("support-note")).toHaveTextContent(/smaller step first/i);
  });

  it("the Done screen shows session-end encouragement and a break reason in plain words", async () => {
    mockSession({
      ...actionFixtures.end_session,
      ended_reason: "break",
      reason: "break",
      extras: { encouragement: { trigger: "session_end", variant: "steady_work", text: "Nice steady work today." } },
    });
    render(<SessionPage />);
    expect(await screen.findByTestId("encouragement")).toHaveTextContent("Nice steady work today.");
    expect(screen.getByText(/taking a break is a good idea/i)).toBeInTheDocument();
    expect(screen.queryByText("break")).not.toBeInTheDocument();
  });

  it("show_item after 'might be right' asks the student to submit", async () => {
    mockSession({ ...actionFixtures.show_item, extras: { prompt_submit: true } });
    render(<SessionPage />);
    expect(await screen.findByText(/go ahead and type your answer/i)).toBeInTheDocument();
  });
});
