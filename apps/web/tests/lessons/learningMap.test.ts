import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  calibration,
  clearSaved,
  loadSaved,
  rotated,
  saveLesson,
  summarise,
  type Confidence,
  type Evidence,
} from "@/lib/lessons/learning-map";

function item(id: string, right: boolean, confidence: Confidence | null, idea: string | null = null): Evidence {
  return { id, kind: "check", question: `Q ${id}`, options: ["a", "b", "c", "d"], correct: 1, right, confidence, idea };
}

describe("summarise and calibration", () => {
  it("sorts answers into right, shaky and sure-but-wrong", () => {
    const evidence = [
      item("1", true, "sure"),
      item("2", true, null),
      item("3", false, "unsure", "idea x"),
      item("4", false, null),
      item("5", false, "sure", "idea y"),
    ];
    const s = summarise(evidence);
    expect(s.right.map((e) => e.id)).toEqual(["1", "2"]);
    expect(s.shaky.map((e) => e.id)).toEqual(["3", "4"]);
    expect(s.sureButWrong.map((e) => e.id)).toEqual(["5"]);
    expect([s.sureCount, s.sureRight]).toEqual([2, 1]);
  });

  it("says nothing about calibration when the learner never said how sure they were", () => {
    expect(calibration(summarise([item("1", true, null), item("2", false, null)]))).toBe("none");
    expect(calibration(summarise([]))).toBe("none");
  });

  it("calls it good only when every sure answer was right, and overconfident when one was not", () => {
    expect(calibration(summarise([item("1", true, "sure"), item("2", false, "unsure")]))).toBe("good");
    expect(calibration(summarise([item("1", true, "sure"), item("2", false, "sure")]))).toBe("overconfident");
  });
});

describe("rotated", () => {
  it("changes the order without losing an option, and never returns the same order", () => {
    for (const options of [["a", "b"], ["a", "b", "c"], ["a", "b", "c", "d"]]) {
      const out = rotated(options);
      expect([...out].sort()).toEqual([...options].sort());
      expect(out).not.toEqual(options);
    }
    expect(rotated(["only"])).toEqual(["only"]);
    expect(rotated([])).toEqual([]);
  });

  it("does not change its input", () => {
    const options = ["a", "b", "c", "d"];
    rotated(options);
    expect(options).toEqual(["a", "b", "c", "d"]);
  });
});

describe("the device-only record", () => {
  beforeEach(() => window.localStorage.clear());
  afterEach(() => vi.restoreAllMocks());

  it("keeps a lesson's result without the question text of each item, newest first", () => {
    saveLesson("what is tunnelling", [item("1", false, "sure", "idea y")], new Date("2026-11-03T10:00:00Z"));
    saveLesson("pythagoras", [item("1", true, null)], new Date("2026-11-03T11:00:00Z"));
    const saved = loadSaved();
    expect(saved.map((s) => s.topic)).toEqual(["pythagoras", "what is tunnelling"]);
    expect(saved[1]!.items).toEqual([{ id: "1", kind: "check", right: false, confidence: "sure", idea: "idea y" }]);
    expect(JSON.stringify(saved)).not.toContain("Q 1");
  });

  it("keeps only the latest twenty and caps the topic length", () => {
    for (let i = 0; i < 25; i += 1) saveLesson(`topic ${i} ` + "x".repeat(200), [item("1", true, null)]);
    const saved = loadSaved();
    expect(saved).toHaveLength(20);
    expect(saved[0]!.topic.length).toBeLessThanOrEqual(80);
    expect(saved[0]!.topic.startsWith("topic 24")).toBe(true);
  });

  it("saves nothing for a lesson with no answers, and clears everything on request", () => {
    saveLesson("nothing answered", []);
    expect(loadSaved()).toEqual([]);
    saveLesson("something", [item("1", true, null)]);
    expect(loadSaved()).toHaveLength(1);
    clearSaved();
    expect(loadSaved()).toEqual([]);
  });

  it("survives blocked storage and corrupt data without throwing", () => {
    window.localStorage.setItem("yt.learning-map.v1", "{not json");
    expect(loadSaved()).toEqual([]);
    window.localStorage.setItem("yt.learning-map.v1", JSON.stringify({ not: "a list" }));
    expect(loadSaved()).toEqual([]);

    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "removeItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(() => saveLesson("t", [item("1", true, null)])).not.toThrow();
    expect(() => clearSaved()).not.toThrow();
  });
});
