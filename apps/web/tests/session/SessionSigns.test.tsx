import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import SessionPage from "@/app/session/[id]/page";
import { getSession, postEvent, type ActionPayload } from "@/lib/api";
import { actionFixture, sampleItem } from "./actionFixtures";

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "sess-test" }),
  useRouter: () => ({ push: vi.fn() }),
}));
vi.mock("@/lib/api", () => ({ getSession: vi.fn(), postEvent: vi.fn(), locale: () => "en" }));

const sum = { ...sampleItem, stem: "Compute 10 + (-7).", answer: "3", steps: ["Adding -7 to 10 is 3.", "x = 3"] };
const base = { allow_hint: true, can_request_help: true, can_request_hint: true, dont_know_option: true, item: sum };

const view = (action: ActionPayload, done = 0) => ({
  id: "sess-test",
  session_id: "sess-test",
  type: "practice",
  student_id: "s",
  action,
  progress: { items_completed: done, active_ms: 0, resumable: false },
});

function start(first: ActionPayload, done = 0) {
  vi.mocked(getSession).mockResolvedValue(view(first, done));
}

beforeEach(() => vi.clearAllMocks());
afterEach(cleanup);

describe("number-line hint on a practice item", () => {
  it("is not offered before any attempt", async () => {
    start(actionFixture("show_item", base));
    render(<SessionPage />);
    await screen.findByTestId("help-button");
    expect(screen.queryByTestId("sign-hint-button")).toBeNull();
  });

  it("appears after the first wrong answer and never shows the result", async () => {
    start(actionFixture("show_item", base));
    vi.mocked(postEvent).mockResolvedValue(view(actionFixture("hint", { ...base, text: "Think about the sign.", hint_level: 1 })));
    render(<SessionPage />);
    await userEvent.type(await screen.findByPlaceholderText(/type your answer/i), "17");
    await userEvent.click(screen.getByRole("button", { name: /check/i }));
    await userEvent.click(screen.getByTestId("confidence-skip"));
    const button = await screen.findByTestId("sign-hint-button");
    expect(screen.getByTestId("hint-heading")).toHaveTextContent("Not quite. Here is a hint.");
    await userEvent.click(button);
    const body = await screen.findByTestId("sign-hint-body");
    expect(body.textContent).toMatch(/A plus sign means go right/);
    expect(body.textContent).not.toMatch(/land/i);
    expect(screen.getByTestId("mini-number-line")).toHaveAttribute("data-landing", "hidden");
    // I don't know and Help still there
    expect(screen.getByTestId("dont-know")).toBeInTheDocument();
    expect(screen.getByTestId("help-button")).toBeInTheDocument();
  });

  it("appears after Help is pressed", async () => {
    start(actionFixture("show_item", base));
    vi.mocked(postEvent).mockResolvedValue(view(actionFixture("hint", { ...base, text: "A hint.", hint_level: 1 })));
    render(<SessionPage />);
    await userEvent.click(await screen.findByTestId("help-button"));
    expect(await screen.findByTestId("sign-hint-button")).toBeInTheDocument();
    expect(screen.getByTestId("hint-heading")).toHaveTextContent("Here is a hint.");
    expect(postEvent).toHaveBeenCalledWith("sess-test", "request_help", {}, sum.id);
  });

  it("is not offered for a stem that is not integer arithmetic", async () => {
    start(actionFixture("hint", { ...base, item: sampleItem, text: "A hint.", hint_level: 1 }));
    render(<SessionPage />);
    await screen.findByTestId("hint-text");
    expect(screen.queryByTestId("sign-hint-button")).toBeNull();
  });
});

describe("solution screen", () => {
  it("shows the sign panel, hides the stray x step and cleans the source", async () => {
    start(
      actionFixture("reveal_solution", {
        ...base,
        sources: [{ id: "SRC.INT", title: "Adding and subtracting integers (authored note)" }],
      }),
    );
    render(<SessionPage />);
    expect(await screen.findByTestId("sign-explanation")).toBeInTheDocument();
    expect(screen.getByText("What does the sign mean?")).toBeInTheDocument();
    expect(screen.getByText("Start at 10.")).toBeInTheDocument();
    expect(screen.getByText("You land on 3.")).toBeInTheDocument();
    expect(screen.queryByText("x = 3")).toBeNull();
    expect(screen.getByText("From the lesson: Adding and subtracting whole numbers")).toBeInTheDocument();
    expect(screen.getByTestId("solution-answer")).toHaveTextContent("3");
  });

  it("keeps the normal solution when the answer does not match the parse", async () => {
    start(actionFixture("reveal_solution", { ...base, item: { ...sum, answer: "4" } }));
    render(<SessionPage />);
    await waitFor(() => expect(screen.getByTestId("solution-answer")).toHaveTextContent("4"));
    expect(screen.queryByTestId("sign-explanation")).toBeNull();
    expect(screen.getByText("Adding -7 to 10 is 3.")).toBeInTheDocument();
  });

  it("keeps x = steps when the stem has an x", async () => {
    start(actionFixture("reveal_solution", { ...base, item: sampleItem }));
    render(<SessionPage />);
    expect(await screen.findByText("x = 6")).toBeInTheDocument();
  });
});

describe("progress header", () => {
  it("shows the question number from items completed, no percentage", async () => {
    start(actionFixture("show_item", base), 3);
    render(<SessionPage />);
    expect(await screen.findByTestId("progress-count")).toHaveTextContent("Question 4");
  });
});
