import type { ChapterStatus } from "@/lib/api";
import { STATUS_MARK, statusLabel } from "@/lib/flow";
import type { Messages } from "@/lib/messages";

/** A status in words, with a shape-and-colour cue so it never relies on colour alone. */
export default function StatusChip({ status, copy }: { status: ChapterStatus; copy: Messages }) {
  return (
    <span className={`chip chip-${status}`} data-status={status}>
      <span aria-hidden="true">{STATUS_MARK[status]}</span> {statusLabel(copy, status)}
    </span>
  );
}
