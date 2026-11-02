import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { DEFAULT_NOTATION, type NotationProfile } from "@/lib/offline/math";
import { verifyResponse } from "@/lib/offline/verify";

const FILE = path.resolve(__dirname, "../../../../packages/shared/fixtures/verifier/cases.json");
const { cases } = JSON.parse(readFileSync(FILE, "utf-8"));
const PROFILES: Record<string, NotationProfile> = {
  default_ascii: DEFAULT_NOTATION,
  decimal_comma: { ...DEFAULT_NOTATION, decimal_separator: "," },
};

describe("verifier fixtures shared with Python", () => {
  it("has the cases", () => expect(cases.length).toBeGreaterThanOrEqual(40));
  for (const c of cases) {
    it(c.name, () => {
      expect(verifyResponse(c.response, c.item, PROFILES[c.profile])).toBe(c.expected);
    });
  }
});
