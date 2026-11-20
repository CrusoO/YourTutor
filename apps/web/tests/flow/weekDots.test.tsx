import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import WeekDots from "@/components/today/WeekDots";
import { weekEn } from "@/lib/today/copy";
import { weekCells } from "@/lib/today/week";
import { weekDotsEnabled } from "@/lib/flags";

// Thursday 19 Nov 2026 (local time).
const THU = new Date(2026, 10, 19, 10, 0, 0);

beforeEach(() => {
  window.localStorage.clear();
  window.sessionStorage.clear();
});
afterEach(() => {
  cleanup();
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

describe("flag", () => {
  it("is off unless exactly true", () => {
    expect(weekDotsEnabled()).toBe(false);
    vi.stubEnv("NEXT_PUBLIC_WEEK_DOTS", "1");
    expect(weekDotsEnabled()).toBe(false);
    vi.stubEnv("NEXT_PUBLIC_WEEK_DOTS", "true");
    expect(weekDotsEnabled()).toBe(true);
  });
});

describe("weekCells", () => {
  it("builds Monday to Sunday with one rest day and no failure state", () => {
    const cells = weekCells(["2026-11-16", "2026-11-19"], THU);
    expect(cells.map((c) => c.status)).toEqual(["practised", "rest", "none", "practised", "later", "later", "later"]);
  });
  it("has no rest day when every past day was practised", () => {
    const cells = weekCells(["2026-11-16", "2026-11-17", "2026-11-18"], THU);
    expect(cells.some((c) => c.status === "rest")).toBe(false);
  });
});

describe("WeekDots", () => {
  it("with the switch off shows only the switch", () => {
    render(<WeekDots learnerId="a" practisedToday={false} now={THU} />);
    expect(screen.getByRole("switch", { name: weekEn.switchLabel })).toHaveAttribute("aria-checked", "false");
    expect(screen.queryByRole("list")).toBeNull();
  });

  it("with the switch on shows seven labelled dots, a rest day and a calm line at 3 days", async () => {
    window.localStorage.setItem("yt_week_dots:a", JSON.stringify({ on: true, days: ["2026-11-16", "2026-11-18"] }));
    render(<WeekDots learnerId="a" practisedToday={true} now={THU} />);
    expect(await screen.findAllByRole("img")).toHaveLength(7);
    expect(screen.getByRole("img", { name: "Tuesday, rest day" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Thursday, practised" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Friday, not yet" })).toBeInTheDocument();
    expect(screen.getByText("3 days this week. Nice rhythm.")).toBeInTheDocument();
    expect(screen.getByText("Tuesday was a rest day.")).toBeInTheDocument();
    expect(window.localStorage.getItem("yt_week_dots:a")).toContain("2026-11-19");
  });

  it("says nothing about a quiet week", async () => {
    window.localStorage.setItem("yt_week_dots:a", JSON.stringify({ on: true, days: [] }));
    render(<WeekDots learnerId="a" practisedToday={false} now={THU} />);
    await screen.findAllByRole("img");
    expect(screen.queryByText(/Nice rhythm/)).toBeNull();
  });

  it("turns on and off by the student, and off forgets the days", async () => {
    render(<WeekDots learnerId="a" practisedToday={true} now={THU} />);
    const sw = await screen.findByRole("switch");
    await userEvent.click(sw);
    expect(await screen.findAllByRole("img")).toHaveLength(7);
    await userEvent.click(screen.getByRole("switch"));
    expect(screen.queryByRole("list")).toBeNull();
    expect(window.localStorage.getItem("yt_week_dots:a")).toBeNull();
  });

  it("records nothing while the switch is off", async () => {
    render(<WeekDots learnerId="a" practisedToday={true} now={THU} />);
    await screen.findByRole("switch");
    expect(window.localStorage.getItem("yt_week_dots:a")).toBeNull();
  });

  it("works when storage throws", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    render(<WeekDots learnerId="a" practisedToday={true} now={THU} />);
    await userEvent.click(await screen.findByRole("switch"));
    expect(await screen.findAllByRole("img")).toHaveLength(7);
  });
});

describe("copy", () => {
  it("has no loss or guilt words and no board names", () => {
    const text = JSON.stringify(weekEn).toLowerCase();
    for (const w of ["streak", "lost", "missed", "broke", "cbse", "ncert", "miss "]) expect(text).not.toContain(w);
  });
});
