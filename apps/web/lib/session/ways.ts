/** The kinds of help Brownie can offer after a wrong answer, and which of them this screen can show. */

export const WAYS = ["picture", "steps", "worked", "video"] as const;
export type Way = (typeof WAYS)[number];

export type WayAvailability = Partial<Record<Way, boolean>>;

function isWay(value: unknown): value is Way {
  return typeof value === "string" && (WAYS as readonly string[]).includes(value);
}

/**
 * The families to show, in the server's order: only known ones, only ones this screen can do, each
 * once. An empty list means "show nothing new", so the existing buttons stay as they were.
 */
export function offeredWays(offer: unknown, available: WayAvailability): Way[] {
  if (!Array.isArray(offer)) return [];
  const seen = new Set<Way>();
  for (const entry of offer) {
    if (isWay(entry) && available[entry] === true) seen.add(entry);
  }
  return [...seen];
}

/** What the server sent about the last wrong answer, reduced to what the screen needs. */
export function readReason(extras: Record<string, unknown> | undefined): { offer: unknown } | null {
  const reason = extras?.reason;
  if (typeof reason !== "object" || reason === null) return null;
  return { offer: (reason as { offer?: unknown }).offer };
}
