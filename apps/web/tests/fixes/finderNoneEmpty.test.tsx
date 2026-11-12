import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { t } from "@/lib/messages";

const state: { replies: unknown[]; ctx: unknown } = { replies: [], ctx: null };
const openWorkspace = vi.fn();
vi.mock("@/components/chat/ChatProvider", () => ({
  useChatApi: () => ({
    copy: t("en"),
    replies: state.replies,
    confirmStep: vi.fn(),
    dismissReplies: vi.fn(),
    pickTopic: vi.fn(),
    mode: "learn",
    busy: false,
    ctx: state.ctx,
    openWorkspace,
  }),
}));

import { Replies } from "@/components/chat/Bubbles";

afterEach(() => {
  cleanup();
  state.ctx = null;
  openWorkspace.mockClear();
});

describe("the not-in-your-syllabus reply", () => {
  it("lists what exists when there are chapters", () => {
    state.replies = [{ id: 1, kind: "none", topics: [{ id: "c1", title: "Quadratics", chapterId: "c1", kind: "chapter" }] }];
    render(<Replies />);
    expect(screen.getByTestId("reply-none")).toHaveTextContent(/what we do have:/);
    expect(screen.getByTestId("topic-c1")).toBeInTheDocument();
  });

  it("says so plainly, with no dangling colon, when the list is empty", () => {
    state.replies = [{ id: 1, kind: "none", topics: [] }];
    render(<Replies />);
    const text = screen.getByTestId("reply-none").textContent ?? "";
    expect(text).toMatch(/no other chapters are ready/);
    expect(text).not.toMatch(/:\s*$/);
  });

  it("offers a Pick a chapter button beside the chapters", () => {
    state.replies = [{ id: 1, kind: "none", topics: [{ id: "c1", title: "Quadratics", chapterId: "c1", kind: "chapter" }] }];
    render(<Replies />);
    screen.getByTestId("none-pick-chapter").click();
    expect(openWorkspace).toHaveBeenCalledWith("/chapters", "Chapters");
  });

  it("when the class has no live chapter, says which classes and subjects exist", () => {
    state.ctx = { curricula: [{ id: "b", grades: [{ grade: 9, subjects: [{ id: "math", books: [{ id: "x" }] }] }] }] };
    state.replies = [{ id: 1, kind: "none", topics: [] }];
    render(<Replies />);
    const text = screen.getByTestId("reply-none").textContent ?? "";
    expect(text).toMatch(/no other chapters are ready/);
    expect(text).toMatch(/Right now Brownie has Class 9 Maths\./);
    expect(screen.queryByTestId("none-pick-chapter")).toBeNull();
  });
});
