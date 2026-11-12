import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
const prefetch = vi.fn();
const api = vi.hoisted(() => ({
  getChapterSkills: vi.fn(),
  startSession: vi.fn(),
  startSkipAhead: vi.fn(),
  getChapters: vi.fn(),
  today: vi.fn(),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push, prefetch }), useParams: () => ({ id: "CH.ONE" }) }));
vi.mock("@/lib/useStudent", () => ({ useStudent: () => ({ student_id: "stu-1", display_name: "Asha", remaining_active_minutes: 20, resume: null }) }));
vi.mock("@/lib/dev-auth", () => ({ ensureDevStudent: async () => {}, skipLogin: () => false }));
vi.mock("@/lib/api", () => ({ ...api, locale: () => "en", setStudentId: vi.fn(), studentId: () => "stu-1" }));

import ChapterPage from "@/app/chapters/[id]/page";
import TodayPage from "@/app/today/page";

const body = {
  chapter: { id: "CH.ONE", title: "Linear equations", live: true, status: "learning", skills_total: 1, skills_can_do_it: 0 },
  skills: [{ id: "S2", title: "Two-step", level: 2, status: "learning", unlocked: true, current: true, has_lesson: true }],
};

beforeEach(() => {
  vi.clearAllMocks();
  api.getChapterSkills.mockResolvedValue(body);
});
afterEach(cleanup);

describe("start buttons: pending state", () => {
  it("shows Starting, is disabled and busy at once, and a double click makes one request", async () => {
    let finish: (v: unknown) => void = () => {};
    api.startSession.mockReturnValue(new Promise((resolve) => (finish = resolve)));
    render(<ChapterPage />);
    const button = await screen.findByTestId("start-chapter");
    fireEvent.click(button);
    fireEvent.click(button);
    fireEvent.click(button);
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
    expect(button).toHaveTextContent("Starting…");
    expect(screen.getByTestId("starting-status")).toHaveTextContent("Starting…");
    // the other start buttons wait too, so a second kind of start cannot run alongside
    expect(screen.getByRole("button", { name: "Skip ahead" })).toBeDisabled();
    finish({ id: "sess-1" });
    await waitFor(() => expect(push).toHaveBeenCalledWith("/session/sess-1"));
    expect(api.startSession).toHaveBeenCalledTimes(1);
    expect(push).toHaveBeenCalledTimes(1);
  });

  it("comes back with a clear error when the request fails, and can be tried again", async () => {
    api.startSession.mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce({ id: "sess-2" });
    render(<ChapterPage />);
    const button = await screen.findByTestId("start-chapter");
    fireEvent.click(button);
    expect(await screen.findByRole("alert")).toHaveTextContent("That didn't load");
    expect(button).not.toBeDisabled();
    expect(button).toHaveTextContent("Continue this chapter");
    expect(screen.getByTestId("starting-status")).toBeEmptyDOMElement();
    fireEvent.click(button);
    await waitFor(() => expect(push).toHaveBeenCalledWith("/session/sess-2"));
    expect(api.startSession).toHaveBeenCalledTimes(2);
  });

  it("skip ahead is single-flight and keeps its own error wording", async () => {
    api.startSkipAhead.mockRejectedValue(new Error("test_out_unavailable"));
    render(<ChapterPage />);
    const skip = await screen.findByRole("button", { name: "Skip ahead" });
    fireEvent.click(skip);
    fireEvent.click(skip);
    expect(await screen.findByRole("alert")).toHaveTextContent("not ready for this topic");
    expect(api.startSkipAhead).toHaveBeenCalledTimes(1);
    expect(skip).not.toBeDisabled();
  });

  it("asks the router to prefetch the session route", async () => {
    render(<ChapterPage />);
    await screen.findByTestId("start-chapter");
    expect(prefetch).toHaveBeenCalledWith("/session/prefetch");
  });

  it("Today: Start practice ignores a second click and shows Starting", async () => {
    api.today.mockResolvedValue({ student_id: "stu-1", display_name: "Asha", goal_minutes: 10, remaining_active_minutes: 10 });
    api.getChapters.mockResolvedValue({ chapters: [{ id: "c", title: "C", live: true }] });
    api.startSession.mockReturnValue(new Promise(() => {}));
    render(<TodayPage />);
    const practice = await screen.findByRole("button", { name: "Start practice" });
    fireEvent.click(practice);
    fireEvent.click(practice);
    await waitFor(() => expect(practice).toHaveTextContent("Starting…"));
    expect(practice).toBeDisabled();
    await waitFor(() => expect(api.startSession).toHaveBeenCalledTimes(1));
    expect(api.startSession).toHaveBeenCalledTimes(1);
  });
});
