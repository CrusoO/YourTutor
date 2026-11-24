import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  deskItems: vi.fn(),
  deskChapters: vi.fn(),
  deskToday: vi.fn(),
  decideDesk: vi.fn(),
  whoAmI: vi.fn(),
  staffToken: () => "token",
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

import ReviewerDesk from "@/components/staff/ReviewerDesk";
import * as api from "@/lib/api";

const TOUR_KEY = "reviewer-desk-tour-v1";

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
  hindi: { stem: null, options: {} },
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
    my_decision: { decision: "approve", note: null, severity: null, reason_code: null, checks: [true, true, true], fix_notes: [] },
    ...over,
  });

const GROUPS: api.DeskChapter[] = [
  { class: 10, subject: "maths", chapter: "cbse.10.maths.quad", title: "Quadratic equations", in_curriculum: true, total: 12, pending: 7 },
  { class: 10, subject: "physics", chapter: "cbse.10.physics.light", title: "Light", in_curriculum: false, total: 4, pending: 0 },
  { class: 10, subject: "physics", chapter: "cbse.10.physics.elec", title: "Electricity", in_curriculum: true, total: 5, pending: 5 },
];

const TWO = () => [card(), card({ id: "ITEM.Q2", content_hash: "h2", stem: "Second question" })];

async function open(cards: api.DeskCard[] = TWO()) {
  vi.mocked(api.deskItems).mockResolvedValue({ total: cards.length, items: cards });
  render(<ReviewerDesk />);
  await userEvent.click(await screen.findByRole("button", { name: "All chapters" }));
  await screen.findByTestId("desk-queue");
}

const keys = async (user: ReturnType<typeof userEvent.setup>, values: ("y" | "n")[]) => {
  for (const v of values) await user.keyboard(v);
};

beforeEach(() => {
  vi.clearAllMocks();
  window.localStorage.setItem(TOUR_KEY, "1");
  vi.mocked(api.whoAmI).mockResolvedValue({ role: "reviewer" } as never);
  vi.mocked(api.deskChapters).mockResolvedValue({ groups: GROUPS });
  vi.mocked(api.deskToday).mockResolvedValue({ active_seconds_today: 42 * 60, daily_cap_seconds: 12600 });
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  window.localStorage.clear();
});

