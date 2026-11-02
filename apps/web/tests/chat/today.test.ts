import { afterEach, describe, expect, it } from "vitest";
import { activeDays, markActive, planFor, progressShare, weekDays } from "../../lib/chat/today";

afterEach(() => window.localStorage.clear());

describe("progress share", () => {
  it("is the share of skills at can-do-it or better across the live chapters", () => {
    expect(progressShare([{ skills_can_do_it: 3, skills_total: 12 }, { skills_can_do_it: 1, skills_total: 4 }])).toEqual({ done: 4, total: 16, percent: 25 });
  });
  it("is zero, not NaN, when there are no skills", () => {
    expect(progressShare([])).toEqual({ done: 0, total: 0, percent: 0 });
  });
});

describe("the daily plan (about 25 minutes)", () => {
  it("mixes due reviews with the next skill and stays near 25 minutes", () => {
    const plan = planFor({ due: 3, next: "Quadratic roots" });
    expect(plan?.items.map((i) => i.kind)).toEqual(["review", "learn"]);
    expect(plan!.minutes).toBeGreaterThanOrEqual(20);
    expect(plan!.minutes).toBeLessThanOrEqual(25);
  });
  it("caps reviews at five so one long queue does not crowd out new learning", () => {
    const plan = planFor({ due: 40, next: "Quadratic roots" });
    const review = plan!.items.find((i) => i.kind === "review")!;
    expect(review.count).toBe(5);
    expect(plan!.items.some((i) => i.kind === "learn")).toBe(true);
  });
  it("is reviews only when everything is learned, learning only when nothing is due, and null when neither", () => {
    expect(planFor({ due: 2, next: undefined })?.items.map((i) => i.kind)).toEqual(["review"]);
    expect(planFor({ due: 0, next: "Quadratic roots" })?.items.map((i) => i.kind)).toEqual(["learn"]);
    expect(planFor({ due: 0, next: undefined })).toBeNull();
  });
});

describe("days active this week (on this device only)", () => {
  // 2026-10-14 is a Wednesday.
  const wed = new Date("2026-10-14T10:00:00");
  it("week starts on Monday and has seven days", () => {
    const days = weekDays(wed);
    expect(days).toHaveLength(7);
    expect(days[0]!.getDay()).toBe(1);
    expect(days[6]!.getDay()).toBe(0);
  });
  it("marks today and reads back which days of this week were active", () => {
    markActive(new Date("2026-10-12T09:00:00"));
    markActive(wed);
    markActive(wed); // twice in a day counts once
    expect(activeDays(wed)).toEqual([true, false, true, false, false, false, false]);
  });
  it("ignores last week and survives a damaged value", () => {
    markActive(new Date("2026-10-05T09:00:00"));
    expect(activeDays(wed).some(Boolean)).toBe(false);
    window.localStorage.setItem("yt.days", "{nope");
    expect(activeDays(wed)).toEqual([false, false, false, false, false, false, false]);
  });
  it("stores only dates, nothing a student typed", () => {
    markActive(wed);
    expect(window.localStorage.getItem("yt.days")).toBe(JSON.stringify(["2026-10-14"]));
  });
});
