import { cn } from "@/lib/cn";
import { langProps } from "./lang";

export type ProgressBarProps = {
  current: number;
  total: number;
  /** Accessible name and visible text, for example "Question 2 of 5". Built by the caller from its own copy. */
  label: string;
  /** Hide the visible text (the name stays for screen readers). */
  hideLabel?: boolean;
  lang?: string;
  className?: string;
};

/** A progress bar with a text value (`role="progressbar"` named by `label`). The fill grows only when motion is allowed. */
export function ProgressBar({ current, total, label, hideLabel, lang, className }: ProgressBarProps) {
  const safeTotal = Math.max(1, total);
  const now = Math.max(0, Math.min(safeTotal, current));
  return (
    <div {...langProps(lang)} className={cn("flex flex-col gap-1.5", className)}>
      {hideLabel ? null : <p className="m-0 text-sm font-semibold text-muted">{label}</p>}
      <div
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={safeTotal}
        aria-valuenow={now}
        aria-valuetext={label}
        className="h-2 w-full overflow-hidden rounded-full bg-surface-2"
      >
        <div className="h-full rounded-full bg-accent motion-safe:transition-[width]" style={{ width: `${(now / safeTotal) * 100}%` }} />
      </div>
    </div>
  );
}
