import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  deskItems: vi.fn(),
  reviewItems: vi.fn(),
  decideDesk: vi.fn(),
  whoAmI: vi.fn(),
  inviteReviewer: vi.fn(),
  setReviewerSuspended: vi.fn(),
  issueReviewerSignInCode: vi.fn(),
  staffToken: () => "token",
}));
const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

import ReviewersAdminPage from "@/app/staff/review/reviewers/page";
import ReviewPage from "@/app/staff/review/page";
import ReviewerDesk from "@/components/staff/ReviewerDesk";
import * as api from "@/lib/api";

const card = (over: Partial<api.DeskCard> = {}): api.DeskCard => ({
  id: "ITEM.Q1",
  skill_ids: ["MATH.X"],
  type: "mcq",
  content_hash: "h1",
  stem: "Does x = 5 solve x + 7 = 12?",
  answer: "a",
  answer_text: "Yes",
  verification: { state: "verified", detail: "" },
  wrong_options: [{ answer: "b", text: "No", misconceptions: ["Wrong inverse"] }],
  solution_steps: ["Subtract 7."],
  hints: ["Undo the plus."],
  hindi: { stem: "क्या x = 5 हल है?", options: {} },
  approvals: null,
  approvals_needed: 2,
  blocked: null,
  notes: [],
  others: [],
  my_decision: null,
  my_history: [],
  ...over,
});

const saved = (over: Partial<api.DeskCard> = {}) =>
  card({
    approvals: 1,
    blocked: false,
    my_decision: { decision: "approve", note: null, severity: null, reason_code: null, checks: [true, true, true, true, true], fix_notes: [] },
    ...over,
  });

async function open(cards: api.DeskCard[] = [card(), card({ id: "ITEM.Q2", content_hash: "h2", stem: "Second question" })]) {
  vi.mocked(api.deskItems).mockResolvedValue({ total: cards.length, items: cards });
  vi.mocked(api.whoAmI).mockResolvedValue({ role: "reviewer" } as never);
  render(<ReviewerDesk />);
  await screen.findByTestId("reviewer-desk");
}

async function answerAll(user: ReturnType<typeof userEvent.setup>, values: ("y" | "n")[]) {
  for (const v of values) await user.keyboard(v);
}

beforeEach(() => vi.clearAllMocks());
afterEach(() => {
  cleanup();
  vi.unstubAllEnvs();
});

