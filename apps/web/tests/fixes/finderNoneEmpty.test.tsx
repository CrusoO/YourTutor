import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { t } from "@/lib/messages";

const state: { replies: unknown[] } = { replies: [] };
vi.mock("@/components/chat/ChatProvider", () => ({
  useChatApi: () => ({ copy: t("en"), replies: state.replies, confirmStep: vi.fn(), dismissReplies: vi.fn(), pickTopic: vi.fn(), mode: "learn" }),
}));

import { Replies } from "@/components/chat/Bubbles";

afterEach(cleanup);

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
});
