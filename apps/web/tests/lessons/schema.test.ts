import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { validateLesson } from "@/lib/lessons/schema";
import { pick } from "@/lib/lessons/types";

const DIR = path.resolve(__dirname, "../../../../packages/shared/fixtures/lessons");
const files = readdirSync(DIR).filter((f) => f.endsWith(".json")).sort();

describe("lesson schema: shared fixtures give the same codes as Python", () => {
  it("has valid and invalid fixtures", () => {
    expect(files.filter((f) => f.startsWith("valid_")).length).toBeGreaterThanOrEqual(2);
    expect(files.filter((f) => f.startsWith("invalid_")).length).toBeGreaterThanOrEqual(14);
  });

  for (const file of files) {
    it(file.replace(".json", ""), () => {
      const data = JSON.parse(readFileSync(path.join(DIR, file), "utf-8"));
      expect(validateLesson(data.lesson)).toEqual(data.expect_errors);
    });
  }

  it("rejects non-objects", () => {
    expect(validateLesson(null)).toEqual(["schema.invalid"]);
    expect(validateLesson("lesson")).toEqual(["schema.invalid"]);
    expect(validateLesson({})).toEqual(["schema.invalid"]);
  });
});

describe("pick", () => {
  it("falls back to English and never returns an empty string", () => {
    expect(pick({ en: "Hello", ne: "नमस्ते" }, "ne")).toBe("नमस्ते");
    expect(pick({ en: "Hello", ne: "" }, "ne")).toBe("Hello");
    expect(pick({ en: "Hello" }, "as")).toBe("Hello");
    expect(pick(null, "en")).toBe("");
  });
});
