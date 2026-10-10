/** UTC timestamps as Python's `datetime.isoformat()` prints them, so state compares byte for byte. */

const DAY_MS = 86_400_000;

export function parseAt(value: string): number {
  return new Date(value).getTime();
}

export function days(n: number): number {
  return n * DAY_MS;
}

/** `2026-01-02T09:01:00+00:00`, with microseconds only when there are some. */
export function isoformat(ms: number): string {
  const d = new Date(ms);
  const pad = (n: number, w = 2) => String(n).padStart(w, "0");
  const base =
    `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}` +
    `T${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}`;
  const micro = d.getUTCMilliseconds() * 1000;
  return `${base}${micro ? "." + pad(micro, 6) : ""}+00:00`;
}
