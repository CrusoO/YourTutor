/**
 * The composer's topic finder (UI-1). Deterministic and local: it cleans and screens the typed text with
 * the rules the server publishes (GET /context/finder-rules), then matches words against the titles of
 * the student's chapters and skills. It generates nothing. The text is never sent anywhere, stored, or
 * logged: this module has no network, storage or console calls, and a test keeps it that way.
 */

import type { Helpline } from "@/lib/api";

/** An everyday word and what it stands for, published by the server as data (config/topic_aliases.yaml). */
export type TopicAlias = { say: string[]; words: string[]; skill_prefixes: string[] };

export type FinderRules = {
  max_chars: number;
  pii: { email: string; phone: string; url: string };
  distress_terms: string[];
  blocked_patterns: string[];
  blocked_terms: string[];
  /** Support lines the device shows when it answers a distress phrase itself (optional: older servers omit it). */
  helplines?: Helpline[];
  /** Everyday words ("algebra", "trig") mapped to topic words and skill id prefixes (optional: older servers omit it). */
  topic_aliases?: TopicAlias[];
};

export type Topic = { id: string; title: string; chapterId: string; kind: "chapter" | "skill" };

export type Prepared =
  | { kind: "empty" }
  | { kind: "too_long" }
  | { kind: "distress" }
  | { kind: "blocked" }
  | { kind: "ok"; text: string; piiRemoved: boolean };

export type FindResult = { kind: "matches"; topics: Topic[] } | { kind: "none" };

const REMOVED = "[removed]";

function compile(pattern: string, flags: string): RegExp | null {
  try {
    return new RegExp(pattern, flags);
  } catch {
    return null; // a bad rule from the server must not break the finder
  }
}

/** Clean and screen typed text. Returns what the matcher may use, or why it must not. */
export function prepare(raw: string, rules: FinderRules): Prepared {
  const text = raw.split(/\s+/).filter(Boolean).join(" ");
  if (!text) return { kind: "empty" };
  if (text.length > rules.max_chars) return { kind: "too_long" };
  const lowered = text.toLowerCase();
  if (rules.distress_terms.some((term) => lowered.includes(term.toLowerCase()))) {
    return { kind: "distress" };
  }
  for (const pattern of rules.blocked_patterns) {
    const re = compile(pattern, "iu");
    if (re?.test(lowered)) return { kind: "blocked" };
  }
  for (const term of rules.blocked_terms) {
    const safe = term.toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const re = compile(`(?<![\\p{L}\\p{N}])${safe}(?![\\p{L}\\p{N}])`, "u");
    if (re?.test(lowered)) return { kind: "blocked" };
  }
  let cleaned = text;
  for (const pattern of [rules.pii.phone, rules.pii.email, rules.pii.url]) {
    const re = compile(pattern, "giu");
    if (re) cleaned = cleaned.replace(re, REMOVED);
  }
  return { kind: "ok", text: cleaned, piiRemoved: cleaned !== text };
}

function tokens(text: string): string[] {
  const words = text.toLowerCase().normalize("NFKC").match(/[\p{L}\p{N}]+/gu) ?? [];
  return words.filter((w) => w.length > 1 || /\p{N}/u.test(w));
}

const STOP_AT = 0.5; // at least half of the typed words must find a word in the topic title

function score(query: string[], title: string[]): number {
  if (!query.length) return 0;
  let total = 0;
  for (const q of query) {
    if (title.includes(q)) total += 1;
    else if (q.length >= 3 && title.some((t) => t.startsWith(q) || (t.length >= 3 && q.startsWith(t)))) {
      total += 0.5;
    }
  }
  return total / query.length;
}

function hasPhrase(query: string[], phrase: string[]): boolean {
  if (!phrase.length) return false;
  for (let i = 0; i + phrase.length <= query.length; i++) {
    if (phrase.every((word, k) => query[i + k] === word)) return true;
  }
  return false;
}

function wordHits(word: string, title: string[]): boolean {
  return title.some((t) => t === word || (word.length >= 4 && t.length >= 4 && (t.startsWith(word) || word.startsWith(t))));
}

/** Topics the everyday words point at: by topic word in the title, or by skill id prefix. Chapters first. */
function matchAliases(query: string[], topics: Topic[], aliases: TopicAlias[], limit: number): Topic[] {
  const hits = aliases.filter((alias) => alias.say.some((phrase) => hasPhrase(query, tokens(phrase))));
  if (!hits.length) return [];
  const words = hits.flatMap((alias) => alias.words.map((w) => w.toLowerCase()));
  const prefixes = hits.flatMap((alias) => alias.skill_prefixes.map((p) => p.toUpperCase()));
  const direct = (topic: Topic): boolean => {
    const title = tokens(topic.title);
    if (words.some((w) => wordHits(w, title))) return true;
    const id = topic.id.toUpperCase();
    return topic.kind === "skill" && prefixes.some((p) => id === p || id.startsWith(`${p}.`));
  };
  const skillChapters = new Set(topics.filter((t) => t.kind === "skill" && direct(t)).map((t) => t.chapterId));
  const chapters = topics.filter((t) => t.kind === "chapter" && (direct(t) || skillChapters.has(t.id)));
  const skills = topics.filter((t) => t.kind === "skill" && direct(t));
  return [...chapters, ...skills].slice(0, limit);
}

/**
 * Up to `limit` topics for "Did you mean" chips, best first; none when the text is off the syllabus.
 * Words that match a title come first; failing that, everyday words from the server's alias table
 * ("algebra", "trig") are matched against the student's own chapters and skills. All on the device.
 */
export function findTopics(text: string, topics: Topic[], limit = 3, aliases: TopicAlias[] = []): FindResult {
  const query = tokens(text);
  const scored = topics
    .map((topic, order) => ({ topic, order, value: score(query, tokens(topic.title)) }))
    .filter((row) => row.value >= STOP_AT)
    .sort((a, b) => b.value - a.value || a.order - b.order);
  if (!scored.length) {
    const viaAlias = matchAliases(query, topics, aliases, limit);
    return viaAlias.length ? { kind: "matches", topics: viaAlias } : { kind: "none" };
  }
  return { kind: "matches", topics: scored.slice(0, limit).map((row) => row.topic) };
}
