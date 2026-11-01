import { describe, expect, it } from "vitest";
import { landingContent, type LandingLanguage } from "../app/brownie/content";
import {
  landingTranslationStatus,
  landingTranslations,
} from "../app/brownie/landing-translations";

function structure(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(structure);
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, child]) => [key, structure(child)]),
    );
  }
  return typeof value;
}

function textValues(value: unknown): string[] {
  if (typeof value === "string") return [value];
  if (Array.isArray(value)) return value.flatMap(textValues);
  if (value !== null && typeof value === "object") {
    return Object.values(value).flatMap(textValues);
  }
  return [];
}

describe("landing translations", () => {
  it("provides complete matching copy for every supported language", () => {
    const englishStructure = structure(landingContent);

    for (const language of ["en", "hi", "ne"] satisfies LandingLanguage[]) {
      const copy = landingTranslations[language];
      expect(structure(copy), `${language} catalog structure`).toEqual(englishStructure);
      expect(textValues(copy).every((text) => text.trim().length > 0), `${language} copy`)
        .toBe(true);
    }
  });

  it("includes the full rotating audience in all three languages", () => {
    for (const language of ["en", "hi", "ne"] satisfies LandingLanguage[]) {
      expect(landingTranslations[language].hero.audiences).toHaveLength(4);
    }

    expect(landingTranslations.en.hero.audiences).toEqual([
      "Students",
      "Teachers",
      "Professionals",
      "Everyone",
    ]);
  });

  it("keeps Hindi and Nepali explicitly marked as drafts", () => {
    expect(landingTranslationStatus).toEqual({ hi: "draft", ne: "draft" });
  });
});
