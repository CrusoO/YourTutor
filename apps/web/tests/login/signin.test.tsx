import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import LoginPage from "@/app/login/page";
import { studentLogin, today } from "@/lib/api";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push, replace: push }), usePathname: () => "/login" }));
vi.mock("@/lib/api", async (orig) => ({
  ...(await orig<typeof import("@/lib/api")>()),
  studentLogin: vi.fn(),
  today: vi.fn(),
  setStudentId: vi.fn(),
  setLocale: vi.fn(),
}));

const failure = (status: number) => Object.assign(new Error("x"), { status });

beforeEach(() => {
  vi.mocked(today).mockResolvedValue({ student_id: "s1", display_name: "Mina" } as never);
});
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

async function openStudent() {
  render(<LoginPage />);
  await userEvent.click(screen.getByTestId("role-student"));
  return screen.getByTestId("student-form");
}

describe("role chooser", () => {
  it("asks who is signing in and shows four large cards", () => {
    render(<LoginPage />);
    expect(screen.getByText("Who is signing in?")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Sign in to Brownie" })).toBeInTheDocument();
    for (const name of [/^Student/, /^Parent or guardian/, /^Teacher/, /^Adult learner/]) {
      expect(screen.queryByRole("link", { name }) ?? screen.queryByRole("button", { name })).toBeTruthy();
    }
    expect(screen.queryByTestId("student-form")).not.toBeInTheDocument();
  });

  it("sends each non-student card to its own route", () => {
    render(<LoginPage />);
    expect(screen.getByTestId("role-guardian")).toHaveAttribute("href", "/staff/login?as=guardian");
    expect(screen.getByTestId("role-teacher")).toHaveAttribute("href", "/staff/login?as=teacher");
    expect(screen.getByTestId("role-adult")).toHaveAttribute("href", "/staff/login?as=adult");
  });

  it("keeps guest secondary, plus the legal links, the draft banner and the language switcher", () => {
    render(<LoginPage />);
    expect(screen.getByTestId("try-guest")).toHaveAttribute("href", "/start");
    expect(screen.getByTestId("legal-links")).toBeInTheDocument();
    expect(screen.getByTestId("draft-banner")).toHaveTextContent(/under legal review/i);
    expect(screen.getByRole("button", { name: "हिन्दी" })).toBeInTheDocument();
  });

  it("the Student card shows the code and PIN form, with the join and start links", async () => {
    const form = await openStudent();
    expect(form).toBeInTheDocument();
    expect(screen.getByLabelText(/family code/i)).toHaveAttribute("autocomplete", "username");
    expect(screen.getByLabelText(/^pin$/i)).toHaveAttribute("autocomplete", "current-password");
    expect(screen.getByRole("link", { name: /join a class/i })).toHaveAttribute("href", "/join");
    expect(screen.getByRole("link", { name: /i am new: start/i })).toHaveAttribute("href", "/start/child");
    await userEvent.click(screen.getByTestId("back-to-roles"));
    expect(screen.getByText("Who is signing in?")).toBeInTheDocument();
  });

  it("works from the keyboard: tab to a card and press Enter", async () => {
    render(<LoginPage />);
    const card = screen.getByTestId("role-student");
    card.focus();
    expect(card).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    expect(screen.getByTestId("student-form")).toBeInTheDocument();
  });
});

describe("student form", () => {
  it("posts rather than gets, so a PIN can never land in the URL", async () => {
    await openStudent();
    expect(screen.getByLabelText(/^pin$/i).closest("form")).toHaveAttribute("method", "post");
  });

  it("keeps the button off until the page has hydrated, and off while empty", async () => {
    await openStudent();
    const button = screen.getByRole("button", { name: /^sign in$/i });
    expect(button).toBeDisabled();
    await userEvent.type(screen.getByLabelText(/family code/i), "abcd2345");
    await userEvent.type(screen.getByLabelText(/^pin$/i), "1234");
    expect(button).toBeEnabled();
  });

  it("signs in and lands in the chat", async () => {
    await openStudent();
    await userEvent.type(screen.getByLabelText(/family code/i), " abcd2345 ");
    await userEvent.type(screen.getByLabelText(/^pin$/i), "1234");
    await userEvent.click(screen.getByRole("button", { name: /^sign in$/i }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/brownie-chat"));
    expect(studentLogin).toHaveBeenCalledWith("abcd2345", "1234");
  });

  it.each([
    [401, /did not match/i],
    [423, /paused for a while/i],
    [429, /too many tries just now/i],
    [500, /could not sign you in just now/i],
  ])("a %i is said kindly and plainly, with no codes or traces", async (status, text) => {
    vi.mocked(studentLogin).mockRejectedValue(failure(status));
    await openStudent();
    await userEvent.type(screen.getByLabelText(/family code/i), "abcd2345");
    await userEvent.type(screen.getByLabelText(/^pin$/i), "1234");
    fireEvent.submit(screen.getByLabelText(/^pin$/i).closest("form")!);
    const error = await screen.findByTestId("login-error");
    expect(error).toHaveTextContent(text);
    expect(error.textContent).not.toMatch(/\b(401|423|429|500)\b|Error|stack/);
    expect(error.closest("[aria-live]")).toBeTruthy();
    expect(studentLogin).toHaveBeenCalledTimes(1); // a lockout or rate limit is never retried
    expect(push).not.toHaveBeenCalled();
  });
});

describe("before hydration", () => {
  it("the server-rendered form already posts and has a disabled submit button", async () => {
    const { renderToString } = await import("react-dom/server");
    const { default: StudentForm } = await import("@/app/login/StudentForm");
    const html = renderToString(<StudentForm mismatch="no" />);
    expect(html).toMatch(/<form[^>]*method="post"/);
    expect(html).toMatch(/<button[^>]*disabled[^>]*type="submit"|<button[^>]*type="submit"[^>]*disabled/);
  });
});
