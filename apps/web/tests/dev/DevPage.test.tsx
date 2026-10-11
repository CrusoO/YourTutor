import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import DevPage from "@/app/dev/page";
import DevLessonsPage from "@/app/dev/lessons/page";
import { devStaffToken, listDevLessons, listDevScenarios, seedDevScenarios, setStudentId, studentLogin, today } from "@/lib/api";

const push = vi.fn();
const notFound = vi.fn(() => {
  throw new Error("NEXT_NOT_FOUND");
});

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  notFound: () => notFound(),
}));

vi.mock("@/lib/api", () => ({
  devStaffToken: vi.fn(),
  listDevScenarios: vi.fn(),
  listDevLessons: vi.fn(),
  seedDevScenarios: vi.fn(),
  studentLogin: vi.fn(),
  today: vi.fn(),
  setStudentId: vi.fn(),
  locale: () => "en",
}));

const scenarios = [
  {
    name: "new_student",
    title: "New student",
    description: "Just enrolled.",
    family_code: "DEVNEW",
    pin: "1234",
    seeded: true,
  },
  {
    name: "review_due",
    title: "Review due",
    description: "Overdue review.",
    family_code: "DEVRVW",
    pin: "1234",
    seeded: false,
  },
];

describe("/dev", () => {
  beforeEach(() => {
    vi.stubEnv("NEXT_PUBLIC_DEV_TOOLS", "true");
    vi.mocked(listDevScenarios).mockResolvedValue({ scenarios });
    vi.mocked(studentLogin).mockResolvedValue({ access_token: "t" });
    vi.mocked(today).mockResolvedValue({ student_id: "stu-1" });
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllEnvs();
    vi.clearAllMocks();
  });

  it("is a 404 when dev tools are off", () => {
    vi.stubEnv("NEXT_PUBLIC_DEV_TOOLS", "false");
    expect(() => render(<DevPage />)).toThrow("NEXT_NOT_FOUND");
    expect(() => render(<DevLessonsPage />)).toThrow("NEXT_NOT_FOUND");
    expect(listDevScenarios).not.toHaveBeenCalled();
  });

  it("lists every scenario with its family code and PIN", async () => {
    render(<DevPage />);
    expect(await screen.findByText("New student")).toBeInTheDocument();
    expect(screen.getByText("Review due")).toBeInTheDocument();
    expect(screen.getByText(/DEVNEW/)).toBeInTheDocument();
    expect(screen.getAllByText(/1234/).length).toBe(2);
    expect(screen.getByRole("link", { name: /lessons/i })).toHaveAttribute("href", "/dev/lessons");
  });

  it("says how to seed a scenario that is not in the database yet", async () => {
    render(<DevPage />);
    await screen.findByText("Review due");
    expect(screen.getByText(/not seeded/i)).toBeInTheDocument();
    expect(screen.getByText(/python -m app\.dev seed_scenarios/)).toBeInTheDocument();
  });

  // UI-1: a scenario login lands on the role home ("/"), no longer on /subjects.
  it("logs in as a scenario with one click and lands on the role home", async () => {
    render(<DevPage />);
    await userEvent.click(await screen.findByTestId("login-new_student"));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/"));
    expect(studentLogin).toHaveBeenCalledWith("DEVNEW", "1234");
    expect(setStudentId).toHaveBeenCalledWith("stu-1");
  });

  it("signs in as the preview teacher and as a scenario's parent, landing on the role home", async () => {
    vi.mocked(devStaffToken).mockResolvedValue({ token: "t", email: "e", role: "teacher" });
    render(<DevPage />);
    await userEvent.click(await screen.findByTestId("login-teacher"));
    await waitFor(() => expect(devStaffToken).toHaveBeenCalledWith("teacher", undefined));
    await userEvent.click(await screen.findByTestId("parent-new_student"));
    await waitFor(() => expect(devStaffToken).toHaveBeenCalledWith("parent", "new_student"));
    expect(push).toHaveBeenCalledWith("/");
  });

  it("shows an error when the login fails", async () => {
    vi.mocked(studentLogin).mockRejectedValue(new Error("nope"));
    render(<DevPage />);
    await userEvent.click(await screen.findByTestId("login-review_due"));
    expect(await screen.findByText(/could not log in/i)).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });

  it("explains when the API has dev tools switched off", async () => {
    vi.mocked(listDevScenarios).mockRejectedValue(new Error("404"));
    render(<DevPage />);
    expect(await screen.findByText(/DEV_TOOLS=true/)).toBeInTheDocument();
  });

  it("lessons page lists every lesson with a link to open it", async () => {
    vi.mocked(listDevLessons).mockResolvedValue({
      lessons: [
        {
          id: "LESSON.A",
          skill_id: "SK.A",
          title: "Lesson A",
          source_ref: "ref A",
          status: "draft",
          beats: ["predict", "check"],
        },
      ],
    });
    render(<DevLessonsPage />);
    const link = await screen.findByRole("link", { name: "Lesson A" });
    expect(link).toHaveAttribute("href", "/dev/lessons/LESSON.A");
    expect(screen.getByText(/predict → check/)).toBeInTheDocument();
  });

  it("lessons page explains when the API is not reachable", async () => {
    vi.mocked(listDevLessons).mockRejectedValue(new Error("404"));
    render(<DevLessonsPage />);
    expect(await screen.findByText(/DEV_TOOLS=true/)).toBeInTheDocument();
  });

  it("resets the scenarios and reloads the list", async () => {
    vi.mocked(seedDevScenarios).mockResolvedValue({ ok: true, output: "" });
    render(<DevPage />);
    await userEvent.click(await screen.findByRole("button", { name: /reset scenarios/i }));
    await waitFor(() => expect(seedDevScenarios).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(listDevScenarios).toHaveBeenCalledTimes(2));
  });

  it("shows an error when the reset fails", async () => {
    vi.mocked(seedDevScenarios).mockRejectedValue(new Error("boom"));
    render(<DevPage />);
    await userEvent.click(await screen.findByRole("button", { name: /reset scenarios/i }));
    expect(await screen.findByText(/could not reset/i)).toBeInTheDocument();
  });
});
