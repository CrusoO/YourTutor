import { describe, expect, it } from "vitest";
import { isPlainSentence, plainMistake } from "@/lib/plain-diagnosis";

describe("isPlainSentence", () => {
  it("accepts a short everyday sentence", () => {
    expect(isPlainSentence("You added 7 instead of taking 7 away.")).toBe(true);
  });

  it.each([
    "The inverse of subtraction is addition.",
    "Collect each Variable on one side.",
    "Treat it as an Integer first.",
    "Check the coefficients.",
    "The constant term stays.",
    "Evaluate the expression.",
    "Use the distributive law.",
    "Addition is commutative.",
  ])("rejects jargon: %s", (text) => {
    expect(isPlainSentence(text)).toBe(false);
  });

  it("rejects a long sentence, an empty one and a non-string", () => {
    expect(isPlainSentence(Array(26).fill("word").join(" "))).toBe(false);
    expect(isPlainSentence(Array(25).fill("word").join(" "))).toBe(true);
    expect(isPlainSentence("   ")).toBe(false);
    expect(isPlainSentence(undefined)).toBe(false);
    expect(isPlainSentence(42)).toBe(false);
  });
});

describe("plainMistake", () => {
  it("takes the first plain candidate and otherwise nothing", () => {
    expect(plainMistake({ description: "The inverse is wrong.", misconception_text: "You flipped the sign." })).toBe(
      "You flipped the sign.",
    );
    expect(plainMistake({ description: "The inverse is wrong." })).toBeNull();
    expect(plainMistake(undefined)).toBeNull();
  });
});
