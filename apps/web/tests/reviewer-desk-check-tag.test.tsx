import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  deskItems: vi.fn(),
  deskChapters: vi.fn(),
  deskToday: vi.fn(),
  whoAmI: vi.fn(),
  staffToken: () => "token",
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

import ReviewerDesk, { CheckChip } from "@/components/staff/ReviewerDesk";
import * as api from "@/lib/api";

const card = (over: Partial<api.DeskCard> = {}): api.DeskCard => ({
  id: "ITEM.T4",
  skill_ids: ["MATH.X"],
  type: "mcq",
  content_hash: "h4",
  stem: "What is the common difference?",
  answer: "a",
  answer_text: "4",
  verification: { state: "verified", detail: "" },
  wrong_options: [],
  solution_steps: [],
  hints: [],
  hindi: { stem: null, options: {} },
  approvals: null,
  approvals_needed: 2,
  blocked: null,
  notes: [],
  others: [],
  my_decision: null,
  my_history: [],
  ...over,
});

const GROUP: api.DeskChapter = {
  class: 10,
  subject: "biology",
  chapter: "heredity_and_evolution",
  title: "Heredity and evolution",
  in_curriculum: true,
  total: 6,
  pending: 6,
};

beforeEach(() => {
  vi.clearAllMocks();
  window.localStorage.setItem("reviewer-desk-tour-v1", "1");
  vi.stubEnv("NEXT_PUBLIC_REVIEWER_DESK", "true");
  vi.mocked(api.whoAmI).mockResolvedValue({ role: "reviewer" } as never);
  vi.mocked(api.deskToday).mockResolvedValue({ active_seconds_today: 0, daily_cap_seconds: 12600 });
  vi.mocked(api.deskChapters).mockResolvedValue({ groups: [GROUP] });
});
afterEach(() => {
  cleanup();
  vi.unstubAllEnvs();
  window.localStorage.clear();
});

async function open() {
  render(<ReviewerDesk />);
  await userEvent.click(await screen.findByRole("button", { name: "All chapters" }));
  await screen.findByTestId("desk-queue");
}

describe("check tag chip", () => {
  it("says a model-drafted card needs a person, and shows its diagram note", async () => {
    vi.mocked(api.deskItems).mockResolvedValue({
      total: 1,
      items: [card({ check_tag: "needs_person", check_label: "Needs a person to check", diagram_note: "A family tree of two parents." })],
    });
    await open();
    const chip = screen.getByTestId("desk-check-tag");
    expect(chip.textContent).toBe("Needs a person to check");
    expect(chip.getAttribute("data-tag")).toBe("needs_person");
    expect(screen.getByTestId("desk-diagram-note").textContent).toContain("A family tree of two parents.");
  });

  it("says a factory-checked card is machine-checked", async () => {
    vi.mocked(api.deskItems).mockResolvedValue({ total: 1, items: [card({ check_tag: "machine_checked" })] });
    await open();
    expect(screen.getByTestId("desk-check-tag").textContent).toBe("Machine-checked");
    expect(screen.queryByTestId("desk-diagram-note")).toBeNull();
  });

  it("shows nothing for an older API without the tag", async () => {
    vi.mocked(api.deskItems).mockResolvedValue({ total: 1, items: [card()] });
    await open();
    expect(screen.queryByTestId("desk-check-tag")).toBeNull();
    const { container } = render(<CheckChip />);
    expect(container.textContent).toBe("");
  });

  it("uses theme tokens for both tones, never a fixed colour", () => {
    const { container } = render(
      <>
        <CheckChip tag="machine_checked" />
        <CheckChip tag="needs_person" />
      </>,
    );
    const classes = Array.from(container.querySelectorAll("span")).map((s) => s.className).join(" ");
    expect(classes).toContain("text-success");
    expect(classes).toContain("text-warning");
    expect(classes).not.toMatch(/#[0-9a-f]{3,6}|text-(red|green|yellow)-/);
  });
});