describe("the three questions", () => {
  it("shows the three plain questions and the how-to strip", async () => {
    await open([card()]);
    for (const text of ["Is the question clear, and right for this class?", "Are the right answer and the steps correct?", "Are the other choices and the hints fine?"])
      expect(screen.getByText(text)).toBeTruthy();
    expect(screen.queryByTestId("check-3")).toBeNull();
    expect(screen.getByTestId("desk-howto").textContent).toMatch(/three yes or no questions/);
  });

  it("opens a plain help text per question", async () => {
    const user = userEvent.setup();
    await open([card()]);
    expect(screen.queryByTestId("check-help-2")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Help for question 3" }));
    const help = screen.getByTestId("check-help-2").textContent ?? "";
    expect(help).toMatch(/each wrong choice is there on purpose/i);
    expect(help).toMatch(/the app tells the student what mistake it thinks they made/);
    await user.click(screen.getByRole("button", { name: "Help for question 3" }));
    expect(screen.queryByTestId("check-help-2")).toBeNull();
  });

  it("has six reasons on keys 1 to 6 and ignores the old keys", async () => {
    const user = userEvent.setup();
    await open([card()]);
    await user.keyboard("n");
    await user.keyboard("{Escape}");
    const group = screen.getByRole("group", { name: "Main reason" });
    expect(within(group).getAllByRole("button")).toHaveLength(6);
    expect(within(group).getByRole("button", { name: /Wrong or doubtful answer/ })).toBeTruthy();
    await user.keyboard("9");
    expect(within(group).getAllByRole("button").some((b) => b.getAttribute("aria-pressed") === "true")).toBe(false);
    await user.keyboard("5");
    expect(within(group).getByRole("button", { name: /Too hard or too easy/ }).getAttribute("aria-pressed")).toBe("true");
  });

  it("asks how serious for Fix (Must fix or Small fix) and sets blocker by itself for Reject", async () => {
    const user = userEvent.setup();
    vi.mocked(api.decideDesk).mockResolvedValue(saved());
    await open();
    await user.keyboard("n");
    await user.type(screen.getByLabelText(/What should be fixed/), "the wording is unclear");
    await user.keyboard("{Escape}");
    await user.keyboard("1");
    expect(screen.getByRole("button", { name: /Must fix/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Small fix/ })).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Blocker/ })).toBeNull();
    await user.click(screen.getByRole("button", { name: /^Reject/ })); // no severity picked: still allowed
    await waitFor(() => expect(api.decideDesk).toHaveBeenCalledTimes(1));
    expect(vi.mocked(api.decideDesk).mock.calls[0][1]).toMatchObject({ decision: "reject", severity: "blocker", reason_code: "1", fix_notes: [{ question_index: 0, text: "the wording is unclear" }] });
  });

  it("sends Small fix as nice_to_fix against the question that needs it", async () => {
    const user = userEvent.setup();
    vi.mocked(api.decideDesk).mockResolvedValue(saved());
    await open();
    await keys(user, ["y", "y", "n"]);
    await user.type(screen.getByLabelText(/What should be fixed/), "hint two is too long");
    await user.keyboard("{Escape}");
    await user.keyboard("4");
    await user.click(screen.getByRole("button", { name: /Small fix/ }));
    await user.click(screen.getByRole("button", { name: /^Fix/ }));
    await waitFor(() => expect(api.decideDesk).toHaveBeenCalledTimes(1));
    expect(vi.mocked(api.decideDesk).mock.calls[0][1]).toMatchObject({ decision: "fix", severity: "nice_to_fix", reason_code: "4", fix_notes: [{ question_index: 2, text: "hint two is too long" }] });
  });

  it("keeps the ids under Details for the team and shows the other choices in plain words", async () => {
    await open([card({ wrong_options: [{ answer: "b", text: "No", misconceptions: ["Forgets to halve"] }, { answer: "c", text: "Maybe", misconceptions: [] }] })]);
    const details = screen.getByText("Details for the team").closest("details") as HTMLDetailsElement;
    expect(details.open).toBe(false);
    expect(details.textContent).toContain("ITEM.Q1");
    const section = screen.getByText("Other choices: what the student is told if they pick one").closest("details") as HTMLDetailsElement;
    expect(section.open).toBe(true);
    expect(section.textContent).toContain("Forgets to halve");
    expect(section.textContent).toContain("The student gets no special message for this choice.");
    expect(section.textContent?.toLowerCase()).not.toMatch(/misconception|trap|template|skill/);
  });

  it("shows the sentence the student is told under each other choice, and nothing extra without one", async () => {
    await open([
      card({
        wrong_options: [
          { answer: "b", text: "No", misconceptions: ["Forgets to halve"], explanation: "You may have multiplied by n and forgotten to divide by 2." },
          { answer: "c", text: "Maybe", misconceptions: ["Sign slip"], explanation: "" },
          { answer: "d", text: "Never", misconceptions: ["Old mistake"] },
        ],
      }),
    ]);
    const section = screen.getByText("Other choices: what the student is told if they pick one").closest("details") as HTMLDetailsElement;
    const items = section.querySelectorAll("li");
    expect(items[0].querySelector("b.block")?.textContent).toBe("Forgets to halve");
    expect(items[0].textContent).toContain("You may have multiplied by n and forgotten to divide by 2.");
    expect(items[1].querySelectorAll("span.block")).toHaveLength(0); // no sentence: no empty line
    expect(items[2].textContent).toBe("(d) NeverOld mistake");
  });

  it("asks for the next questions you have not decided, with no offset, and does not repeat a skipped one", async () => {
    const user = userEvent.setup();
    const first = [card(), card({ id: "ITEM.Q2", content_hash: "h2", stem: "Second question" })];
    const next = [card({ id: "ITEM.Q2", content_hash: "h2" }), card({ id: "ITEM.Q3", content_hash: "h3", stem: "Third question" })];
    vi.mocked(api.decideDesk).mockResolvedValue(saved());
    vi.mocked(api.deskItems).mockResolvedValueOnce({ total: 3, items: first }).mockResolvedValueOnce({ total: 2, items: next });
    render(<ReviewerDesk />);
    await user.click(await screen.findByRole("button", { name: "All chapters" }));
    await screen.findByTestId("desk-queue");
    await keys(user, ["y", "y", "y"]);
    await user.click(screen.getByTestId("act-approve")); // question 1 decided
    await user.keyboard("s"); // question 2 skipped
    await user.click(await screen.findByRole("button", { name: "Load the next batch" }));
    await waitFor(() => expect(api.deskItems).toHaveBeenCalledTimes(2));
    // one skipped question comes back from the API, so one extra is asked for; no offset argument
    expect(vi.mocked(api.deskItems).mock.calls[1]).toEqual([11, null]);
    await screen.findByText("Third question");
  });

  it("keeps the honest amber wording when the computer could not check", async () => {
    await open([card({ verification: { state: "unchecked", detail: "" } })]);
    const box = screen.getByTestId("desk-computer");
    expect(box.getAttribute("data-state")).toBe("unchecked");
    expect(box.textContent).toMatch(/could not check the maths/);
  });

  it("shows an old five-answer decision without breaking", async () => {
    await open([
      saved({
        my_decision: { decision: "fix", note: null, severity: "must_fix", reason_code: "8", checks: [true, true, true, false, true], fix_notes: [{ question_index: 3, text: "Old note text" }] },
      }),
    ]);
    await userEvent.click(await screen.findByRole("button", { name: "Open" })); // every card is decided: the summary shows
    expect((await screen.findByTestId("desk-decided")).textContent).toContain("Old note text");
  });
});

