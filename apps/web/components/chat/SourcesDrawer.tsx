"use client";

import { useRef, useState } from "react";
import { authFetch } from "@/lib/api";
import { cn } from "@/lib/cn";

// Always shown — non-suppressible.
const MANDATORY_CAVEATS = [
  "No person has confirmed these page numbers.",
  "The voice in this video is AI-generated.",
];

type Sources = {
  caveats?: string[];
  book?: {
    title?: string;
    chapter?: string;
    section?: string;
    pages?: number[];
  };
  [key: string]: unknown;
};

interface SourcesDrawerProps {
  jobId: string;
  className?: string;
}

export function SourcesDrawer({ jobId, className }: SourcesDrawerProps) {
  const [sources, setSources] = useState<Sources | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Prevent re-fetching on every open
  const fetchedRef = useRef(false);

  async function fetchSources() {
    if (fetchedRef.current) return;
    fetchedRef.current = true;
    setLoading(true);
    try {
      const r = await authFetch(`/video-jobs/${jobId}/sources.json`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setSources((await r.json()) as Sources);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load sources.");
      fetchedRef.current = false; // allow retry on next open
    } finally {
      setLoading(false);
    }
  }

  // Merge mandatory caveats with any additional ones from the API,
  // deduplicating so mandatory caveats appear only once.
  const extraCaveats =
    sources?.caveats?.filter((c) => !MANDATORY_CAVEATS.includes(c)) ?? [];
  const allCaveats = [...MANDATORY_CAVEATS, ...extraCaveats];

  return (
    // Native <details> handles open/close with zero JS
    <details
      className={cn("rounded-xl border border-[var(--c-line)] bg-[var(--c-surface)]", className)}
      onToggle={(e) => {
        if ((e.currentTarget as HTMLDetailsElement).open) void fetchSources();
      }}
    >
      <summary className="flex cursor-pointer select-none list-none items-center justify-between px-4 py-3 text-sm font-medium text-[var(--c-text)]">
        <span>Sources &amp; caveats</span>
        <span className="text-[var(--c-muted)] transition-transform [[open]_&]:rotate-180">▾</span>
      </summary>

      <div className="space-y-3 px-4 pb-4 text-sm">
        {loading && <p className="text-xs text-[var(--c-muted)]">Loading…</p>}
        {error && (
          <p className="text-xs text-[var(--c-danger)]" role="alert">
            {error}
          </p>
        )}

        {sources?.book && (
          <div>
            <p className="mb-1 text-xs font-medium uppercase tracking-wide text-[var(--c-muted)]">
              Book
            </p>
            {sources.book.title && (
              <p className="text-[var(--c-text)]">{sources.book.title}</p>
            )}
            {(sources.book.chapter ?? sources.book.section) && (
              <p className="text-[var(--c-muted)]">
                {[sources.book.chapter, sources.book.section].filter(Boolean).join(", ")}
              </p>
            )}
            {sources.book.pages && sources.book.pages.length > 0 && (
              <p className="text-[var(--c-muted)]">
                Pages: {sources.book.pages.join(", ")}
              </p>
            )}
          </div>
        )}

        <div>
          <p className="mb-1 text-xs font-medium uppercase tracking-wide text-[var(--c-muted)]">
            Caveats
          </p>
          <ul className="space-y-1">
            {allCaveats.map((c, i) => (
              <li key={i} className="flex gap-2 text-[var(--c-muted)]">
                <span className="shrink-0">•</span>
                <span>{c}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </details>
  );
}
