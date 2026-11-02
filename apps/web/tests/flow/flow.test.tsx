import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ChapterPage from "@/app/chapters/[id]/page";
import ChaptersPage from "@/app/chapters/page";
import SubjectsPage from "@/app/subjects/page";
import DoneScreen from "@/components/flow/DoneScreen";
import StatusChip from "@/components/flow/StatusChip";
import { getChapterSkills, getChapters, startSession, startSkipAhead } from "@/lib/api";
import { reasonCopy, statusLabel, type DoneSummary } from "@/lib/flow";
import { t } from "@/lib/messages";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  useParams: () => ({ id: "CH.ONE" }),
}));

vi.mock("@/lib/useStudent", () => ({
  useStudent: () => ({
    student_id: "stu-1",
    display_name: "Asha",
    remaining_active_minutes: 24,
    resume: null,
  }),
}));

vi.mock("@/lib/api", () => ({
  getChapters: vi.fn(),
  getChapterSkills: vi.fn(),
  startSession: vi.fn(),
  startSkipAhead: vi.fn(),
  locale: () => "en",
}));

const copy = t("en");

const chapters = [
  { id: "CH.ONE", title: "Linear equations", live: true, status: "learning", recommended: true, skills_total: 12, skills_can_do_it: 3 },
  { id: "CH.TWO", title: "Ratios", live: true, status: "not_started", recommended: false, skills_total: 5, skills_can_do_it: 0 },
  { id: "CH.SOON", title: "Quadratic equations", live: false, status: "coming_soon", recommended: false, skills_total: 0, skills_can_do_it: 0 },
] as const;

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(getChapters).mockResolvedValue({
    student_id: "stu-1",
    subject: "math",
    chapters: chapters as never,
  });
});
afterEach(cleanup);

describe("status copy", () => {
  it.each([
    ["not_started", "Not started"],
    ["learning", "Learning"],
    ["can_do_it", "Can do it"],
    ["solid", "Solid"],
    ["review_due", "Review due"],
    ["coming_soon", "Coming soon"],
  ] as const)("says %s in plain words", (status, words) => {
    expect(statusLabel(copy, status)).toBe(words);
    render(<StatusChip status={status} copy={copy} />);
    expect(screen.getByText(words, { exact: false })).toBeInTheDocument();
  });

  it("never shows a raw end reason", () => {
    for (const reason of ["soft_cap", "hard_cap", "idle", "chapter_complete", "consent_revoked", "weird"]) {
      expect(reasonCopy(copy, reason)).not.toMatch(/_/);
    }
    expect(reasonCopy(copy, "idle")).toBe(copy.reasonIdle);
  });
});

describe("Subjects", () => {
  it("offers Maths only and links to the chapters", () => {
    render(<SubjectsPage />);
    const math = screen.getByTestId("subject-math");
    expect(math).toHaveAttribute("href", "/chapters");
    // Maths, plus the link to practise without internet (G9)
    expect(screen.getAllByRole("link")).toHaveLength(2);
    expect(screen.getByTestId("offline-link")).toHaveAttribute("href", "/offline");
    expect(screen.getByText(/Hi Asha/)).toBeInTheDocument();
    expect(screen.getByText(/24 active minutes left today/)).toBeInTheDocument();
  });
});

