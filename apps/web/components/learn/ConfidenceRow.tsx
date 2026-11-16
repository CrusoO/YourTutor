"use client";

import { useId } from "react";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icons";
import { langProps } from "./lang";

export type ConfidenceOption = { value: string; label: string };

export type ConfidenceRowProps = {
  /** The question text, for example "How sure are you?". */
  legend: string;
  /** Exactly the three steps, in order: guessing, think so, sure. */
  options: readonly [ConfidenceOption, ConfidenceOption, ConfidenceOption];
  value?: string | null;
  onChange?: (value: string) => void;
  disabled?: boolean;
  loading?: boolean;
  lang?: string;
  className?: string;
};

/**
 * A three-way segmented control (radiogroup). The chosen segment is filled and carries a check mark, so it is
 * not colour alone. Native hidden radios give arrow-key movement; each segment is 48 px tall.
 */
export function ConfidenceRow({ legend, options, value = null, onChange, disabled, loading, lang, className }: ConfidenceRowProps) {
  const name = useId();
  const labelId = `${name}-legend`;
  const off = disabled || loading;
  return (
    <div
      {...langProps(lang)}
      className={cn("flex flex-col gap-2", className)}
      data-state={loading ? "loading" : disabled ? "disabled" : value ? "selected" : "default"}
    >
      <p id={labelId} className="m-0 text-base font-semibold text-ink">
        {legend}
      </p>
      <div role="radiogroup" aria-labelledby={labelId} aria-busy={loading || undefined} className="grid grid-cols-3 gap-2">
        {options.map((o) => {
          const on = value === o.value;
          return (
            <label key={o.value} className={cn("block", off ? "cursor-not-allowed opacity-70" : "cursor-pointer")}>
              <input
                type="radio"
                name={name}
                value={o.value}
                checked={on}
                disabled={off}
                onChange={() => onChange?.(o.value)}
                className="peer sr-only"
              />
              <span
                className={cn(
                  "flex min-h-12 items-center justify-center gap-1 rounded-xl border-2 px-1 py-2 text-center text-sm font-semibold",
                  "peer-focus-visible:outline peer-focus-visible:outline-[3px] peer-focus-visible:outline-offset-2 peer-focus-visible:outline-[color:var(--c-focus)]",
                  on ? "border-accent bg-accent text-accent-fg" : "border-input-line bg-surface text-ink hover:bg-surface-2",
                )}
              >
                {on ? <Icon name="check" size={14} /> : null}
                {o.label}
              </span>
            </label>
          );
        })}
      </div>
    </div>
  );
}