describe("undo", () => {
  async function decideFirst(user: ReturnType<typeof userEvent.setup>) {
    vi.mocked(api.decideDesk).mockResolvedValueOnce(saved());
    await keys(user, ["y", "y", "y"]);
    await user.click(screen.getByTestId("act-approve"));
    await waitFor(() => expect(screen.getByTestId("desk-stem").textContent).toBe("Second question"));
  }

  it("withdraws the last decision, reopens that question and refreshes the time", async () => {
    const user = userEvent.setup();
    await open();
    expect((screen.getByTestId("act-undo") as HTMLButtonElement).disabled).toBe(true);
    await decideFirst(user);
    const todayCalls = vi.mocked(api.deskToday).mock.calls.length;
    expect(todayCalls).toBeGreaterThan(1); // refreshed after the decision
    vi.mocked(api.decideDesk).mockResolvedValueOnce(card()); // the blind card again
    await user.keyboard("{Backspace}");
    await waitFor(() => expect(screen.getByTestId("desk-stem").textContent).toBe("Does x = 5 solve x + 7 = 12?"));
    expect(vi.mocked(api.decideDesk).mock.calls[1]).toEqual(["ITEM.Q1", { content_hash: "h1", decision: "withdraw" }]);
    expect(screen.queryByTestId("desk-decided")).toBeNull();
    expect(screen.getByTestId("desk-progress").textContent).toBe("0 of 2 done");
    expect(vi.mocked(api.deskToday).mock.calls.length).toBeGreaterThan(todayCalls);
    expect((screen.getByTestId("act-undo") as HTMLButtonElement).disabled).toBe(true);
  });

  it("shows the server's refusal in its own words and leaves the decision as it was", async () => {
    const user = userEvent.setup();
    await open();
    await decideFirst(user);
    vi.mocked(api.decideDesk).mockRejectedValueOnce(new api.ApiError(JSON.stringify({ detail: "you have no decision to withdraw" }), 409));
    await user.click(screen.getByTestId("act-undo"));
    expect((await screen.findByTestId("desk-problems")).textContent).toBe("you have no decision to withdraw");
    expect(screen.getByTestId("desk-stem").textContent).toBe("Second question");
    expect(screen.getByTestId("desk-progress").textContent).toBe("1 of 2 done");
    expect((screen.getByTestId("act-undo") as HTMLButtonElement).disabled).toBe(false);
  });

  it("falls back to a plain sentence when the refusal has no text, and never shows blame", async () => {
    const user = userEvent.setup();
    await open([card({ my_history: [{ decision: "approve", severity: null, created_at: "x", changed_after_seeing: true }] }), card({ id: "ITEM.Q2", content_hash: "h2", stem: "Second question" })]);
    await decideFirst(user);
    vi.mocked(api.decideDesk).mockRejectedValueOnce(new api.ApiError("boom", 500));
    await user.click(screen.getByTestId("act-undo"));
    expect((await screen.findByTestId("desk-problems")).textContent).toBe("Could not undo that. Try again.");
    expect(document.body.textContent).not.toMatch(/changed after|after seeing/i);
  });

  it("undoes a skip without asking the server", async () => {
    const user = userEvent.setup();
    vi.mocked(api.decideDesk).mockResolvedValueOnce(card());
    await open();
    await user.keyboard("s");
    await waitFor(() => expect(screen.getByTestId("desk-stem").textContent).toBe("Second question"));
    await user.click(screen.getByTestId("act-undo"));
    await waitFor(() => expect(screen.getByTestId("desk-stem").textContent).toBe("Does x = 5 solve x + 7 = 12?"));
    expect(api.decideDesk).toHaveBeenCalledTimes(1);
  });
});

