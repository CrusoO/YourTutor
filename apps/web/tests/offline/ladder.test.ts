import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { compute, type LadderEvent, summary } from "@/lib/offline/ladder";
import { parseAt } from "@/lib/offline/time";

const DIR = path.resolve(__dirname, "../../../../packages/shared/fixtures/ladder");
const files = readdirSync(DIR).filter((f) => f.endsWith(".json")).sort();

function events(raw: Record<string, unknown>[]): LadderEvent[] {
  return raw.map((row) => ({
    event_id: String(row.event_id),
    skill_id: String(row.skill_id),
    kind: String(row.kind),
    at: parseAt(String(row.at)),
    item_id: (row.item_id as string | undefined) ?? "",
    correct: (row.correct as boolean | undefined) ?? null,
    pool: (row.pool as string | undefined) ?? "practice",
    role: (row.role as string | undefined) ?? "procedure",
    structure: (row.structure as string | undefined) ?? "",
  }));
}

describe("ladder fixtures shared with Python", () => {
  it("has the fixtures", () => {
    expect(files.length).toBeGreaterThanOrEqual(14);
  });
  for (const file of files) {
    it(file, () => {
      const data = JSON.parse(readFileSync(path.join(DIR, file), "utf-8"));
      const ladders = compute(events(data.events), parseAt(data.now), data.params);
      expect(new Set(ladders.keys())).toEqual(new Set(Object.keys(data.expect)));
      for (const [skill, want] of Object.entries<Record<string, any>>(data.expect)) {
        const got = summary(ladders.get(skill)!);
        expect(got.level).toBe(want.level);
        expect(got.evidence).toEqual(want.evidence);
        for (const [key, value] of Object.entries(want.flags ?? {})) {
          expect((got.flags as Record<string, unknown>)[key]).toEqual(value);
        }
      }
    });
  }
});
