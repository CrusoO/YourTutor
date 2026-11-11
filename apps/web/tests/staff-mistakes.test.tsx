import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  classMistakes: vi.fn(),
  classWarmup: vi.fn(),
}));

import MistakeList from "@/components/staff/MistakeList";
import * as api from "@/lib/api";

const list = (over: Partial<api.MistakeList> = {}): api.MistakeList => ({
  state: "ok",
  window_days: 14,
  minimum_students: 5,
  mistakes: [
    {
      misconception_id: "MC.ADD",
      label: "Adds instead of subtracts",
      explanation: "Why.",
      students: 14,
      occurrences: 31,
      skill_title: "Solving pairs",
      chapter: "Linear equations",
      example: { stem: "Solve x + 2 = 5", steps: ["Subtract 2", "x = 3"] },
    },
  ],
  ...over,
});

const warm = (over: Partial<api.Warmup> = {}): api.Warmup => ({
  state: "ok",
  seed: "1",
  size: 5,
  short_by: 0,
  targets: [],
  items: [
    {
      item_id: "I1",
      skill_title: "Solving pairs",
      stem: "Solve x - 2 = 5",
      options: [{ id: "a", text: "7" }],
      answer: "7",
      steps: ["Add 2"],
      targets: { misconception_id: "MC.ADD", label: "Adds instead of subtracts" },
    },
  ],
  ...over,
});

beforeEach(() => vi.clearAllMocks());
afterEach(cleanup);

describe("MistakeList", () => {
  it("shows counts and the label, with no names", async () => {
    vi.mocked(api.classMistakes).mockResolvedValue(list());
    render(<MistakeList classId="c1" />);
    await waitFor(() => expect(screen.getByTestId("mistakes-list")).toBeTruthy());
    expect(screen.getByText("Adds instead of subtracts")).toBeTruthy();
    expect(screen.getByText(/14 students/)).toBeTruthy();
    expect(screen.getByText(/31 times/)).toBeTruthy();
  });

  it("says plainly when there are not enough students, and offers no warm-up", async () => {
    vi.mocked(api.classMistakes).mockResolvedValue(list({ state: "not_enough_students", mistakes: [] }));
    render(<MistakeList classId="c1" />);
    await waitFor(() => expect(screen.getByTestId("mistakes-not-enough")).toBeTruthy());
    expect(screen.queryByRole("button", { name: /warm-up/i })).toBeNull();
  });

  it("shows the empty state", async () => {
    vi.mocked(api.classMistakes).mockResolvedValue(list({ state: "none", mistakes: [] }));
    render(<MistakeList classId="c1" />);
    await waitFor(() => expect(screen.getByTestId("mistakes-none")).toBeTruthy());
  });

  it("builds a warm-up, each item showing its target, and says when it is short", async () => {
    vi.mocked(api.classMistakes).mockResolvedValue(list());
    vi.mocked(api.classWarmup).mockResolvedValue(warm({ short_by: 4 }));
    render(<MistakeList classId="c1" />);
    const button = await screen.findByRole("button", { name: "Build a 5-question warm-up" });
    await userEvent.click(button);
    await waitFor(() => expect(screen.getByTestId("mistakes-warmup")).toBeTruthy());
    expect(api.classWarmup).toHaveBeenCalledWith("c1", "1");
    expect(screen.getByText(/Aims at: Adds instead of subtracts/)).toBeTruthy();
    expect(screen.getByText(/fewer than 5/)).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "Build a different warm-up" }));
    await waitFor(() => expect(api.classWarmup).toHaveBeenLastCalledWith("c1", "2"));
  });

  it("says plainly when no questions exist", async () => {
    vi.mocked(api.classMistakes).mockResolvedValue(list());
    vi.mocked(api.classWarmup).mockResolvedValue(warm({ state: "no_items", items: [], short_by: 5 }));
    render(<MistakeList classId="c1" />);
    await userEvent.click(await screen.findByRole("button", { name: "Build a 5-question warm-up" }));
    await waitFor(() => expect(screen.getByText(/no approved questions/)).toBeTruthy());
  });
});
