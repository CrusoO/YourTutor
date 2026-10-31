"use client";

import type { VideoJobTopic } from "@/lib/api";
import { cn } from "@/lib/cn";

interface TopicChipsProps {
  topics: VideoJobTopic[];
  selected: string | null;
  onSelect: (nodeId: string) => void;
}

function groupByChapter(topics: VideoJobTopic[]): Map<string, VideoJobTopic[]> {
  const map = new Map<string, VideoJobTopic[]>();
  for (const t of topics) {
    const group = map.get(t.chapter_title) ?? [];
    group.push(t);
    map.set(t.chapter_title, group);
  }
  return map;
}

export function TopicChips({ topics, selected, onSelect }: TopicChipsProps) {
  const groups = groupByChapter(topics);

  return (
    <div className="space-y-4">
      {Array.from(groups.entries()).map(([chapter, items]) => (
        <div key={chapter}>
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-[var(--c-muted)]">
            {chapter}
          </p>
          <div className="flex flex-wrap gap-2">
            {items.map((t) => (
              <button
                key={t.node_id}
                type="button"
                onClick={() => onSelect(t.node_id)}
                data-testid={`topic-${t.node_id}`}
                className={cn(
                  "rounded-full px-3 py-1.5 text-xs font-medium transition-colors",
                  selected === t.node_id
                    ? "bg-[var(--c-accent)] text-[var(--c-accent-fg)]"
                    : "border border-[var(--c-line)] bg-[var(--c-surface)] text-[var(--c-text)] hover:border-[var(--c-accent-ink)]",
                )}
              >
                {t.section_title}
                {t.page_start != null && (
                  <span className="ml-1 opacity-60">
                    p.{t.page_start}
                    {t.page_end != null && t.page_end !== t.page_start
                      ? `–${t.page_end}`
                      : ""}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
