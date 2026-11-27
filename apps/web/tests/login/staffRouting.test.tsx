import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import StaffLogin from "@/app/staff/login/page";
import { adultSession } from "@/lib/agreements-api";
import { requestStaffCode, verifyStaffCode, whoAmI } from "@/lib/api";

const push = vi.fn();
let search = "";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: push }),
  useSearchParams: () => new URLSearchParams(search),
}));
vi.mock("@/lib/agreements-api", async (orig) => ({
  ...(await orig<typeof import("@/lib/agreements-api")>()),
  getAuthOptions: vi.fn().mockResolvedValue({ phone_signin: false, child_profiles: true }),
  adultSession: vi.fn(),
}));
vi.mock("@/lib/api", async (orig) => ({
  ...(await orig<typeof import("@/lib/api")>()),
  requestStaffCode: vi.fn().mockResolvedValue({}),
  verifyStaffCode: vi.fn().mockResolvedValue({}),
  whoAmI: vi.fn(),
  keepTabSession: vi.fn(),
  setStudentId: vi.fn(),
}));

beforeEach(() => vi.mocked(adultSession).mockResolvedValue({ student_id: "s1", token: "t" }));
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

async function signIn(as: string, me: { role: string; agreements?: string[] }) {
  search = `as=${as}`;
  vi.mocked(whoAmI).mockResolvedValue(me as never);
  render(<StaffLogin />);
  await userEvent.type(screen.getByLabelText(/email/i), "a@b.co");
  await userEvent.click(screen.getByRole("button", { name: /send/i }));
  await userEvent.type(await screen.findByLabelText(/code/i), "123456");
  await userEvent.click(screen.getByRole("button", { name: /^sign in$|verify/i }));
}

describe("where each role lands after the one-time code", () => {
  it("guardian goes to the guardian page", async () => {
    await signIn("guardian", { role: "parent", agreements: [] });
    await waitFor(() => expect(push).toHaveBeenCalledWith("/guardian"));
  });

  it("teacher goes to the teacher page and sees the note about school-made accounts", async () => {
    await signIn("teacher", { role: "teacher", agreements: [] });
    await waitFor(() => expect(push).toHaveBeenCalledWith("/teacher"));
    expect(screen.getByTestId("teacher-note")).toHaveTextContent(/school or an admin/i);
  });

  it("an invited reviewer who has accepted the terms goes to the review screen, not a teacher or guardian page", async () => {
    await signIn("teacher", { role: "reviewer", agreements: [] });
    await waitFor(() => expect(push).toHaveBeenCalledWith("/staff/review"));
    expect(push).toHaveBeenCalledTimes(1);
  });

  it("an invited reviewer with the terms pending goes to the agreement page first", async () => {
    await signIn("teacher", { role: "reviewer", agreements: ["reviewer"] });
    await waitFor(() => expect(push).toHaveBeenCalledWith("/agreement"));
    expect(push).toHaveBeenCalledTimes(1);
  });

  it("a returning adult learner goes to the chat", async () => {
    await signIn("adult", { role: "parent", agreements: [] });
    await waitFor(() => expect(push).toHaveBeenCalledWith("/brownie-chat"));
  });

  it("an adult with no profile yet falls back to the guardian page", async () => {
    vi.mocked(adultSession).mockResolvedValue(undefined as never); // no usable profile came back
    await signIn("adult", { role: "parent", agreements: [] });
    await waitFor(() => expect(push).toHaveBeenCalled());
    expect(push).toHaveBeenCalledWith("/guardian");
  });

  it.each(["guardian", "teacher", "adult"])("a pending agreement comes first for %s", async (as) => {
    await signIn(as, { role: as === "teacher" ? "teacher" : "parent", agreements: ["guardian"] });
    await waitFor(() => expect(push).toHaveBeenCalledWith("/agreement"));
    expect(push).toHaveBeenCalledTimes(1);
  });
});

describe("an admin-issued code (reviewer desk on)", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("lets a reviewer enter the code without asking for an email, then lands on the review screen", async () => {
    vi.stubEnv("NEXT_PUBLIC_REVIEWER_DESK", "true");
    search = "";
    vi.mocked(whoAmI).mockResolvedValue({ role: "reviewer", agreements: [] } as never);
    render(<StaffLogin />);
    await userEvent.type(screen.getByLabelText(/email/i), "asha@example.org");
    await userEvent.click(screen.getByTestId("have-code"));
    await userEvent.type(await screen.findByLabelText(/code/i), "482913");
    await userEvent.click(screen.getByRole("button", { name: /^sign in$|verify/i }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/staff/review"));
    expect(requestStaffCode).not.toHaveBeenCalled();
    expect(verifyStaffCode).toHaveBeenCalledWith({ email: "asha@example.org" }, "482913");
  });

  it("sends the admin to the review screen, not the teacher page (a reviewers-only site closes that page)", async () => {
    vi.stubEnv("NEXT_PUBLIC_REVIEWER_DESK", "true");
    search = "";
    vi.mocked(whoAmI).mockResolvedValue({ role: "admin", agreements: [] } as never);
    render(<StaffLogin />);
    await userEvent.type(screen.getByLabelText(/email/i), "admin@example.org");
    await userEvent.click(screen.getByTestId("have-code"));
    await userEvent.type(await screen.findByLabelText(/code/i), "482913");
    await userEvent.click(screen.getByRole("button", { name: /^sign in$|verify/i }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/staff/review"));
    expect(push).not.toHaveBeenCalledWith("/teacher");
    expect(push).toHaveBeenCalledTimes(1);
  });

  it("keeps the admin on the teacher page when the desk is off", async () => {
    search = "as=teacher";
    vi.mocked(whoAmI).mockResolvedValue({ role: "admin", agreements: [] } as never);
    render(<StaffLogin />);
    await userEvent.type(screen.getByLabelText(/email/i), "admin@example.org");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));
    await userEvent.type(await screen.findByLabelText(/code/i), "123456");
    await userEvent.click(screen.getByRole("button", { name: /^sign in$|verify/i }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/teacher"));
  });

  it("does not show the option with the desk off", () => {
    search = "";
    render(<StaffLogin />);
    expect(screen.queryByTestId("have-code")).toBeNull();
  });
});
