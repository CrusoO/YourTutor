import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  deskItems: vi.fn(),
  deskChapters: vi.fn(),
  deskToday: vi.fn(),
  deskTemplateSummary: vi.fn(),
  listReviewers: vi.fn(),
  whoAmI: vi.fn(),
  staffToken: () => "token",
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

import ReviewersAdminPage from "@/app/staff/review/reviewers/page";
import ReviewerDesk from "@/components/staff/ReviewerDesk";
import * as api from "@/lib/api";

const card = (over: Partial<api.DeskCard> = {}): api.DeskCard => ({
  id: "ITEM.T4",
  skill_ids: ["MATH.X"],
  type: "mcq",
  content_hash: "h4",
  stem: "What is the common difference?",
  answer: "a",
  answer_text: "4",
  verification: { state: "verified", detail: "" },
  wrong_options: [],
  solution_steps: [],
  hints: [],
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

const GROUP: api.DeskChapter = {
  class: 10,
  subject: "maths",
  chapter: "cbse.10.maths.ap",
  title: "Arithmetic progressions",
  in_curriculum: true,
  total: 40,
  pending: 9,
  templates_pending: 3,
};

beforeEach(() => {
  vi.clearAllMocks();
  window.localStorage.setItem("reviewer-desk-tour-v1", "1");
  vi.stubEnv("NEXT_PUBLIC_REVIEWER_DESK", "true");
  vi.mocked(api.whoAmI).mockResolvedValue({ role: "reviewer" } as never);
  vi.mocked(api.deskToday).mockResolvedValue({ active_seconds_today: 0, daily_cap_seconds: 12600 });
  vi.mocked(api.listReviewers).mockResolvedValue({ reviewers: [] });
});
afterEach(() => {
  cleanup();
  vi.unstubAllEnvs();
  window.localStorage.clear();
});

describe("template approval on the reviewer desk", () => {
  it("says which sample the card is", async () => {
    vi.mocked(api.deskChapters).mockResolvedValue({ groups: [GROUP], template_mode: true });
    vi.mocked(api.deskItems).mockResolvedValue({
      total: 1,
      items: [card({ template: { template_id: "TPL.C10.AP", sample_index: 2, sample_count: 3, questions: 40 } })],
    });
    render(<ReviewerDesk />);
    await userEvent.click(await screen.findByRole("button", { name: "All chapters" }));
    expect((await screen.findByTestId("desk-sample")).textContent).toBe("Sample 2 of 3 for this question type");
  });

  it("shows no sample line for a card that is not a sample, or with the switch off", async () => {
    vi.mocked(api.deskChapters).mockResolvedValue({ groups: [{ ...GROUP, templates_pending: undefined }] });
    vi.mocked(api.deskItems).mockResolvedValue({ total: 1, items: [card(), card({ id: "ITEM.X", template: null })] });
    render(<ReviewerDesk />);
    await userEvent.click(await screen.findByRole("button", { name: "All chapters" }));
    await screen.findByTestId("desk-queue");
    expect(screen.queryByTestId("desk-sample")).toBeNull();
  });

  it("counts question types in the chapter picker", async () => {
    vi.mocked(api.deskChapters).mockResolvedValue({ groups: [GROUP], template_mode: true });
    render(<ReviewerDesk />);
    const picker = await screen.findByTestId("desk-picker");
    expect(picker.textContent).toContain("3 question types left for you");
    expect(picker.textContent).toContain("9 left for you");
  });

  it("keeps the old picker line when template approval is off", async () => {
    vi.mocked(api.deskChapters).mockResolvedValue({ groups: [{ ...GROUP, templates_pending: undefined }] });
    render(<ReviewerDesk />);
    const picker = await screen.findByTestId("desk-picker");
    expect(picker.textContent).not.toContain("question type");
    expect(picker.textContent).toContain("9 left for you");
  });
});

describe("admin question types summary", () => {
  const SUMMARY: api.DeskTemplateSummary = {
    totals: { in_review: 4, ready: 2, blocked: 1, escalated: 1, total: 8 },
    chapters: [],
    blocked: [
      { template_id: "TPL.C10.AP", template_hash: "h", generator_version: "factory-2", state: "escalated", chapter: "c", questions: 12, samples: ["a", "b", "c"] },
    ],
  };

  it("lists counts by state and the blocked or escalated types", async () => {
    vi.mocked(api.whoAmI).mockResolvedValue({ role: "admin" } as never);
    vi.mocked(api.deskTemplateSummary).mockResolvedValue(SUMMARY);
    render(<ReviewersAdminPage />);
    expect((await screen.findByTestId("types-totals")).textContent).toBe("2 ready, 4 in review, 1 blocked, 1 escalated");
    expect(screen.getByTestId("types-flagged").textContent).toContain("TPL.C10.AP: escalated, 12 questions");
  });

  it("shows nothing when the summary is not available (switch off)", async () => {
    vi.mocked(api.whoAmI).mockResolvedValue({ role: "admin" } as never);
    vi.mocked(api.deskTemplateSummary).mockRejectedValue(new Error("404"));
    render(<ReviewersAdminPage />);
    await screen.findByTestId("reviewers-admin");
    expect(screen.queryByTestId("types-summary")).toBeNull();
  });
});
