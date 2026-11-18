import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import SessionPage from "@/app/session/[id]/page";
import { ConfidenceAsk, ConfidenceTap, ExplainGrade, WhyWrong } from "@/components/session/Signals";
import { getSession, postEvent, type ActionPayload } from "@/lib/api";
import { t } from "@/lib/messages";
import { MAX_ANSWER_MS, elapsedMs } from "@/lib/session-timers";
import { actionFixture, actionFixtures } from "./actionFixtures";

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "sess-test" }),
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  getSession: vi.fn(),
  postEvent: vi.fn(),
  locale: () => "en",
}));

const copy = t("en");

describe("elapsedMs", () => {
  it("is the real time, in whole milliseconds, never below 1 and never above five minutes", () => {
    expect(elapsedMs(1000, 3500)).toBe(2500);
    expect(elapsedMs(1000, 1000.4)).toBe(1);
    expect(elapsedMs(1000, 900)).toBe(1);
    expect(elapsedMs(1000, 1000 + 10 * 60_000)).toBe(MAX_ANSWER_MS);
    expect(elapsedMs(Number.NaN, 5)).toBe(1);
  });
});

describe("ConfidenceAsk", () => {
  afterEach(cleanup);

  it("shows the answer and three choices; each sends once and Skip sends no confidence", async () => {
    const onChoose = vi.fn();
    render(<ConfidenceAsk copy={copy} answer="3" busy={false} onChoose={onChoose} />);
    expect(screen.getByRole("group", { name: "How sure were you?" })).toBeInTheDocument();
    expect(screen.getByTestId("confidence-answer")).toHaveTextContent("3");
    await userEvent.click(screen.getByTestId("confidence-sure"));
    expect(onChoose).toHaveBeenLastCalledWith("sure");
    await userEvent.click(screen.getByTestId("confidence-unsure"));
    expect(onChoose).toHaveBeenLastCalledWith("unsure");
    await userEvent.click(screen.getByTestId("confidence-skip"));
    expect(onChoose).toHaveBeenLastCalledWith(null);
  });

  it("is reachable by keyboard and disables every button while sending", async () => {
    const onChoose = vi.fn();
    const { rerender } = render(<ConfidenceAsk copy={copy} answer="3" busy={false} onChoose={onChoose} />);
    expect(screen.getByTestId("confidence-sure")).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    expect(onChoose).toHaveBeenCalledWith("sure");
    rerender(<ConfidenceAsk copy={copy} answer="3" busy onChoose={onChoose} />);
    for (const id of ["sure", "unsure", "skip"]) expect(screen.getByTestId(`confidence-${id}`)).toBeDisabled();
    expect(screen.getByTestId("confidence").querySelector("[aria-live]")).not.toBeNull();
  });
});

