/**
 * The offline player: runs a practice session from a downloaded pack with the same policy the
 * server runs, keeps every event it sends itself in a queue, and saves after each step so a
 * reload or a dead battery loses nothing. `sync.ts` sends the queue when the network is back.
 */

import type { Card } from "ts-fsrs";
import { fromJson, toJson } from "./ladder";
import { learnerFromPack, type Pack, policyEventFor, sessionFromPack, type SyncEvent } from "./pack";
import { policy } from "./policy";
import { isoformat } from "./time";
import type { KeyValueStore } from "./store";
import type { Action, LearnerState, PolicyEvent, SessionState } from "./types";

const PACK_KEY = "pack";
const SESSION_KEY = "session";

export type QueuedEvent = SyncEvent & { client_action: { type: string; item_id: string | null } };

type SetKey =
  | "explain_back_done"
  | "introduced_skills"
  | "wheel_skills"
  | "seen_items"
  | "answered_items"
  | "probe_done"
  | "skill_failed"
  | "stretch_skills"
  | "blocked_skills";
const SET_KEYS: SetKey[] = [
  "explain_back_done",
  "introduced_skills",
  "wheel_skills",
  "seen_items",
  "answered_items",
  "probe_done",
  "skill_failed",
  "stretch_skills",
  "blocked_skills",
];
const DROPPED = ["catalog", "overlay_skill_ids", "bkt_params", "prerequisites", "bkt_memory"];

export type StoredSession = {
  client_session_id: string;
  started_at: string;
  pack_hash: string;
  state: Record<string, unknown>;
  memory: {
    bkt_done: string[];
    hinted: string[];
    first_wrong: string[];
    warmup_skills: string[];
    session_unhinted: Record<string, Record<string, [number, number]>>;
  };
  learner: ReturnType<typeof serializeLearner>;
  events: QueuedEvent[];
  action: Action | null;
  /** state hash the server last confirmed, once a sync has gone through */
  confirmed_hash: string | null;
};

export function serializeLearner(learner: LearnerState) {
  return {
    mastery: Object.fromEntries(learner.mastery),
    ladders: Object.fromEntries([...learner.ladders].map(([k, v]) => [k, toJson(v)])),
    cards: Object.fromEntries(
      [...learner.cards].map(([k, c]) => [
        k,
        {
          ...c,
          due: c.due.toISOString(),
          last_review: c.last_review ? c.last_review.toISOString() : null,
        },
      ]),
    ),
  };
}

export function deserializeLearner(data: ReturnType<typeof serializeLearner>): LearnerState {
  return {
    mastery: new Map(Object.entries(data.mastery)),
    ladders: new Map(Object.entries(data.ladders).map(([k, v]) => [k, fromJson(v)])),
    cards: new Map(
      Object.entries(data.cards).map(([k, c]) => [
        k,
        {
          ...c,
          due: new Date(c.due),
          last_review: c.last_review ? new Date(c.last_review) : undefined,
        } as Card,
      ]),
    ),
  };
}

function serializeSession(state: SessionState): Pick<StoredSession, "state" | "memory"> {
  const plain: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(state)) {
    if (DROPPED.includes(key)) continue;
    plain[key] = SET_KEYS.includes(key as SetKey) ? [...(value as Set<string>)] : value;
  }
  const memory = state.bkt_memory;
  const unhinted: Record<string, Record<string, [number, number]>> = {};
  for (const [sid, skills] of memory.session_unhinted) unhinted[sid] = Object.fromEntries(skills);
  return {
    state: plain,
    memory: {
      bkt_done: [...memory.bkt_done],
      hinted: [...memory.hinted],
      first_wrong: [...memory.first_wrong],
      warmup_skills: [...memory.warmup_skills],
      session_unhinted: unhinted,
    },
  };
}

function restoreSession(pack: Pack, stored: StoredSession): SessionState {
  const base = sessionFromPack(pack, stored.started_at, stored.client_session_id);
  const merged = base as unknown as Record<string, unknown>;
  for (const [key, value] of Object.entries(stored.state)) {
    merged[key] = SET_KEYS.includes(key as SetKey) ? new Set(value as string[]) : value;
  }
  base.bkt_memory = {
    bkt_done: new Set(stored.memory.bkt_done),
    hinted: new Set(stored.memory.hinted),
    first_wrong: new Set(stored.memory.first_wrong),
    warmup_skills: new Set(stored.memory.warmup_skills),
    session_unhinted: new Map(
      Object.entries(stored.memory.session_unhinted).map(([sid, skills]) => [
        sid,
        new Map(Object.entries(skills)),
      ]),
    ),
  };
  return base;
}