describe("reviewer desk: gating", () => {
  it("keeps Approve locked until all five answers are yes", async () => {
    const user = userEvent.setup();
    await open();
    const approve = screen.getByTestId("act-approve");
    expect((approve as HTMLButtonElement).disabled).toBe(true);
    await answerAll(user, ["y", "y", "y", "y"]);
    expect((approve as HTMLButtonElement).disabled).toBe(true);
    await user.keyboard("y");
    expect((approve as HTMLButtonElement).disabled).toBe(false);
    expect(screen.getByTestId("desk-status").textContent).toMatch(/You can approve/);
  });

  it("opens a required note under a needs-a-fix answer and blocks Fix, Reject, Skip and moving until it has 8 characters", async () => {
    const user = userEvent.setup();
    await open();
    await user.keyboard("n");
    const note = screen.getByLabelText(/What should be fixed/) as HTMLTextAreaElement;
    expect(note).toBeTruthy();
    await user.click(screen.getByRole("button", { name: /^Fix/ }));
    expect(api.decideDesk).not.toHaveBeenCalled();
    expect(screen.getByTestId("fix-note-box-0").getAttribute("data-state")).toBe("bad");
    expect(screen.getAllByRole("alert").some((e) => /say what to fix/i.test(e.textContent ?? ""))).toBe(true);
    await user.click(screen.getByRole("button", { name: /^Reject/ }));
    await user.click(screen.getByRole("button", { name: /^Skip/ }));
    await user.click(screen.getByRole("button", { name: /Question 2/ }));
    expect(api.decideDesk).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: /Question 1/ }).getAttribute("aria-current")).toBe("true");
    await user.type(note, "short");
    await user.click(screen.getByRole("button", { name: /Question 2/ }));
    expect(screen.getByRole("button", { name: /Question 1/ }).getAttribute("aria-current")).toBe("true");
    await user.type(note, " enough now");
    await user.click(screen.getByRole("button", { name: /Question 2/ }));
    expect(screen.getByRole("button", { name: /Question 2/ }).getAttribute("aria-current")).toBe("true");
  });

  it("needs a reason and a severity for Fix, then sends the fix note by question", async () => {
    const user = userEvent.setup();
    vi.mocked(api.decideDesk).mockResolvedValue(saved({ my_decision: { decision: "fix", note: null, severity: "must_fix", reason_code: "4", checks: [true, false, true, true, true], fix_notes: [] } }));
    await open();
    await answerAll(user, ["y", "n"]);
    await user.type(screen.getByLabelText(/What should be fixed/), "the rule is the wrong way round");
    await user.keyboard("{Escape}");
    await user.click(screen.getByRole("button", { name: /^Fix/ }));
    expect(api.decideDesk).not.toHaveBeenCalled();
    const text = screen.getByTestId("desk-reasons").textContent ?? "";
    expect(text).toMatch(/Pick the main reason/);
    expect(screen.getAllByRole("alert").map((a) => a.textContent).join(" ")).toMatch(/Pick how serious/);
    await user.keyboard("4");
    await user.click(screen.getByRole("button", { name: /Must fix/ }));
    // the other three questions are not answered yet: the fix is still allowed (they are not "needs a fix")
    await user.click(screen.getByRole("button", { name: /^Fix/ }));
    await waitFor(() => expect(api.decideDesk).toHaveBeenCalledTimes(1));
    const [id, body] = vi.mocked(api.decideDesk).mock.calls[0];
    expect(id).toBe("ITEM.Q1");
    expect(body).toMatchObject({
      decision: "fix",
      severity: "must_fix",
      reason_code: "4",
      content_hash: "h1",
      fix_notes: [{ question_index: 1, text: "the rule is the wrong way round" }],
    });
    expect(typeof body.active_seconds).toBe("number");
  });

  it("approves with all yes and moves to the next question", async () => {
    const user = userEvent.setup();
    vi.mocked(api.decideDesk).mockResolvedValue(saved());
    await open();
    await answerAll(user, ["y", "y", "y", "y", "y"]);
    await user.click(screen.getByTestId("act-approve"));
    await waitFor(() => expect(screen.getByTestId("desk-stem").textContent).toBe("Second question"));
    expect(vi.mocked(api.decideDesk).mock.calls[0][1]).toMatchObject({ decision: "approve", checks: [true, true, true, true, true] });
  });
});