describe("WhyWrong", () => {
  afterEach(cleanup);

  it.each([
    ["misconception", "where it went off track"],
    ["slip", "small slip"],
    ["prerequisite_gap", "from before"],
    ["incomplete_procedure", "one step early"],
  ])("says something plain for %s", (kind, words) => {
    render(<WhyWrong copy={copy} diagnosis={{ class: kind }} onNotWhy={vi.fn()} />);
    expect(screen.getByTestId("why-wrong")).toHaveTextContent(words);
  });

  it("shows nothing for a class it has no words for, or none at all", () => {
    for (const diagnosis of [{ class: "generic" }, { class: "disengagement" }, {}, undefined]) {
      const { container } = render(<WhyWrong copy={copy} diagnosis={diagnosis} onNotWhy={vi.fn()} />);
      expect(container).toBeEmptyDOMElement();
      cleanup();
    }
  });

  it("sends 'that's not why' once, with the class that was shown, and then thanks the learner", async () => {
    const onNotWhy = vi.fn();
    render(<WhyWrong copy={copy} diagnosis={{ class: "slip" }} onNotWhy={onNotWhy} />);
    await userEvent.click(screen.getByTestId("not-why"));
    expect(onNotWhy).toHaveBeenCalledTimes(1);
    expect(onNotWhy).toHaveBeenCalledWith("slip");
    expect(screen.queryByTestId("not-why")).toBeNull();
    expect(screen.getByRole("status")).toHaveTextContent("Okay, thanks for telling us.");
  });

  it("shows a plain described mistake with Yes / No buttons, and a gentle line for a jargon one", () => {
    const plain = "You added 7 instead of taking 7 away.";
    const { rerender } = render(
      <WhyWrong copy={copy} diagnosis={{ class: "misconception", description: plain }} onNotWhy={vi.fn()} />,
    );
    expect(screen.getByRole("heading", { name: "Let's look at your answer" })).toBeInTheDocument();
    expect(screen.getByText("It looks like you may have done this:")).toBeInTheDocument();
    expect(screen.getByTestId("why-mistake")).toHaveTextContent(plain);
    expect(screen.getByRole("button", { name: "Yes, that is what I did" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "No, I did something else" })).toBeInTheDocument();
    rerender(
      <WhyWrong
        copy={copy}
        diagnosis={{ class: "misconception", description: "The inverse of subtraction is addition." }}
        onNotWhy={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("why-mistake")).toBeNull();
    expect(screen.getByTestId("why-generic")).toHaveTextContent("Let's work out together");
    // Nothing specific is said, so there is nothing to confirm: no Yes / No buttons.
    expect(screen.queryByTestId("yes-why")).toBeNull();
    expect(screen.queryByTestId("not-why")).toBeNull();
  });
});

describe("ExplainGrade", () => {
  afterEach(cleanup);

  it.each([
    ["good", "main idea"],
    ["partly", "partway there"],
    ["not_yet", "Not yet"],
  ])("shows the %s grade in words", (grade, words) => {
    render(<ExplainGrade copy={copy} grade={grade} />);
    expect(screen.getByTestId("explain-grade")).toHaveTextContent(words);
  });

  it("shows nothing when there is no grade or it is unknown", () => {
    for (const grade of [null, undefined, "", "excellent"]) {
      const { container } = render(<ExplainGrade copy={copy} grade={grade} />);
      expect(container).toBeEmptyDOMElement();
      cleanup();
    }
  });
});

function mockSession(action: ActionPayload) {
  vi.mocked(getSession).mockResolvedValue({
    id: "sess-test",
    type: "practice",
    student_id: "stu-1",
    action,
    progress: { items_completed: 0, active_ms: 0, resumable: false },
  });
  vi.mocked(postEvent).mockImplementation(async () => ({
    id: "sess-test",
    session_id: "sess-test",
    type: "practice",
    student_id: "stu-1",
    action,
    progress: { items_completed: 0, active_ms: 0, resumable: false },
  }));
}

describe("SessionPage signals", () => {
  let now = 10_000;

  beforeEach(() => {
    vi.clearAllMocks();
    now = 10_000;
    vi.spyOn(Date, "now").mockImplementation(() => now);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  async function open(action: ActionPayload) {
    mockSession(action);
    render(<SessionPage />);
    await waitFor(() => expect(getSession).toHaveBeenCalled());
    await screen.findByRole("main");
  }

  it("sends how long the answer really took, not a constant", async () => {
    await open(actionFixtures.show_item!);
    now += 7_300;
    await userEvent.type(screen.getByPlaceholderText(/type your answer/i), "6");
    await userEvent.click(screen.getByRole("button", { name: /check/i }));
    now += 3_000;
    await userEvent.click(screen.getByTestId("confidence-skip"));
    const payload = vi.mocked(postEvent).mock.calls.at(-1)![2] as { latency_ms: number };
    expect(payload.latency_ms).toBeGreaterThanOrEqual(7_300);
    expect(payload.latency_ms).toBeLessThan(MAX_ANSWER_MS);
    expect([200, 400, 500]).not.toContain(payload.latency_ms);
  });

  it("times 'I don't know' for real as well", async () => {
    await open(actionFixtures.show_item!);
    now += 4_100;
    await userEvent.click(screen.getByRole("button", { name: /i don't know/i }));
    const payload = vi.mocked(postEvent).mock.calls.at(-1)![2] as { latency_ms: number };
    expect(payload.latency_ms).toBeGreaterThanOrEqual(4_100);
  });

  async function check(value = "6") {
    await userEvent.type(screen.getByPlaceholderText(/type your answer/i), value);
    await userEvent.click(screen.getByRole("button", { name: /check/i }));
  }

  it("asks how sure only after Check, and sends nothing until a choice is made", async () => {
    await open(actionFixtures.show_item!);
    expect(screen.queryByTestId("confidence")).toBeNull();
    await check();
    expect(screen.getByTestId("confidence")).toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/type your answer/i)).toBeNull();
    expect(postEvent).not.toHaveBeenCalled();
  });

  it("sends the answer with the chosen confidence", async () => {
    await open(actionFixtures.show_item!);
    await check();
    await userEvent.click(screen.getByTestId("confidence-unsure"));
    expect(postEvent).toHaveBeenCalledTimes(1);
    expect(vi.mocked(postEvent).mock.calls.at(-1)![2]).toMatchObject({ response: "6", confidence: "unsure" });
  });

  it("Skip sends the answer with no confidence", async () => {
    await open(actionFixtures.show_item!);
    await check();
    await userEvent.click(screen.getByTestId("confidence-skip"));
    expect(postEvent).toHaveBeenCalledTimes(1);
    const payload = vi.mocked(postEvent).mock.calls.at(-1)![2];
    expect(payload).toMatchObject({ response: "6" });
    expect(payload).not.toHaveProperty("confidence");
  });

  it("never double-sends: rapid taps give one request", async () => {
    await open(actionFixtures.show_item!);
    await check();
    let release: () => void = () => {};
    vi.mocked(postEvent).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          release = () =>
            resolve({
              id: "sess-test",
              session_id: "sess-test",
              type: "practice",
              student_id: "stu-1",
              action: actionFixtures.show_item!,
              progress: { items_completed: 0, active_ms: 0, resumable: false },
            });
        }),
    );
    const sure = screen.getByTestId("confidence-sure");
    await userEvent.click(sure);
    await userEvent.click(sure);
    await userEvent.click(screen.getByTestId("confidence-skip"));
    expect(postEvent).toHaveBeenCalledTimes(1);
    release();
  });

  it("keeps the answer and lets the learner try again when sending fails", async () => {
    await open(actionFixtures.show_item!);
    await check();
    vi.mocked(postEvent).mockRejectedValueOnce(new Error("offline"));
    await userEvent.click(screen.getByTestId("confidence-sure"));
    await waitFor(() => expect(screen.getByTestId("confidence-sure")).not.toBeDisabled());
    expect(screen.getByTestId("confidence-answer")).toHaveTextContent("6");
    await userEvent.click(screen.getByTestId("confidence-sure"));
    expect(postEvent).toHaveBeenCalledTimes(2);
  });

  it("lets the learner change the answer before it is sent", async () => {
    await open(actionFixtures.show_item!);
    await check();
    await userEvent.click(screen.getByTestId("confidence-change"));
    expect(screen.queryByTestId("confidence")).toBeNull();
    expect(screen.getByPlaceholderText(/type your answer/i)).toBeInTheDocument();
  });

  it("asks after a multiple-choice pick, before any feedback", async () => {
    const item = {
      id: "i1",
      type: "mcq",
      stem: "Pick",
      options: [
        { id: "a", label: "Five" },
        { id: "b", label: "Six" },
      ],
    };
    await open(actionFixture("show_item", { session_type: "practice", item: item as never }));
    expect(screen.queryByTestId("confidence")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Six" }));
    expect(screen.getByTestId("confidence-answer")).toHaveTextContent("Six");
    expect(postEvent).not.toHaveBeenCalled();
    await userEvent.click(screen.getByTestId("confidence-sure"));
    expect(vi.mocked(postEvent).mock.calls.at(-1)![2]).toMatchObject({ response: "b", confidence: "sure" });
  });

  it("I don't know still sends at once, with no confidence step", async () => {
    await open(actionFixtures.show_item!);
    await userEvent.click(screen.getByRole("button", { name: /i don't know/i }));
    expect(screen.queryByTestId("confidence")).toBeNull();
    expect(postEvent).toHaveBeenCalledTimes(1);
  });

  it("offers no confidence tap in a diagnostic, a checkpoint or a warm-up", async () => {
    for (const action of [
      actionFixture("show_item", { session_type: "diagnostic" }),
      actionFixture("show_item", { session_type: "checkpoint" }),
      actionFixtures.warmup_item!,
    ]) {
      await open(action);
      expect(screen.queryByTestId("confidence")).toBeNull();
      cleanup();
    }
  });

  it("explains a wrong answer in plain words on the hint screen and records 'that's not why' without moving", async () => {
    const hint = actionFixture("hint", {
      text: "Try undoing the + 4.",
      hint_level: 1,
      extras: { diagnosis: { class: "slip" } },
    });
    await open(hint);
    expect(screen.getByTestId("why-wrong")).toHaveTextContent("small slip");
    await userEvent.click(screen.getByTestId("not-why"));
    expect(postEvent).toHaveBeenCalledWith("sess-test", "diagnosis_correction", { diagnosed: "slip" }, hint.item_id);
    expect(screen.getByTestId("hint-text")).toHaveTextContent("Try undoing the + 4.");
  });

  it("says nothing about why when the server did not send a diagnosis", async () => {
    await open(actionFixtures.hint!);
    expect(screen.queryByTestId("why-wrong")).toBeNull();
  });

  it("shows the explain-back grade and the explanation together", async () => {
    await open(actionFixture("explain_back_result", { text: "Thanks for explaining.", grade: "partly" }));
    expect(screen.getByTestId("explain-grade")).toHaveTextContent("partway there");
    expect(screen.getByText("Thanks for explaining.")).toBeInTheDocument();
  });
});
