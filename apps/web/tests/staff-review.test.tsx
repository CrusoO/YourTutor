import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  decideItem: vi.fn(),
  reviewItems: vi.fn(),
  staffToken: () => "token",
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

import ReviewPage from "@/app/staff/review/page";
import ReviewItemCard from "@/components/staff/ReviewItemCard";
import * as api from "@/lib/api";

const card = (over: Partial<api.ReviewCard> = {}): api.ReviewCard => ({
  id: "ITEM.Q1",
  content_hash: "abc123",
  stem: "Does x = 5 solve x + 7 = 12?",
  answer: "yes",
  answer_text: "Yes",
  verification: { state: "verified", detail: "" },
  wrong_options: [{ answer: "no", text: "No", misconceptions: ["Wrong inverse"] }],
  hindi: { stem: "क्या x = 5 हल है?", options: {} },
  approvals: 1,
  approvals_needed: 2,
  blocked: false,
  notes: [],
  my_decision: null,
  ...over,
});

beforeEach(() => vi.clearAllMocks());
afterEach(cleanup);

describe("ReviewItemCard", () => {
  it("shows the answer, its check, the wrong options with labels, the Hindi text and the count", () => {
    render(<ReviewItemCard card={card()} onDecided={vi.fn()} />);
    expect(screen.getByText("Does x = 5 solve x + 7 = 12?")).toBeTruthy();
    expect(screen.getByTestId("review-verdict").getAttribute("data-state")).toBe("verified");
    expect(screen.getByText(/No: Wrong inverse/)).toBeTruthy();
    expect(screen.getByText(/क्या x = 5/)).toBeTruthy();
    expect(screen.getByTestId("review-count").textContent).toContain("1 of 2 approvals");
  });

  it("sends the approval with the content hash", async () => {
    const onDecided = vi.fn();
    vi.mocked(api.decideItem).mockResolvedValue(card({ approvals: 2 }));
    render(<ReviewItemCard card={card()} onDecided={onDecided} />);
    await userEvent.click(screen.getByRole("button", { name: "Approve" }));
    expect(api.decideItem).toHaveBeenCalledWith("ITEM.Q1", {
      content_hash: "abc123",
      decision: "approve",
      note: undefined,
    });
    await waitFor(() => expect(onDecided).toHaveBeenCalledWith(expect.objectContaining({ approvals: 2 })));
  });

  it("asks for a note before a fix or a reject, then sends it", async () => {
    vi.mocked(api.decideItem).mockResolvedValue(card({ blocked: true }));
    render(<ReviewItemCard card={card()} onDecided={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: "Fix with note" }));
    expect(screen.getByRole("alert").textContent).toBe("Write a note first.");
    expect(api.decideItem).not.toHaveBeenCalled();
    await userEvent.type(screen.getByLabelText(/Note/), "Hint 2 gives it away");
    await userEvent.click(screen.getByRole("button", { name: "Fix with note" }));
    expect(api.decideItem).toHaveBeenCalledWith("ITEM.Q1", {
      content_hash: "abc123",
      decision: "fix",
      note: "Hint 2 gives it away",
    });
  });

  it("tells the reviewer when the item changed (409)", async () => {
    vi.mocked(api.decideItem).mockRejectedValue(new api.ApiError("changed", 409));
    render(<ReviewItemCard card={card()} onDecided={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: "Approve" }));
    expect((await screen.findByRole("alert")).textContent).toContain("changed");
  });
});

describe("ReviewPage", () => {
  it("lists the pending cards", async () => {
    vi.mocked(api.reviewItems).mockResolvedValue({ total: 1, items: [card()] });
    render(<ReviewPage />);
    expect(await screen.findByTestId("review-card")).toBeTruthy();
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Review content");
  });
});
