/**
 * Sharing a lesson as a link: `/brownie-chat?topic=...` opens straight into a lesson on that question.
 *
 * The link carries the question and nothing else: no name, no account, no result. Opening it goes through
 * exactly the same safety checks as typing the question, and the page shows the question to whoever opens
 * it, so a link cannot quietly ask something the reader cannot see.
 */

/** The longest question a link may carry; the explain endpoints cap the question at about this much. */
export const MAX_TOPIC_CHARS = 300;

/** The question in a page address, or null when there is none worth starting a lesson on. */
export function topicFromSearch(search: string): string | null {
  let raw: string | null;
  try {
    raw = new URLSearchParams(search).get("topic");
  } catch {
    return null;
  }
  const topic = (raw ?? "").replace(/\s+/g, " ").trim().slice(0, MAX_TOPIC_CHARS);
  return topic.length >= 2 ? topic : null;
}

/** The code of a shared group lesson in a page address, or null when it is missing or malformed. */
export function groupFromSearch(search: string): string | null {
  let raw: string | null;
  try {
    raw = new URLSearchParams(search).get("group");
  } catch {
    return null;
  }
  return raw !== null && /^[A-Za-z0-9_-]{6,16}$/.test(raw) ? raw : null;
}

/** The address that opens a lesson on this question. */
export function lessonLink(origin: string, topic: string): string {
  const clean = topic.replace(/\s+/g, " ").trim().slice(0, MAX_TOPIC_CHARS);
  return `${origin}/brownie-chat?topic=${encodeURIComponent(clean)}`;
}

type ShareEnv = {
  origin: string;
  share?: (data: { title?: string; text?: string; url: string }) => Promise<void>;
  writeText?: (text: string) => Promise<void>;
};

export type ShareOutcome = "shared" | "copied" | "cancelled" | "failed";

/**
 * Offer the link through the device's own share sheet where there is one (on a phone that includes
 * WhatsApp), and copy it otherwise. Backing out of the sheet is not an error.
 */
export async function shareLesson(topic: string, title: string, env: ShareEnv): Promise<ShareOutcome> {
  const url = lessonLink(env.origin, topic);
  if (env.share) {
    try {
      await env.share({ title, text: title, url });
      return "shared";
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return "cancelled";
      // the share sheet failed for another reason: fall through and try copying
    }
  }
  if (env.writeText) {
    try {
      await env.writeText(url);
      return "copied";
    } catch {
      return "failed";
    }
  }
  return "failed";
}

/** The share and copy abilities of this browser, or none when it has neither (server rendering, old browsers). */
export function browserShareEnv(): ShareEnv {
  const nav = typeof navigator === "undefined" ? undefined : navigator;
  return {
    origin: typeof window === "undefined" ? "" : window.location.origin,
    share: nav && typeof nav.share === "function" ? (data) => nav.share(data) : undefined,
    writeText: nav?.clipboard && typeof nav.clipboard.writeText === "function" ? (text) => nav.clipboard.writeText(text) : undefined,
  };
}