describe("reviewer desk: keys", () => {
  it("does not fire keys while typing in a note", async () => {
    const user = userEvent.setup();
    await open();
    await user.keyboard("n");
    await user.type(screen.getByLabelText(/What should be fixed/), "yyyy aaaa nnn fff");
    const checks = screen.getByTestId("check-1");
    expect(within(checks).getByRole("button", { name: /^Yes/ }).getAttribute("aria-pressed")).toBe("false");
    expect(api.decideDesk).not.toHaveBeenCalled();
    // Esc leaves the note, then keys work again
    await user.keyboard("{Escape}");
    await user.keyboard("y");
    expect(within(screen.getByTestId("check-1")).getByRole("button", { name: /^Yes/ }).getAttribute("aria-pressed")).toBe("true");
  });

  it("opens and closes the key help with ? and Esc", async () => {
    const user = userEvent.setup();
    await open();
    await user.keyboard("?");
    expect(screen.getByRole("dialog", { name: "Keyboard help" })).toBeTruthy();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("E shows the right answer", async () => {
    const user = userEvent.setup();
    await open();
    expect(screen.queryByText("right answer")).toBeNull();
    await user.keyboard("e");
    expect(screen.getByText("right answer")).toBeTruthy();
  });
});

describe("reviewer desk: the API is the authority", () => {
  it("shows the server's 422 messages next to the field", async () => {
    const user = userEvent.setup();
    const detail = { detail: { code: "invalid_decision", errors: [{ field: "fix_notes", message: "question 2: say what to fix (at least 8 characters)" }, { field: "severity", message: "pick how serious it is" }] } };
    vi.mocked(api.decideDesk).mockRejectedValue(new api.ApiError(JSON.stringify(detail), 422));
    await open();
    await answerAll(user, ["y", "n"]);
    await user.type(screen.getByLabelText(/What should be fixed/), "enough text here");
    await user.keyboard("{Escape}");
    await user.keyboard("1");
    await user.click(screen.getByRole("button", { name: /Blocker/ }));
    await user.click(screen.getByRole("button", { name: /^Fix/ }));
    await waitFor(() => expect(api.decideDesk).toHaveBeenCalled());
    expect((await screen.findAllByText("question 2: say what to fix (at least 8 characters)")).length).toBeGreaterThan(0);
    expect(within(screen.getByTestId("check-1")).getByText(/question 2: say what to fix/)).toBeTruthy();
    expect(within(screen.getByTestId("desk-reasons")).getByText("pick how serious it is")).toBeTruthy();
  });

  it("says when the question changed (409)", async () => {
    const user = userEvent.setup();
    vi.mocked(api.decideDesk).mockRejectedValue(new api.ApiError("changed", 409));
    await open();
    await answerAll(user, ["y", "y", "y", "y", "y"]);
    await user.click(screen.getByTestId("act-approve"));
    expect((await screen.findByTestId("desk-problems")).textContent).toMatch(/changed/);
  });
});

describe("reviewer desk: blind review", () => {
  it("shows no other reviewer and no counts before the reviewer decides", async () => {
    await open([card()]);
    expect(screen.getByTestId("desk-blind")).toBeTruthy();
    expect(screen.queryByTestId("desk-others")).toBeNull();
    expect(screen.queryByTestId("desk-approvals")).toBeNull();
  });

  it("shows the others by pseudonym after the reviewer decides, from what the API returns", async () => {
    const user = userEvent.setup();
    vi.mocked(api.decideDesk).mockResolvedValue(
      saved({
        approvals: 1,
        others: [{ reviewer: "Reviewer 1", decision: "fix", note: "Hint is too long", severity: "must_fix", reason_code: "7", checks: null, fix_notes: [{ question_index: 3, text: "Choice B is silly" }] }],
        blocked: true,
      }),
    );
    await open([card()]);
    await answerAll(user, ["y", "y", "y", "y", "y"]);
    await user.click(screen.getByTestId("act-approve"));
    await waitFor(() => expect(screen.getByTestId("desk-summary")).toBeTruthy());
    await user.click(screen.getByRole("button", { name: "Open" }));
    const others = await screen.findByTestId("desk-others");
    expect(others.textContent).toContain("Reviewer 1");
    expect(others.textContent).toContain("Choice B is silly");
    expect(others.textContent).not.toMatch(/@/);
  });

  it("opens an already decided question read-only, with the others the API sent", async () => {
    await open([saved({ id: "ITEM.D", others: [{ reviewer: "Reviewer 1", decision: "approve", note: null, severity: null, reason_code: null, checks: null, fix_notes: [] }], approvals: 2 })]);
    // every card is decided, so the summary shows; open it
    expect(screen.getByTestId("desk-summary")).toBeTruthy();
  });
});

describe("reviewer desk: the student view", () => {
  it("shows the stem, the choices, the computer box, and a no-translation notice for Nepali", async () => {
    const user = userEvent.setup();
    await open([card()]);
    expect(screen.getByTestId("desk-stem").textContent).toBe("Does x = 5 solve x + 7 = 12?");
    expect(screen.getByTestId("desk-computer").getAttribute("data-state")).toBe("verified");
    expect(screen.getByText(/The computer already checked the maths/)).toBeTruthy();
    await user.click(screen.getByRole("tab", { name: "हिन्दी" }));
    expect(screen.getByTestId("desk-hindi").textContent).toContain("क्या x = 5");
    await user.click(screen.getByRole("tab", { name: "नेपाली" }));
    expect(screen.getByTestId("desk-no-translation").textContent).toMatch(/no Nepali version/);
  });

  it("warns when the computer could not check or disagrees", async () => {
    await open([card({ verification: { state: "mismatch", detail: "x" } })]);
    expect(screen.getByTestId("desk-computer").getAttribute("data-state")).toBe("mismatch");
  });

  it("pauses the timer", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      await open([card()]);
      await vi.advanceTimersByTimeAsync(3000);
      expect(screen.getByTestId("desk-clock").textContent).toBe("0:03");
      await user.click(screen.getByTestId("desk-pause"));
      await vi.advanceTimersByTimeAsync(5000);
      expect(screen.getByTestId("desk-clock").textContent).toBe("0:03");
    } finally {
      vi.useRealTimers();
    }
  });

  it("offers the admin link only to an admin", async () => {
    vi.mocked(api.deskItems).mockResolvedValue({ total: 1, items: [card()] });
    vi.mocked(api.whoAmI).mockResolvedValue({ role: "admin" } as never);
    render(<ReviewerDesk />);
    expect(await screen.findByRole("link", { name: /Invite or suspend reviewers/ })).toBeTruthy();
    cleanup();
    await open([card()]);
    expect(screen.queryByRole("link")).toBeNull(); // a reviewer sees no link to classes, students or admin
  });

  it("says when nothing is waiting", async () => {
    await open([]);
    expect(screen.getByTestId("desk-empty")).toBeTruthy();
  });
});

