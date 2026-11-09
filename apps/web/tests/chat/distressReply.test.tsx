import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const LINES = [{ id: "tele_manas", kind: "mental_health", name: "Tele-MANAS", number: "14416", hours: null, verified: true }];

vi.mock("@/components/chat/ChatProvider", () => ({
  useChatApi: () => ({
    copy: { chatFinderDistress: "Please talk to a grown-up you trust." },
    replies: [{ id: 1, kind: "distress", helplines: LINES }],
    confirmStep: vi.fn(),
    dismissReplies: vi.fn(),
  }),
}));

import { Replies } from "@/components/chat/Bubbles";

afterEach(cleanup);

describe("the on-device distress reply", () => {
  it("shows the support message and the helplines the device already holds", () => {
    render(<Replies />);
    expect(screen.getByTestId("reply-distress")).toHaveTextContent("Please talk to a grown-up you trust.");
    expect(screen.getByRole("link", { name: /Tele-MANAS/ })).toHaveAttribute("href", "tel:14416");
  });
});