describe("Chapter map", () => {
  it("shows one recommended chapter, status chips and a coming-soon card that is not a link", async () => {
    render(<ChaptersPage />);
    await screen.findByText("Linear equations");
    expect(screen.getAllByText("Start here")).toHaveLength(1);
    const first = screen.getByTestId("chapter-CH.ONE");
    expect(first).toHaveAttribute("href", "/chapters/CH.ONE");
    expect(within(first).getByText("Start here")).toBeInTheDocument();
    expect(within(first).getByText(/3\/12 skills you can do/)).toBeInTheDocument();
    const soon = screen.getByTestId("chapter-CH.SOON");
    expect(soon.tagName).not.toBe("A");
    expect(soon).toHaveAttribute("aria-disabled", "true");
    expect(within(soon).getByText(/Coming soon/)).toBeInTheDocument();
  });

  it("does not lock a live chapter that is not the recommended one", async () => {
    render(<ChaptersPage />);
    await screen.findByText("Ratios");
    expect(screen.getByTestId("chapter-CH.TWO")).toHaveAttribute("href", "/chapters/CH.TWO");
  });

  it("explains a load failure", async () => {
    vi.mocked(getChapters).mockRejectedValue(new Error("x"));
    render(<ChaptersPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent(copy.loadError);
  });
});

const path = [
  { id: "S1", title: "Integers", level: 4, status: "can_do_it", unlocked: true, current: false, has_lesson: false },
  { id: "S2", title: "Two-step equations", level: 2, status: "learning", unlocked: true, current: true, has_lesson: true },
  { id: "S3", title: "Brackets", level: 0, status: "not_started", unlocked: false, current: false, has_lesson: false },
] as const;

describe("Chapter page", () => {
  beforeEach(() => {
    vi.mocked(getChapterSkills).mockResolvedValue({
      chapter: { id: "CH.ONE", title: "Linear equations", live: true, status: "learning", skills_total: 3, skills_can_do_it: 1 },
      skills: path as never,
    });
  });

  it("shows the skill path with statuses, the next skill and visual locks", async () => {
    render(<ChapterPage />);
    await screen.findByText("Two-step equations");
    expect(screen.getByTestId("skill-S2")).toHaveTextContent("Up next");
    expect(screen.getByTestId("skill-S2")).toHaveTextContent("Lesson, then practice");
    expect(screen.getByTestId("skill-S3")).toHaveAttribute("data-unlocked", "false");
    expect(screen.getByTestId("skill-S3")).toHaveTextContent("Do the one before first");
    expect(within(screen.getByTestId("skill-S1")).getByText(/Can do it/)).toBeInTheDocument();
  });

  it("starts the chapter with its id", async () => {
    vi.mocked(startSession).mockResolvedValue({ id: "sess-9" } as never);
    render(<ChapterPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Continue this chapter" }));
    expect(startSession).toHaveBeenCalledWith("practice", "stu-1", "CH.ONE");
    expect(push).toHaveBeenCalledWith("/session/sess-9");
  });

  it("offers Skip ahead on skills that are not yet Can do it, and a locked one can still be tried", async () => {
    vi.mocked(startSkipAhead).mockResolvedValue({ id: "sess-7" } as never);
    render(<ChapterPage />);
    await screen.findByText("Brackets");
    expect(within(screen.getByTestId("skill-S1")).queryByRole("button", { name: "Skip ahead" })).toBeNull();
    await userEvent.click(within(screen.getByTestId("skill-S3")).getByRole("button", { name: "Skip ahead" }));
    expect(startSkipAhead).toHaveBeenCalledWith("stu-1", "CH.ONE", "S3");
    expect(push).toHaveBeenCalledWith("/session/sess-7");
  });

  it("says so when skip ahead is not available for a skill", async () => {
    vi.mocked(startSkipAhead).mockRejectedValue(new Error('{"detail":"test_out_unavailable"}'));
    render(<ChapterPage />);
    await userEvent.click(
      within(await screen.findByTestId("skill-S2")).getByRole("button", { name: "Skip ahead" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(copy.skipAheadUnavailable);
    expect(push).not.toHaveBeenCalled();
  });
});

const summary: DoneSummary = {
  learned: [{ id: "S2", title: "Two-step equations", status: "can_do_it" }],
  practised: [{ id: "S2", title: "Two-step equations", status: "can_do_it" }],
  skills: [
    { id: "S1", title: "Integers", status: "solid" },
    { id: "S2", title: "Two-step equations", status: "can_do_it" },
    { id: "S3", title: "Brackets", status: "not_started" },
  ],
  next: { id: "S3", title: "Brackets" },
  remaining_active_minutes: 9,
  chapter: { id: "CH.ONE", title: "Linear equations", status: "learning" },
  recommended_chapter: "CH.ONE",
};

describe("Done screen", () => {
  const onKeepGoing = vi.fn();
  const onChapters = vi.fn();

  it("shows what moved forward, every skill status, what is next and the minutes left", () => {
    render(<DoneScreen copy={copy} reason="soft_cap" summary={summary} onKeepGoing={onKeepGoing} onChapters={onChapters} />);
    expect(screen.getByRole("heading", { name: "Nice work" })).toBeInTheDocument();
    expect(screen.getByText(copy.reasonSoftCap)).toBeInTheDocument();
    const learned = screen.getByRole("region", { name: copy.doneLearned });
    expect(within(learned).getByText(/Two-step equations/)).toBeInTheDocument();
    const skills = screen.getByRole("region", { name: copy.doneSkills });
    expect(within(skills).getAllByRole("listitem")).toHaveLength(3);
    expect(screen.getByText(/Brackets/, { selector: "p" })).toBeInTheDocument();
    expect(screen.getByText(/9 active minutes left today/)).toBeInTheDocument();
  });

  it("uses no streaks, ranks, scores or points", () => {
    const { container } = render(
      <DoneScreen copy={copy} reason="idle" summary={summary} onKeepGoing={onKeepGoing} onChapters={onChapters} />,
    );
    expect(container.textContent).not.toMatch(/streak|rank|score|points|leaderboard|xp/i);
  });

  it("falls back to practised skills, then to a kind line, when nothing moved forward", () => {
    const { rerender } = render(
      <DoneScreen copy={copy} reason="idle" summary={{ ...summary, learned: [] }} onKeepGoing={onKeepGoing} onChapters={onChapters} />,
    );
    expect(screen.getByRole("region", { name: copy.donePractised })).toBeInTheDocument();
    rerender(
      <DoneScreen copy={copy} reason="idle" summary={{ ...summary, learned: [], practised: [] }} onKeepGoing={onKeepGoing} onChapters={onChapters} />,
    );
    expect(screen.getByText(copy.doneNothingNew)).toBeInTheDocument();
  });

  it("keeps going to the chapter page or back to the map", async () => {
    render(<DoneScreen copy={copy} reason="soft_cap" summary={summary} onKeepGoing={onKeepGoing} onChapters={onChapters} />);
    await userEvent.click(screen.getByRole("button", { name: copy.doneContinue }));
    expect(onKeepGoing).toHaveBeenCalledWith("CH.ONE");
    await userEvent.click(screen.getByRole("button", { name: copy.doneChapters }));
    expect(onChapters).toHaveBeenCalled();
  });

  it("still works without a summary", async () => {
    render(<DoneScreen copy={copy} reason="consent_revoked" summary={undefined} onKeepGoing={onKeepGoing} onChapters={onChapters} />);
    await waitFor(() => expect(screen.getByRole("button", { name: copy.doneChapters })).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: copy.doneContinue })).toBeNull();
  });
});
