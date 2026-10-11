import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { createEmptyCard } from "ts-fsrs";
import { fromJson } from "@/lib/offline/ladder";
import { policy } from "@/lib/offline/policy";
import { dumpAction, dumpLearner, dumpSession } from "@/lib/offline/state";
import { parseAt } from "@/lib/offline/time";
import { type CatalogItem, newLearner, newSession, type SessionState } from "@/lib/offline/types";

const DIR = path.resolve(__dirname, "../../../../packages/shared/fixtures/policy");
const files = readdirSync(DIR).filter((f) => f.endsWith(".json")).sort();
const SET_KEYS = new Set([
  "explain_back_done",
  "introduced_skills",
  "wheel_skills",
  "seen_items",
  "answered_items",
  "probe_done",
  "skill_failed",
  "stretch_skills",
  "blocked_skills",
]);

function build(data: any) {
  const session = newSession({
    now: parseAt(data.now),
    catalog: data.catalog as CatalogItem[],
    overlay_skill_ids: data.overlay,
    bkt_params: data.bkt_params,
    prerequisites: data.prerequisites,
  });
  session.session_key = "fixture-session";
  session.misconception_remedial = { ...data.misconception_remedial };
  session.misconception_text = { ...data.misconception_text };
  session.teacher_share = !!data.teacher_share;
  for (const [key, value] of Object.entries<any>(data.session_setup ?? {})) {
    (session as unknown as Record<string, unknown>)[key] = SET_KEYS.has(key) ? new Set(value) : value;
  }
  const learner = newLearner();
  for (const [skill, row] of Object.entries<any>(data.learner.mastery ?? {})) {
    learner.mastery.set(skill, { skill_id: skill, ...row });
  }
  for (const [skill, row] of Object.entries<any>(data.learner.ladders ?? {})) {
    learner.ladders.set(skill, fromJson(row));
  }
  for (const [skill, due] of Object.entries<string>(data.learner.cards ?? {})) {
    learner.cards.set(skill, createEmptyCard(new Date(due)));
  }
  return { session: session as SessionState, learner };
}

describe("policy fixtures recorded from Python", () => {
  it("has the scenarios", () => expect(files.length).toBeGreaterThanOrEqual(20));
  for (const file of files) {
    it(file, () => {
      const data = JSON.parse(readFileSync(path.join(DIR, file), "utf-8"));
      const { session, learner } = build(data);
      data.steps.forEach((step: any, index: number) => {
        session.now = parseAt(step.now);
        const event = step.event ? { ...step.event } : null;
        const action = policy(learner, session, event);
        const where = `${file} step ${index} (${event ? event.type : "start"})`;
        expect(dumpAction(action), where).toEqual(step.expect.action);
        expect(dumpSession(session), where).toEqual(step.expect.session);
        expect(dumpLearner(learner), where).toEqual(step.expect.learner);
      });
    });
  }
});