export type Clock = () => number;

export class OfflinePlayer {
  private constructor(
    private readonly store: KeyValueStore,
    readonly pack: Pack,
    private stored: StoredSession,
    private session: SessionState,
    private learner: LearnerState,
    private readonly clock: Clock,
  ) {}

  get action(): Action | null {
    return this.stored.action;
  }
  get pending(): QueuedEvent[] {
    return this.stored.events;
  }
  get sessionId(): string {
    return this.stored.client_session_id;
  }
  get ended(): boolean {
    return this.session.phase === "ended";
  }
  get state(): LearnerState {
    return this.learner;
  }
  snapshot(): StoredSession {
    return this.stored;
  }

  /** Download-time: keep a pack for later. */
  static async savePack(store: KeyValueStore, pack: Pack): Promise<void> {
    await store.set(PACK_KEY, pack);
  }

  static async loadPack(store: KeyValueStore): Promise<Pack | undefined> {
    return store.get<Pack>(PACK_KEY);
  }

  /** Start a new session from the saved pack and show its first step. */
  static async start(
    store: KeyValueStore,
    pack: Pack,
    clock: Clock = Date.now,
    id: string = crypto.randomUUID(),
  ): Promise<OfflinePlayer> {
    const started = isoformat(clock());
    const session = sessionFromPack(pack, started, id);
    const learner = learnerFromPack(pack);
    const action = policy(learner, session, null);
    const stored: StoredSession = {
      client_session_id: id,
      started_at: started,
      pack_hash: pack.hash,
      ...serializeSession(session),
      learner: serializeLearner(learner),
      events: [],
      action,
      confirmed_hash: null,
    };
    const player = new OfflinePlayer(store, pack, stored, session, learner, clock);
    await player.save();
    return player;
  }

  /** Pick up the session that was running when the page closed, if there is one. */
  static async resume(store: KeyValueStore, clock: Clock = Date.now): Promise<OfflinePlayer | null> {
    const pack = await OfflinePlayer.loadPack(store);
    const stored = await store.get<StoredSession>(SESSION_KEY);
    if (!pack || !stored) return null;
    return new OfflinePlayer(
      store,
      pack,
      stored,
      restoreSession(pack, stored),
      deserializeLearner(stored.learner),
      clock,
    );
  }

  /** The student did something; returns the next step. Saved before it returns. */
  async send(
    eventType: string,
    payload: Record<string, unknown> = {},
    itemId: string | null = null,
    eventId: string = crypto.randomUUID(),
  ): Promise<Action> {
    const at = this.clock();
    this.session.now = at;
    const event: SyncEvent = {
      client_event_id: eventId,
      event_type: eventType,
      item_id: itemId ?? this.stored.action?.item_id ?? null,
      at: isoformat(at),
      payload,
    };
    const policyEvent: PolicyEvent = policyEventFor(event);
    const action = policy(this.learner, this.session, policyEvent);
    this.stored.events.push({
      ...event,
      client_action: { type: action.type, item_id: action.item_id ?? null },
    });
    this.stored.action = action;
    Object.assign(this.stored, serializeSession(this.session));
    this.stored.learner = serializeLearner(this.learner);
    await this.save();
    return action;
  }

  /** The server took these events: drop them from the queue. If nothing is left unsent, adopt the
   *  server's learner state (its review cards replace the local approximations). */
  async confirm(sentIds: string[], serverLearner: LearnerState, stateHash: string): Promise<void> {
    const sent = new Set(sentIds);
    this.stored.events = this.stored.events.filter((e) => !sent.has(e.client_event_id));
    if (this.stored.events.length === 0) {
      this.learner = serverLearner;
      this.stored.learner = serializeLearner(serverLearner);
    }
    this.stored.confirmed_hash = stateHash;
    await this.save();
  }

  private async save(): Promise<void> {
    await this.store.set(SESSION_KEY, this.stored);
  }
}
