import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const push = vi.fn();
const api = vi.hoisted(() => ({
  today: vi.fn(),
  getChapters: vi.fn(),
  startSession: vi.fn(),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("@/lib/dev-auth", () => ({ ensureDevStudent: async () => {}, skipLogin: () => false }));
vi.mock("@/lib/api", () => ({ ...api, setStudentId: vi.fn(), studentId: () => "s1" }));

import TodayPage from "@/app/today/page";

const row = { student_id: "s1", display_name: "Asha", goal_minutes: 10, remaining_active_minutes: 10 };
const card = (live: boolean) => ({ id: "c", title: "C", live, status: live ? "not_started" : "coming_soon", recommended: false, skills_total: 0, skills_can_do_it: 0 });

beforeEach(() => {
  vi.clearAllMocks();
  api.today.mockResolvedValue(row);
  api.startSession.mockResolvedValue({ id: "sess" });
});
afterEach(cleanup);

describe("Start practice when the chapter is not ready", () => {
  it("says the chapter is not ready and starts nothing", async () => {
    api.getChapters.mockResolvedValue({ chapters: [card(false)] });
    render(<TodayPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Start practice" }));
    expect(await screen.findByText(/not ready yet/)).toBeInTheDocument();
    expect(api.startSession).not.toHaveBeenCalled();
    expect(push).not.toHaveBeenCalled();
  });

  it("starts a session as before when a chapter is live", async () => {
    api.getChapters.mockResolvedValue({ chapters: [card(false), card(true)] });
    render(<TodayPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Start practice" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/session/sess"));
  });
});
