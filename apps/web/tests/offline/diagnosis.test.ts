import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { classify } from "@/lib/offline/diagnosis";
import { newLadder } from "@/lib/offline/ladder";
import { makeItem, newLearner, newSession } from "@/lib/offline/types";

const FILE = path.resolve(__dirname, "../../../../packages/shared/fixtures/diagnosis/classify.json");
const DATA = JSON.parse(readFileSync(FILE, "utf-8"));

function build(ctx: Record<string, any>) {
  const spec = DATA.base_item;
  const item = makeItem({
    id: "ITEM.DX",
    skill_ids: [spec.skill],
    answer_sympy: spec.answer,
    accept: [spec.answer],
    misconception_rules: spec.misconception_rules,
    slip_patterns: spec.slip_patterns ?? [],
    prereq_signatures: spec.prereq_signatures ?? [],
    intermediate_values: spec.intermediate_values ?? [],
    min_plausible_ms: spec.min_plausible_ms ?? null,
  });
  const learner = newLearner();
  const ladder = newLadder(spec.skill);
  ladder.achieved = Array.from({ length: ctx.ladder_level }, (_, i) => i + 1);
  learner.ladders.set(spec.skill, ladder);
  const session = newSession({
    now: Date.UTC(2026, 9, 8),
    catalog: [item],
    overlay_skill_ids: [spec.skill],
    bkt_params: {},
    prerequisites: { [spec.skill]: ctx.prerequisites },
    current_item_id: item.id,
    current_skill: spec.skill,
  });
  session.misconception_remedial = { ...ctx.remedial };
  session.fast_streak = ctx.fast_streak;
  session.help_without_attempt = ctx.help_without_attempt;
  session.last_wrong_item_id = ctx.first_attempt ? null : item.id;
  return { item, learner, session };
}

describe("diagnosis fixtures shared with Python", () => {
  for (const c of DATA.cases) {
    it(c.name, () => {
      const { item, learner, session } = build({ ...DATA.base_context, ...(c.context ?? {}) });
      const got = classify(item, c.response, c.correct ?? false, learner, session);
      expect(got.class).toBe(c.expected.class);
      if ("detail" in c.expected) expect(got.detail).toBe(c.expected.detail);
    });
  }
});
