/** Send the queued offline events to the server and take its learner state back. */

import { canonical, sha256Hex } from "./canonical";
import { dumpLearner } from "./state";
import { learnerFromPack, type PackLearner, type Pack } from "./pack";
import type { OfflinePlayer } from "./player";

export const BATCH = 200;

export type SyncBody = {
  client_session_id: string;
  started_at: string;
  pack_hash: string;
  events: unknown[];
};

export type SyncReply = {
  session_id: string;
  pack_hash_ok: boolean;
  applied: number;
  duplicates: number;
  rejected: number;
  results: { client_event_id: string; status: string; guardrail_flag?: string | null }[];
  state: PackLearner;
  state_hash: string;
  ended: boolean;
};

export type SyncOutcome =
  | { ok: true; applied: number; rejected: number; matched: boolean; packStale: boolean }
  | { ok: false; reason: "offline" | "refused"; detail: string };

/** `post` sends the body to `/sync/events` and returns the parsed reply, or throws. */
export type PostSync = (body: SyncBody) => Promise<SyncReply>;

async function localHash(player: OfflinePlayer): Promise<string> {
  const dumped = dumpLearner(player.state);
  return sha256Hex(canonical({ mastery: dumped.mastery, ladders: dumped.ladders }));
}

export async function syncPlayer(player: OfflinePlayer, post: PostSync): Promise<SyncOutcome> {
  let applied = 0;
  let rejected = 0;
  let matched = true;
  let packStale = false;
  while (player.pending.length > 0) {
    const batch = player.pending.slice(0, BATCH);
    const mine = await localHash(player);
    let reply: SyncReply;
    try {
      reply = await post({
        client_session_id: player.sessionId,
        started_at: player.snapshot().started_at,
        pack_hash: player.pack.hash,
        events: batch,
      });
    } catch (error) {
      const detail = error instanceof Error ? error.message : String(error);
      const refused = /^\{|^\[|forbidden|consent|detail/i.test(detail);
      return { ok: false, reason: refused ? "refused" : "offline", detail };
    }
    applied += reply.applied;
    rejected += reply.rejected;
    packStale = packStale || !reply.pack_hash_ok;
    const taken = reply.results.map((r) => r.client_event_id);
    const last = player.pending.length === batch.length;
    // the server's hash covers every event it has, so it is comparable once the queue is empty
    if (last) matched = matched && mine === reply.state_hash;
    const learner = learnerFromPack({ learner: reply.state } as unknown as Pack);
    await player.confirm(taken, learner, reply.state_hash);
    if (taken.length === 0) break;
  }
  return { ok: true, applied, rejected, matched, packStale };
}
