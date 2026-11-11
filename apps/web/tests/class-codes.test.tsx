import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  joinClass: vi.fn(),
  myClasses: vi.fn(),
  leaveClass: vi.fn(),
  classRequests: vi.fn(),
  decideClassRequest: vi.fn(),
  classCodeStatus: vi.fn(),
  joinRequests: vi.fn(),
  makeClassCode: vi.fn(),
  disableClassCode: vi.fn(),
}));

import ClassCodePanel from "@/components/staff/ClassCodePanel";
import ClassRequests from "@/components/staff/ClassRequests";
import JoinPage from "@/app/join/page";
import * as api from "@/lib/api";

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.myClasses).mockResolvedValue({ classes: [] });
});
afterEach(cleanup);

describe("join box", () => {
  it("has a labelled code field and says a guardian must agree when the join is pending", async () => {
    vi.mocked(api.joinClass).mockResolvedValue({ class_id: "c1", class_name: "10A", status: "pending" });
    render(<JoinPage />);
    const box = screen.getByLabelText("Class code");
    await userEvent.type(box, "abcd-2345");
    await userEvent.click(screen.getByRole("button", { name: "Join" }));
    await waitFor(() =>
      expect(screen.getByTestId("join-message").textContent).toBe(
        "Your guardian needs to say yes before your teacher can see your progress.",
      ),
    );
    expect(api.joinClass).toHaveBeenCalledWith("abcd-2345", "");
  });

  it("gives one plain message for a wrong code and does not say why", async () => {
    vi.mocked(api.joinClass).mockRejectedValue(new api.JoinError("bad_code"));
    render(<JoinPage />);
    await userEvent.type(screen.getByLabelText("Class code"), "zzzz-zzzz");
    await userEvent.click(screen.getByRole("button", { name: "Join" }));
    await waitFor(() =>
      expect(screen.getByTestId("join-message").textContent).toBe(
        "That code did not work. Check it with your teacher.",
      ),
    );
  });

  it("keeps the button off until there is a code and lets a student leave", async () => {
    vi.mocked(api.myClasses).mockResolvedValue({ classes: [{ class_id: "c1", name: "10A", status: "pending" }] });
    vi.mocked(api.leaveClass).mockResolvedValue({});
    render(<JoinPage />);
    expect((screen.getByRole("button", { name: "Join" }) as HTMLButtonElement).disabled).toBe(true);
    await userEvent.click(await screen.findByRole("button", { name: "Leave" }));
    expect(api.leaveClass).toHaveBeenCalledWith("c1");
  });
});

describe("guardian class request", () => {
  const row = {
    student_id: "s1",
    student_name: "Riya",
    class_id: "c1",
    class_name: "10A",
    teacher: "t@example.com",
    requested_at: null,
  };

  it("shows class and teacher and accepts", async () => {
    vi.mocked(api.classRequests).mockResolvedValue({ requests: [row] });
    vi.mocked(api.decideClassRequest).mockResolvedValue({});
    render(<ClassRequests />);
    expect((await screen.findByTestId("guardian-class-requests")).textContent).toContain(
      "Riya asked to join 10A, taught by t@example.com",
    );
    await userEvent.click(screen.getByRole("button", { name: "Yes, share" }));
    expect(api.decideClassRequest).toHaveBeenCalledWith("c1", "s1", "accept");
    await waitFor(() => expect(screen.queryByTestId("guardian-class-requests")).toBeNull());
  });

  it("declines", async () => {
    vi.mocked(api.classRequests).mockResolvedValue({ requests: [row] });
    vi.mocked(api.decideClassRequest).mockResolvedValue({});
    render(<ClassRequests />);
    await userEvent.click(await screen.findByRole("button", { name: "No, do not share" }));
    expect(api.decideClassRequest).toHaveBeenCalledWith("c1", "s1", "decline");
  });

  it("renders nothing when there is no request", async () => {
    vi.mocked(api.classRequests).mockResolvedValue({ requests: [] });
    const { container } = render(<ClassRequests />);
    await waitFor(() => expect(api.classRequests).toHaveBeenCalled());
    expect(container.textContent).toBe("");
  });
});

describe("teacher class code panel", () => {
  it("shows the new code once and only labels for waiting students", async () => {
    vi.mocked(api.classCodeStatus).mockResolvedValue({
      enabled: true,
      expired: false,
      expires_at: null,
      pending_count: 1,
    });
    vi.mocked(api.joinRequests).mockResolvedValue({ requests: [{ label: "Student 1" }], count: 1 });
    vi.mocked(api.makeClassCode).mockResolvedValue({ code: "ABCD-2345", expires_at: null });
    render(<ClassCodePanel classId="c1" />);
    expect((await screen.findByTestId("classcode-requests")).textContent).toBe("Student 1");
    await userEvent.click(screen.getByRole("button", { name: "Make a new code" }));
    expect((await screen.findByTestId("classcode-value")).textContent).toBe("ABCD-2345");
    expect(api.makeClassCode).toHaveBeenCalledWith("c1", 30);
  });

  it("can turn joining off", async () => {
    vi.mocked(api.classCodeStatus).mockResolvedValue({
      enabled: true,
      expired: false,
      expires_at: null,
      pending_count: 0,
    });
    vi.mocked(api.joinRequests).mockResolvedValue({ requests: [], count: 0 });
    vi.mocked(api.disableClassCode).mockResolvedValue({});
    render(<ClassCodePanel classId="c1" />);
    await userEvent.click(await screen.findByRole("button", { name: "Turn joining off" }));
    expect(api.disableClassCode).toHaveBeenCalledWith("c1");
  });
});
