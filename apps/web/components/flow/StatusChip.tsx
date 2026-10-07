import type { ChapterStatus } from "@/lib/api";
import { statusLabel } from "@/lib/flow";
import type { Messages } from "@/lib/messages";

/** A status in words, with a shape-and-colour cue so it never relies on colour alone. */
const MARK: Record<ChapterStatus, string> = {
  not_started: "○",
  learning: "◐",
  can_do_it: "✓",
  solid: "★",
  review_due: "↻",
  coming_soon: "…",
};

export default function StatusChip({ status, copy }: { status: ChapterStatus; copy: Messages }) {
  return (
    <span className={`chip chip-${status}`} data-status={status}>
      <span aria-hidden="true">{MARK[status]}</span> {statusLabel(copy, status)}
    </span>
  );
}
