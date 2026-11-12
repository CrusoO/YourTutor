"use client";

import { useCallback, useRef, useState, type ReactNode } from "react";
import { useCopy } from "@/lib/locale";

/** The session page compiles on first visit in dev and can be slow to load; warm it while the student reads. */
export const SESSION_PREFETCH_PATH = "/session/prefetch";

/** Ask the router to load the session route ahead of time. Safe when the router has no prefetch (tests, old builds). */
export function prefetchSession(router: { prefetch?: (href: string) => unknown }): void {
  try {
    void router.prefetch?.(SESSION_PREFETCH_PATH);
  } catch {
    /* a failed prefetch only means the first visit is slower */
  }
}

/**
 * One start button at a time. The first click runs `task` and every other click is ignored until it fails:
 * a slow page load must never turn into several sessions. On success the button stays in its pending state
 * because the page is changing; on failure it comes back with the message the task (or `describe`) gives.
 * A task may return a string to say "nothing was started, tell the student this".
 */
export function useStarting() {
  const flight = useRef(false);
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState("");
  const copy = useCopy();

  const run = useCallback(
    async (key: string, task: () => Promise<void | string>, describe?: (err: unknown) => string) => {
      if (flight.current) return;
      flight.current = true;
      setPending(key);
      setError("");
      try {
        const stop = await task();
        if (typeof stop === "string") {
          flight.current = false;
          setPending(null);
          setError(stop);
        }
      } catch (err) {
        flight.current = false;
        setPending(null);
        setError(describe ? describe(err) : copy.loadError);
      }
    },
    [copy.loadError],
  );

  /** Props for a start button: disabled while any start is running, aria-busy on the one that was pressed. */
  const buttonProps = (key: string) => ({
    disabled: pending !== null,
    "aria-busy": pending === key,
  });
  const label = (key: string, text: ReactNode): ReactNode => (pending === key ? copy.starting : text);

  /** A polite announcement for screen readers (the visible label changes too). */
  const status = (
    <span role="status" aria-live="polite" className="sr-only" data-testid="starting-status">
      {pending !== null ? copy.starting : ""}
    </span>
  );

  return { run, pending, error, buttonProps, label, status };
}