describe("time today", () => {
  it("shows used and cap as hours and minutes", async () => {
    await open([card()]);
    await waitFor(() => expect(screen.getByTestId("desk-today").textContent).toContain("Time today"));
    expect(screen.getByTestId("desk-today").textContent).toContain("0:42 of 3:30 h");
  });

  it("is simply absent when the meter cannot be read", async () => {
    vi.mocked(api.deskToday).mockRejectedValue(new api.ApiError("x", 500));
    await open([card()]);
    expect(screen.queryByTestId("desk-today")).toBeNull();
    expect(screen.getByTestId("reviewer-desk")).toBeTruthy();
  });
});

describe("chapter picker", () => {
  it("lists only chapters with questions left, with class, subject and the count", async () => {
    render(<ReviewerDesk />);
    const picker = await screen.findByTestId("desk-picker");
    expect(within(picker).getByRole("button", { name: /Quadratic equations/ }).textContent).toMatch(/Class 10 · maths.*7 left for you/);
    expect(within(picker).getByRole("button", { name: /Electricity/ }).textContent).toMatch(/5 left for you/);
    expect(within(picker).queryByRole("button", { name: /^Light/ })).toBeNull(); // nothing left there
    expect(within(picker).getByRole("button", { name: "All chapters" })).toBeTruthy();
    expect(api.deskItems).not.toHaveBeenCalled(); // nothing is loaded until a choice
  });

  it("starts a batch of up to 10 from the chosen chapter", async () => {
    const user = userEvent.setup();
    vi.mocked(api.deskItems).mockResolvedValue({ total: 7, items: [card()] });
    render(<ReviewerDesk />);
    await user.click(await screen.findByRole("button", { name: /Quadratic equations/ }));
    await screen.findByTestId("desk-queue");
    expect(api.deskItems).toHaveBeenCalledWith(10, { class: 10, subject: "maths", chapter: "cbse.10.maths.quad" });
  });

  it("All chapters sends no chapter, and the next batch keeps the choice", async () => {
    const user = userEvent.setup();
    vi.mocked(api.decideDesk).mockResolvedValue(saved());
    vi.mocked(api.deskItems).mockResolvedValue({ total: 5, items: [card()] });
    render(<ReviewerDesk />);
    await user.click(await screen.findByRole("button", { name: "All chapters" }));
    await screen.findByTestId("desk-queue");
    expect(api.deskItems).toHaveBeenCalledWith(10, null);
    await keys(user, ["y", "y", "y"]);
    await user.click(screen.getByTestId("act-approve"));
    await user.click(await screen.findByRole("button", { name: "Load the next batch" }));
    await waitFor(() => expect(api.deskItems).toHaveBeenCalledTimes(2));
    expect(vi.mocked(api.deskItems).mock.calls[1]).toEqual([10, null]);
  });

  it("goes back to the picker with Change chapter, unless a required note is empty", async () => {
    const user = userEvent.setup();
    await open([card()]);
    await user.keyboard("n");
    await user.click(screen.getByRole("button", { name: "Change chapter" }));
    expect(screen.queryByTestId("desk-picker")).toBeNull();
    await user.type(screen.getByLabelText(/What should be fixed/), "now this is long");
    await user.keyboard("{Escape}");
    await user.click(screen.getByRole("button", { name: "Change chapter" }));
    expect(await screen.findByTestId("desk-picker")).toBeTruthy();
  });

  it("starts on everything when the chapter list cannot be read", async () => {
    vi.mocked(api.deskChapters).mockRejectedValue(new api.ApiError("x", 500));
    vi.mocked(api.deskItems).mockResolvedValue({ total: 1, items: [card()] });
    render(<ReviewerDesk />);
    expect(await screen.findByTestId("desk-queue")).toBeTruthy();
    expect(api.deskItems).toHaveBeenCalledWith(10, null);
  });

  it("says so when no chapter has questions left", async () => {
    vi.mocked(api.deskChapters).mockResolvedValue({ groups: [] });
    render(<ReviewerDesk />);
    expect(await screen.findByTestId("desk-pick-none")).toBeTruthy();
  });
});