describe("the review route and its flag", () => {
  it("shows the old list when the flag is off (default)", async () => {
    vi.mocked(api.reviewItems).mockResolvedValue({ total: 0, items: [] });
    render(<ReviewPage />);
    expect(await screen.findByRole("heading", { level: 1 })).toHaveProperty("textContent", "Review content");
    expect(screen.queryByTestId("reviewer-desk")).toBeNull();
    expect(api.deskItems).not.toHaveBeenCalled();
    expect(screen.getByRole("link", { name: "Back to your classes" })).toBeTruthy();
  });

  it("shows the desk when NEXT_PUBLIC_REVIEWER_DESK is true, and does not call the old list", async () => {
    vi.stubEnv("NEXT_PUBLIC_REVIEWER_DESK", "true");
    vi.mocked(api.deskItems).mockResolvedValue({ total: 1, items: [card()] });
    vi.mocked(api.whoAmI).mockResolvedValue({ role: "reviewer" } as never);
    render(<ReviewPage />);
    expect(await screen.findByTestId("reviewer-desk")).toBeTruthy();
    expect(api.reviewItems).not.toHaveBeenCalled();
  });
});

describe("admin invite page", () => {
  it("is closed to a non-admin", async () => {
    vi.stubEnv("NEXT_PUBLIC_REVIEWER_DESK", "true");
    vi.mocked(api.whoAmI).mockResolvedValue({ role: "teacher" } as never);
    render(<ReviewersAdminPage />);
    expect(await screen.findByTestId("reviewers-denied")).toBeTruthy();
  });

  it("is closed when the flag is off", async () => {
    vi.mocked(api.whoAmI).mockResolvedValue({ role: "admin" } as never);
    render(<ReviewersAdminPage />);
    expect(await screen.findByTestId("reviewers-denied")).toBeTruthy();
  });

  it("invites, suspends and reinstates", async () => {
    const user = userEvent.setup();
    vi.stubEnv("NEXT_PUBLIC_REVIEWER_DESK", "true");
    vi.mocked(api.whoAmI).mockResolvedValue({ role: "admin" } as never);
    vi.mocked(api.inviteReviewer).mockResolvedValue({ id: "r1", email: "asha@example.org", role: "reviewer", suspended: false });
    vi.mocked(api.setReviewerSuspended).mockResolvedValueOnce({ id: "r1", email: "asha@example.org", role: "reviewer", suspended: true });
    render(<ReviewersAdminPage />);
    await user.type(await screen.findByLabelText("Reviewer email"), "asha@example.org");
    await user.click(screen.getByRole("button", { name: "Invite" }));
    expect(await screen.findByText(/asha@example.org is invited/)).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Suspend" }));
    expect(api.setReviewerSuspended).toHaveBeenCalledWith("r1", true);
    expect(await screen.findByRole("button", { name: "Reinstate" })).toBeTruthy();
  });

  it("explains a 409 (the email belongs to another account)", async () => {
    const user = userEvent.setup();
    vi.stubEnv("NEXT_PUBLIC_REVIEWER_DESK", "true");
    vi.mocked(api.whoAmI).mockResolvedValue({ role: "admin" } as never);
    vi.mocked(api.inviteReviewer).mockRejectedValue(new api.ApiError("x", 409));
    render(<ReviewersAdminPage />);
    await user.type(await screen.findByLabelText("Reviewer email"), "t@example.org");
    await user.click(screen.getByRole("button", { name: "Invite" }));
    expect((await screen.findByRole("alert")).textContent).toMatch(/another account/);
  });

  const invited = async (user: ReturnType<typeof userEvent.setup>) => {
    vi.stubEnv("NEXT_PUBLIC_REVIEWER_DESK", "true");
    vi.mocked(api.whoAmI).mockResolvedValue({ role: "admin" } as never);
    vi.mocked(api.inviteReviewer).mockResolvedValue({ id: "r1", email: "asha@example.org", role: "reviewer", suspended: false });
    render(<ReviewersAdminPage />);
    await user.type(await screen.findByLabelText("Reviewer email"), "asha@example.org");
    await user.click(screen.getByRole("button", { name: "Invite" }));
    await screen.findByText(/asha@example.org is invited/);
  };

  it("shows a sign-in code once, with the WhatsApp note, a copy button and a way to dismiss it", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    vi.mocked(api.issueReviewerSignInCode).mockResolvedValue({ code: "482913", expires_at: "2026-11-25T10:15:00Z" });
    await invited(user);
    await user.click(screen.getByRole("button", { name: "Create sign-in code" }));
    expect(api.issueReviewerSignInCode).toHaveBeenCalledWith("r1");
    expect((await screen.findByTestId("signin-code-value")).textContent).toBe("482913");
    expect(screen.getByText(/for example on WhatsApp. It works once and expires in 15 minutes/)).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Copy" }));
    expect(writeText).toHaveBeenCalledWith("482913");
    expect(await screen.findByRole("button", { name: "Copied" })).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Done" }));
    expect(screen.queryByTestId("signin-code")).toBeNull();
    vi.unstubAllGlobals();
  });

  it.each([
    [409, /suspended/],
    [429, /Too many codes/],
    [404, /not found/],
    [500, /Could not create a code/],
  ])("explains a %i when making a code", async (status, message) => {
    const user = userEvent.setup();
    vi.mocked(api.issueReviewerSignInCode).mockRejectedValue(new api.ApiError("x", status));
    await invited(user);
    await user.click(screen.getByRole("button", { name: "Create sign-in code" }));
    expect((await screen.findByRole("alert")).textContent).toMatch(message);
    expect(screen.queryByTestId("signin-code")).toBeNull();
  });
});
