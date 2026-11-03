import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import SessionPage from "@/app/session/[id]/page";
import { ConfidenceTap, ExplainGrade, WhyWrong } from "@/components/session/Signals";
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

describe("ConfidenceTap", () => {
  it("offers two optional choices, and tapping the chosen one again clears it", async () => {
    const onChange = vi.fn();
    const { rerender } = render(<ConfidenceTap copy={copy} value={null} onChange={onChange} />);
    expect(screen.getByRole("group", { name: "How sure are you?" })).toBeInTheDocument();
    await userEvent.click(screen.getByTestId("confidence-sure"));
    expect(onChange).toHaveBeenLastCalledWith("sure");
    rerender(<ConfidenceTap copy={copy} value="sure" onChange={onChange} />);
    expect(screen.getByTestId("confidence-sure")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("confidence-unsure")).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(screen.getByTestId("confidence-sure"));
    expect(onChange).toHaveBeenLastCalledWith(null);
  });
});

describe("WhyWrong", () => {
  afterEach(cleanup);

  it.each([
    ["misconception", "A common idea"],
    ["slip", "small slip"],
    ["prerequisite_gap", "earlier idea"],
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
    expect(screen.getByRole("status")).toHaveTextContent("Got it, thanks.");
  });
});

describe("ExplainGrade", () => {
  afterEach(cleanup);

  it.each([
    ["good", "Clear"],
    ["partly", "Partly there"],
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

  it("sends the confidence only when the learner tapped it", async () => {
    await open(actionFixtures.show_item!);
    await userEvent.type(screen.getByPlaceholderText(/type your answer/i), "6");
    await userEvent.click(screen.getByRole("button", { name: /check/i }));
    expect(vi.mocked(postEvent).mock.calls.at(-1)![2]).not.toHaveProperty("confidence");

    cleanup();
    vi.clearAllMocks();
    await open(actionFixtures.show_item!);
    await userEvent.click(screen.getByTestId("confidence-unsure"));
    await userEvent.type(screen.getByPlaceholderText(/type your answer/i), "6");
    await userEvent.click(screen.getByRole("button", { name: /check/i }));
    expect(vi.mocked(postEvent).mock.calls.at(-1)![2]).toMatchObject({ response: "6", confidence: "unsure" });
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
    expect(screen.getByTestId("explain-grade")).toHaveTextContent("Partly there");
    expect(screen.getByText("Thanks for explaining.")).toBeInTheDocument();
  });
});
