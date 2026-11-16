"use client";

import { useId, useState, type ReactNode } from "react";
import { cn } from "@/lib/cn";
import { langProps } from "./lang";

export type HintLadderLabels = {
  /** First button while no hint is open, for example "Show a hint". */
  first: string;
  /** Button once at least one is open, for example "Show the next hint". */
  next: string;
  /** The last-resort button, for example "Show full steps". */
  steps: string;
  /** Said under the locked steps button, for example "Open a hint first". */
  stepsLocked: string;
  /** Heading for hint number n of total. */
  hintTitle: (n: number, total: number) => string;
};

export type HintLadderProps = {
  hints: readonly string[];
  labels: HintLadderLabels;
  /** Full worked steps, shown only after the gate button is pressed. */
  steps?: ReactNode;
  /** Called with the zero-based index each time a hint opens (the caller logs it; the text never leaves the device). */
  onReveal?: (index: number) => void;
  onShowSteps?: () => void;
  disabled?: boolean;
  /** Loading: a hint is being prepared; buttons wait. */
  loading?: boolean;
  lang?: string;
  className?: string;
};

const BTN =
  "inline-flex min-h-11 w-full cursor-pointer font-[family-name:var(--ff-body)]! normal-case! tracking-normal! items-center justify-center rounded-xl border-2 px-4 py-2 text-base font-semibold focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-[color:var(--c-focus)] disabled:cursor-not-allowed disabled:opacity-60";

/**
 * Hints open one at a time, in order. "Show full steps" is a last resort: it stays disabled until at least one hint
 * has been opened. New hints are announced through an aria-live region. States: default, disabled, loading.
 */
export function HintLadder({ hints, labels, steps, onReveal, onShowSteps, disabled, loading, lang, className }: HintLadderProps) {
  const [open, setOpen] = useState(0);
  const [showSteps, setShowSteps] = useState(false);
  const whyId = useId();
  const off = disabled || loading;
  const more = open < hints.length;
  return (
    <div {...langProps(lang)} data-state={loading ? "loading" : disabled ? "disabled" : "default"} className={cn("flex flex-col gap-3", className)}>
      <div aria-live="polite" aria-atomic="false" aria-busy={loading || undefined} className="flex flex-col gap-3" data-testid="hint-list">
        {hints.slice(0, open).map((h, i) => (
          <div key={i} className="rounded-xl border border-input-line bg-accent-soft p-4 text-ink">
            <p className="m-0 text-sm font-semibold text-accent-ink">{labels.hintTitle(i + 1, hints.length)}</p>
            <p className="m-0 mt-1 text-base">{h}</p>
          </div>
        ))}
        {showSteps ? (
          <div data-testid="full-steps" className="rounded-xl border border-input-line bg-surface p-4 text-base text-ink">
            {steps}
          </div>
        ) : null}
      </div>
      {loading ? <div aria-hidden="true" className="h-12 rounded-xl bg-surface-2 motion-safe:animate-pulse" /> : null}
      {more ? (
        <button
          type="button"
          data-testid="hint-next"
          disabled={off}
          onClick={() => {
            onReveal?.(open);
            setOpen(open + 1);
          }}
          className={cn(BTN, "border-accent bg-accent text-accent-fg")}
        >
          {open === 0 ? labels.first : labels.next}
        </button>
      ) : null}
      {steps && !showSteps ? (
        <div className="flex flex-col gap-1">
          <button
            type="button"
            data-testid="hint-steps"
            disabled={off || open < 1}
            aria-describedby={open < 1 ? whyId : undefined}
            onClick={() => {
              setShowSteps(true);
              onShowSteps?.();
            }}
            className={cn(BTN, "border-input-line bg-surface text-ink")}
          >
            {labels.steps}
          </button>
          {open < 1 ? (
            <p id={whyId} className="m-0 text-xs text-muted">
              {labels.stepsLocked}
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
