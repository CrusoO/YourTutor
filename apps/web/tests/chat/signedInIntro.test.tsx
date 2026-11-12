import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SignedInIntro } from "@/components/chat/SignedInIntro";
import { t } from "@/lib/messages";
const en = t("en");
import { liveSubjects } from "@/lib/chat/intro";

const openWorkspace = vi.fn();
const startMode = vi.fn();
let ctx: unknown = null;
let identity: unknown = { role: "student", name: "Mina" };
vi.mock("@/components/chat/ChatProvider", () => ({
  useChatApi: () => ({ copy: en, ctx, identity, openWorkspace, startMode }),
}));

const maths = { curricula: [{ id: "c", grades: [{ grade: 10, subjects: [{ id: "math", books: [{ id: "b", medium: null }] }] }, { grade: 9, subjects: [] }] }] };

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  ctx = null;
  identity = { role: "student", name: "Mina" };
});

describe("liveSubjects", () => {
  it("lists only what has books, never an empty list entry", () => {
    expect(liveSubjects(maths, (n) => `Class ${n}`, (id) => id)).toEqual(["Class 10 math"]);
    expect(liveSubjects(null, (n) => `Class ${n}`, (id) => id)).toEqual([]);
  });
});

describe("SignedInIntro", () => {
  it("tells a student who they are, what exists today, and offers maths chips", async () => {
    ctx = maths;
    render(<SignedInIntro role="student" hasProgress chapterPath="/chapters/c1" chapterTitle="Quadratics" topics={["Quadratics", "Polynomials"]} />);
    expect(screen.getByTestId("intro-who")).toHaveTextContent("You are signed in as Mina.");
    expect(screen.getByTestId("intro-can")).toHaveTextContent(/Quadratics, Polynomials/);
    expect(screen.getByTestId("intro-can")).toHaveTextContent(/other subjects and classes are coming/i);
    await userEvent.click(screen.getByTestId("intro-chip-start"));
    expect(openWorkspace).toHaveBeenCalledWith("/chapters/c1", "Quadratics");
    await userEvent.click(screen.getByTestId("intro-chip-revise"));
    expect(startMode).toHaveBeenCalledWith("revise");
    expect(screen.getAllByRole("button").length).toBeLessThanOrEqual(3);
  });

  it("offers no revise chip before there is progress", () => {
    ctx = maths;
    render(<SignedInIntro role="student" topics={["Quadratics"]} />);
    expect(screen.queryByTestId("intro-chip-revise")).not.toBeInTheDocument();
  });

  it("when no chapter is live for the learner it names what exists (Class 10 Maths) and offers only the chapters chip", () => {
    ctx = maths;
    render(<SignedInIntro role="student" hasProgress />);
    expect(screen.getByTestId("intro-can")).toHaveTextContent(/Nothing is ready for your class yet. For now Brownie has Class 10 Maths/);
    expect(screen.queryByTestId("intro-chip-start")).not.toBeInTheDocument();
    expect(screen.queryByTestId("intro-chip-revise")).not.toBeInTheDocument();
    expect(screen.getByTestId("intro-chip-chapters")).toBeInTheDocument();
  });

  it("says plainly when nothing exists at all, with no dangling chips", () => {
    ctx = { curricula: [] };
    render(<SignedInIntro role="student" />);
    expect(screen.getByTestId("intro-can")).toHaveTextContent(/nothing is ready/i);
    expect(screen.queryByTestId("intro-chips")).not.toBeInTheDocument();
  });

  it("teacher and guardian get role-fitting chips", async () => {
    identity = { role: "teacher" };
    const { unmount } = render(<SignedInIntro role="teacher" />);
    expect(screen.getByTestId("intro-who")).toHaveTextContent(/teacher/i);
    await userEvent.click(screen.getByTestId("intro-chip-classes"));
    expect(openWorkspace).toHaveBeenCalledWith("/teacher", expect.any(String));
    unmount();
    render(<SignedInIntro role="parent" />);
    expect(screen.getByTestId("intro-chip-child")).toBeInTheDocument();
  });
});
