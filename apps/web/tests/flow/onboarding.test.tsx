import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import StartPage from "@/app/start/page";
import FirstRun from "@/components/flow/FirstRun";
import { getContextOptions, guestStart } from "@/lib/api";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push, replace: push }) }));
let offer: "first_run" | "warmup_reoffer" | null = "first_run";
vi.mock("@/lib/useStudent", () => ({
  useStudent: () => ({ student_id: "stu-1", display_name: "Asha", remaining_active_minutes: 20, resume: null, offer }),
}));
vi.mock("@/lib/api", async (orig) => ({
  ...(await orig<typeof import("@/lib/api")>()),
  getContextOptions: vi.fn(),
  guestStart: vi.fn(),
  answerOnboarding: vi.fn(),
  startSession: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("FirstRun", () => {
  it("offers the warm-up or the beginning, never as a test", async () => {
    const onChoose = vi.fn();
    render(<FirstRun offer="first_run" onChoose={onChoose} />);
    expect(screen.queryByText(/\btest\b|marks|score/i)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Quick warm-up to find where to start" }));
    expect(onChoose).toHaveBeenCalledWith("warmup");
    await userEvent.click(screen.getByRole("button", { name: "Start from the beginning" }));
    expect(onChoose).toHaveBeenCalledWith("start_beginning");
    expect(screen.queryByRole("button", { name: "Not now" })).not.toBeInTheDocument();
  });

  it("the re-offer has a respected Not now", async () => {
    const onChoose = vi.fn();
    render(<FirstRun offer="warmup_reoffer" onChoose={onChoose} />);
    await userEvent.click(screen.getByRole("button", { name: "Not now" }));
    expect(onChoose).toHaveBeenCalledWith("not_now");
    expect(screen.queryByRole("button", { name: "Start from the beginning" })).not.toBeInTheDocument();
  });

  it("shows nothing when there is no offer", () => {
    const { container } = render(<FirstRun offer={null} onChoose={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("StartPage", () => {
  beforeEach(() => {
    vi.mocked(getContextOptions).mockResolvedValue({
      curricula: [
        {
          id: "sample_board",
          grades: [{ grade: 9, subjects: [{ id: "math", books: [{ id: "sample_class9", medium: null }] }] }],
        },
      ],
      languages: [{ code: "en", name: "English" }],
    });
    vi.mocked(guestStart).mockResolvedValue({ student_id: "s1", display_name: "Guest" });
  });

  it("walks curriculum, grade, subject and language, then starts a guest with the device time zone", async () => {
    render(<StartPage />);
    await userEvent.selectOptions(await screen.findByLabelText("Curriculum"), "sample_board");
    await userEvent.selectOptions(screen.getByLabelText("Grade"), "9");
    await userEvent.selectOptions(screen.getByLabelText("Subject"), "math");
    await userEvent.click(screen.getByRole("button", { name: "Start" }));
    await waitFor(() => expect(guestStart).toHaveBeenCalledTimes(1));
    const body = vi.mocked(guestStart).mock.calls[0][0];
    expect(body).toMatchObject({ curriculum_id: "sample_board", grade: 9, subject: "math", home_language: "en" });
    expect(typeof body.device_timezone).toBe("string");
    expect(Object.keys(body).sort()).toEqual(
      ["curriculum_id", "device_timezone", "grade", "home_language", "subject"],
    );
    expect(push).toHaveBeenCalledWith("/subjects");
  });

  it("keeps Start off until every choice is made", async () => {
    render(<StartPage />);
    expect(await screen.findByLabelText("Curriculum")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start" })).toBeDisabled();
  });

  it("asks for nothing personal", async () => {
    render(<StartPage />);
    await screen.findByLabelText("Curriculum");
    expect(screen.queryByLabelText(/name|email|phone|school/i)).not.toBeInTheDocument();
  });
});

describe("Subjects page first run", () => {
  it("answers the offer, then starts the matching session", async () => {
    const { answerOnboarding, startSession } = await import("@/lib/api");
    vi.mocked(answerOnboarding).mockResolvedValue({ next: { session_type: "practice" } });
    vi.mocked(startSession).mockResolvedValue({ id: "sess-1" } as never);
    const { default: SubjectsPage } = await import("@/app/subjects/page");
    render(<SubjectsPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Start from the beginning" }));
    await waitFor(() => expect(answerOnboarding).toHaveBeenCalledWith("start_beginning"));
    await waitFor(() => expect(startSession).toHaveBeenCalledWith("practice", "stu-1"));
    expect(push).toHaveBeenCalledWith("/session/sess-1");
  });

  it("not now just hides the card and keeps the student on the page", async () => {
    const { answerOnboarding, startSession } = await import("@/lib/api");
    vi.mocked(answerOnboarding).mockResolvedValue({ next: { session_type: "practice" } });
    offer = "warmup_reoffer";
    const { default: SubjectsPage } = await import("@/app/subjects/page");
    render(<SubjectsPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Not now" }));
    await waitFor(() => expect(answerOnboarding).toHaveBeenCalledWith("not_now"));
    await waitFor(() => expect(screen.queryByTestId("first-run")).not.toBeInTheDocument());
    expect(startSession).not.toHaveBeenCalled();
    offer = "first_run";
  });
});
