import type { ChapterStatus } from "@/lib/api";
import { statusLabel } from "@/lib/flow";
import type { Messages } from "@/lib/messages";
import { cn } from "@/lib/cn";

/** Status in words with a shape cue and a tone, so colour is never the only signal. */
const MARK: Record<ChapterStatus, string> = {
  not_started: "○",
  learning: "◐",
  can_do_it: "✓",
  solid: "★",
  review_due: "↻",
  coming_soon: "…",
};

const TONE: Record<ChapterStatus, string> = {
  not_started: "bg-neutral-soft text-neutral",
  learning: "bg-warning-soft text-warning",
  can_do_it: "bg-success-soft text-success",
  solid: "bg-success-soft text-success",
  review_due: "bg-accent-soft text-ink",
  coming_soon: "bg-neutral-soft text-muted",
};

export function StatusChip({
  status,
  copy,
  className,
}: {
  status: ChapterStatus;
  copy: Messages;
  className?: string;
}) {
  return (
    <span
      data-status={status}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-semibold",
        TONE[status],
        className,
      )}
    >
      <span aria-hidden="true">{MARK[status]}</span>
      {statusLabel(copy, status)}
    </span>
  );
}
