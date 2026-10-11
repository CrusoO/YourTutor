import "fake-indexeddb/auto";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { canonical } from "@/lib/offline/canonical";
import { OfflinePlayer } from "@/lib/offline/player";
import { dumpLearner } from "@/lib/offline/state";
import { memoryStore, openStore } from "@/lib/offline/store";
import { type SyncReply, syncPlayer } from "@/lib/offline/sync";
import { parseAt } from "@/lib/offline/time";

const FILE = path.resolve(
  __dirname,
  "../../../../packages/shared/fixtures/offline_sync/session_1.json",
);
const data = JSON.parse(readFileSync(FILE, "utf-8"));

function core(player: OfflinePlayer) {
  const d = dumpLearner(player.state);
  return canonical({ mastery: d.mastery, ladders: d.ladders });
}

async function play(player: OfflinePlayer, clock: { now: number }, events: any[], reopen?: () => Promise<OfflinePlayer>) {
  let current = player;
  for (const [index, event] of events.entries()) {
    clock.now = parseAt(event.at);
    await current.send(event.event_type, event.payload, event.item_id, event.client_event_id);
    if (reopen && index % 7 === 3) current = await reopen();
  }
  return current;
}

describe("the offline player", () => {
  it("plays the recorded session and reaches the server's state, even through reloads", async () => {
    const store = memoryStore();
    await OfflinePlayer.savePack(store, data.pack);
    const clock = { now: parseAt(data.started_at) };
    let player = await OfflinePlayer.start(store, data.pack, () => clock.now, "session-x");
    player = await play(player, clock, data.events, () =>
      OfflinePlayer.resume(store, () => clock.now).then((p) => p!),
    );
    expect(core(player)).toBe(canonical(data.expected));
    expect(createHash("sha256").update(core(player)).digest("hex")).toBe(data.state_hash);
    expect(player.pending).toHaveLength(data.events.length);
  });

  it("keeps the queue in IndexedDB across a reopen", async () => {
    const store = await openStore("test-offline-1");
    expect(store.durable).toBe(true);
    await OfflinePlayer.savePack(store, data.pack);
    const clock = { now: parseAt(data.started_at) };
    const player = await OfflinePlayer.start(store, data.pack, () => clock.now, "s1");
    await play(player, clock, data.events.slice(0, 6));
    const again = await openStore("test-offline-1");
    const resumed = await OfflinePlayer.resume(again, () => clock.now);
    expect(resumed?.pending).toHaveLength(6);
    expect(resumed?.action?.type).toBe(data.events[5].client_action.type);
  });

  it("falls back to memory when IndexedDB is missing", async () => {
    const store = await openStore("x", null);
    expect(store.durable).toBe(false);
    await store.set("k", { a: 1 });
    expect(await store.get("k")).toEqual({ a: 1 });
    expect(await store.keys()).toEqual(["k"]);
    await store.delete("k");
    expect(await store.get("k")).toBeUndefined();
  });

  it("syncs: the server's state equals the local one and the queue empties", async () => {
    const store = memoryStore();
    await OfflinePlayer.savePack(store, data.pack);
    const clock = { now: parseAt(data.started_at) };
    const player = await play(
      await OfflinePlayer.start(store, data.pack, () => clock.now, "s2"),
      clock,
      data.events,
    );
    const seen: unknown[] = [];
    const reply = (body: any): SyncReply => ({
      session_id: "x",
      pack_hash_ok: body.pack_hash === data.pack.hash,
      applied: body.events.length,
      duplicates: 0,
      rejected: 0,
      results: body.events.map((e: any) => ({ client_event_id: e.client_event_id, status: "applied" })),
      state: { ...data.expected, cards: {} },
      state_hash: data.state_hash,
      ended: false,
    });
    const outcome = await syncPlayer(player, async (body) => {
      seen.push(body);
      return reply(body);
    });
    expect(outcome).toEqual({ ok: true, applied: data.events.length, rejected: 0, matched: true, packStale: false });
    expect(player.pending).toHaveLength(0);
    expect(player.snapshot().confirmed_hash).toBe(data.state_hash);
    expect(seen).toHaveLength(1);
  });

  it("keeps the queue when the network is down and reports a mismatch if the states differ", async () => {
    const store = memoryStore();
    await OfflinePlayer.savePack(store, data.pack);
    const clock = { now: parseAt(data.started_at) };
    const player = await play(
      await OfflinePlayer.start(store, data.pack, () => clock.now, "s3"),
      clock,
      data.events.slice(0, 8),
    );
    const down = await syncPlayer(player, async () => {
      throw new TypeError("Failed to fetch");
    });
    expect(down).toEqual({ ok: false, reason: "offline", detail: "Failed to fetch" });
    expect(player.pending).toHaveLength(8);
    const wrong = await syncPlayer(player, async (body) => ({
      session_id: "x",
      pack_hash_ok: false,
      applied: body.events.length,
      duplicates: 0,
      rejected: 0,
      results: body.events.map((e: any) => ({ client_event_id: (e as any).client_event_id, status: "applied" })),
      state: { mastery: {}, ladders: {}, cards: {} },
      state_hash: "0".repeat(64),
      ended: false,
    }));
    expect(wrong).toMatchObject({ ok: true, matched: false, packStale: true });
    expect(player.pending).toHaveLength(0);
  });

  it("sends a long queue in batches", async () => {
    const store = memoryStore();
    await OfflinePlayer.savePack(store, data.pack);
    const clock = { now: parseAt(data.started_at) };
    const player = await OfflinePlayer.start(store, data.pack, () => clock.now, "s4");
    for (let i = 0; i < 450; i++) {
      clock.now += 1000;
      await player.send("idle_nudge", {}, null);
    }
    const sizes: number[] = [];
    await syncPlayer(player, async (body) => {
      sizes.push(body.events.length);
      return {
        session_id: "x",
        pack_hash_ok: true,
        applied: body.events.length,
        duplicates: 0,
        rejected: 0,
        results: (body.events as any[]).map((e) => ({ client_event_id: e.client_event_id, status: "applied" })),
        state: { mastery: {}, ladders: {}, cards: {} },
        state_hash: "h",
        ended: false,
      };
    });
    expect(sizes).toEqual([200, 200, 50]);
  });
});
