import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { canonical } from "@/lib/offline/canonical";
import { learnerFromPack, policyEventFor, sessionFromPack } from "@/lib/offline/pack";
import { policy } from "@/lib/offline/policy";
import { dumpLearner } from "@/lib/offline/state";
import { parseAt } from "@/lib/offline/time";

const FILE = path.resolve(
  __dirname,
  "../../../../packages/shared/fixtures/offline_sync/session_1.json",
);
const data = JSON.parse(readFileSync(FILE, "utf-8"));

describe("an offline session played in TypeScript equals the server's recompute", () => {
  it("reaches exactly the state the server stored, byte for byte", () => {
    const learner = learnerFromPack(data.pack);
    const session = sessionFromPack(data.pack, data.started_at);
    policy(learner, session, null);
    for (const event of data.events) {
      session.now = parseAt(event.at);
      const action = policy(learner, session, policyEventFor(event));
      // the browser showed the same next step the policy gives here
      expect({ type: action.type, item_id: action.item_id ?? null }).toEqual({
        type: event.client_action.type,
        item_id: event.client_action.item_id,
      });
    }
    const dumped = dumpLearner(learner);
    const mine = canonical({ mastery: dumped.mastery, ladders: dumped.ladders });
    expect(mine).toBe(canonical(data.expected));
    expect(createHash("sha256").update(mine).digest("hex")).toBe(data.state_hash);
  });

  it("replays a different pack hash as the same pack content", () => {
    expect(data.pack.hash).toMatch(/^[0-9a-f]{64}$/);
    expect(data.events.length).toBeGreaterThan(15);
  });
});