describe("first-time tour", () => {
  const start = async () => {
    render(<ReviewerDesk />);
    await screen.findByTestId("desk-picker");
  };

  it("shows three steps and the keys once, then remembers", async () => {
    const user = userEvent.setup();
    window.localStorage.clear();
    await start();
    const tour = await screen.findByTestId("desk-tour");
    expect(tour.textContent).toMatch(/Step 1 of 3.*Read the question/);
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByTestId("desk-tour").textContent).toMatch(/Step 2 of 3.*Answer three questions/);
    await user.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getByTestId("desk-tour").textContent).toMatch(/Step 3 of 3.*Approve or Needs a fix/);
    expect(screen.getByTestId("desk-tour").textContent).toMatch(/Backspace undo/);
    await user.click(screen.getByRole("button", { name: "Start reviewing" }));
    expect(screen.queryByTestId("desk-tour")).toBeNull();
    expect(window.localStorage.getItem(TOUR_KEY)).toBe("1");
    cleanup();
    await start();
    expect(screen.queryByTestId("desk-tour")).toBeNull();
  });

  it("can be skipped, and Esc skips it too", async () => {
    const user = userEvent.setup();
    window.localStorage.clear();
    await start();
    await user.click(await screen.findByRole("button", { name: "Skip the tour" }));
    expect(screen.queryByTestId("desk-tour")).toBeNull();
    expect(window.localStorage.getItem(TOUR_KEY)).toBe("1");
    cleanup();
    window.localStorage.clear();
    await start();
    await screen.findByTestId("desk-tour");
    await user.keyboard("{Escape}");
    expect(screen.queryByTestId("desk-tour")).toBeNull();
  });

  it("still works when storage is blocked: shows, closes, never throws", async () => {
    const user = userEvent.setup();
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    await start();
    await screen.findByTestId("desk-tour");
    await user.click(screen.getByRole("button", { name: "Skip the tour" }));
    expect(screen.queryByTestId("desk-tour")).toBeNull();
    expect(screen.getByTestId("desk-picker")).toBeTruthy();
  });
});
