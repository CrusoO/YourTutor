import { describe, expect, it } from "vitest";
import { landingContent, robinScenes } from "../app/brownie/content";

const GENDERED = /\b(he|him|his|she|her|hers|boy|girl)\b/i;

describe("Robin scenes", () => {
  it("offers distinct settings, each about Robin", () => {
    const ids = robinScenes.scenes.map((scene) => scene.id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(ids.length).toBeGreaterThanOrEqual(3);
    for (const scene of robinScenes.scenes) {
      expect(scene.text).toContain("Robin");
      expect(scene.label.trim().length).toBeGreaterThan(0);
    }
  });

  it("never gives Robin a gender or limits Robin to students", () => {
    const english = [
      ...robinScenes.scenes.map((scene) => scene.text),
      landingContent.chapterOne.headline,
      ...landingContent.chapterOne.paragraphs,
      landingContent.chapterOne.invitation,
      landingContent.chapterOne.stats,
      ...landingContent.chapterTwo.paragraphs,
      landingContent.chapterThree.headlineStart,
      landingContent.chapterThree.headlineEnd,
      landingContent.chapterThree.body,
    ];
    for (const text of english) {
      expect(text, text).not.toMatch(GENDERED);
    }
    expect(landingContent.chapterOne.stats).not.toMatch(/student/i);
  });
});
