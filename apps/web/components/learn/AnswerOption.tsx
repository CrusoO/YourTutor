"use client";

import { useId, type ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icons";
import { langProps } from "./lang";

export type AnswerState = "default" | "correct" | "look-again";

export type AnswerOptionProps = {
  /** Radios with the same `name` form one group (arrow keys move between them). */
  name: string;
  value: string;
  children: ReactNode;
  selected?: boolean;
  onSelect?: (value: string) => void;
  /** correct and look-again need `stateLabel`: the words are always shown beside the icon, never colour alone. */
  state?: AnswerState;
  /** Words for the state ("Correct", "Look again"). Required for the state to show. */
  stateLabel?: string;
  disabled?: boolean;
  /** Loading: a grey bar in place of the text; not selectable. */
  loading?: boolean;
  /** Short marker shown in the circle (A, B, C). */
  marker?: string;
  lang?: string;
  className?: string;
};

/** Wrap AnswerOptions in this: it is the radiogroup. Give it `label` (the question) or `labelledBy`. */
export function AnswerGroup({
  label,
  labelledBy,
  children,
  className,
}: {
  label?: string;
  labelledBy?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div role="radiogroup" aria-label={label} aria-labelledby={labelledBy} className={cn("flex flex-col gap-3", className)}>
      {children}
    </div>
  );
}

/**
 * A full-width selectable answer card with radio semantics (a real visually hidden radio, so arrow keys, Space and
 * form behaviour come from the browser). States: default, selected, correct, look-again, disabled, loading.
 * Correct and look-again show an icon AND a text label. Targets are 48 px or more. It never reads or sends the text.
 */
export function AnswerOption({
  name,
  value,
  children,
  selected = false,
  onSelect,
  state = "default",
  stateLabel,
  disabled,
  loading,
  marker,
  lang,
  className,
}: AnswerOptionProps) {
  const id = useId();
  const result = state !== "default" && stateLabel ? state : "default";
  const off = disabled || loading;
  const tone =
    result === "correct"
      ? "border-success bg-success-soft"
      : result === "look-again"
        ? "border-warning bg-warning-soft"
        : selected
          ? "border-accent bg-accent-soft"
          : "border-input-line bg-surface hover:bg-surface-2";
  return (
    <label
      {...langProps(lang)}
      data-state={loading ? "loading" : disabled ? "disabled" : result !== "default" ? result : selected ? "selected" : "default"}
      className={cn("relative block", off ? "cursor-not-allowed opacity-70" : "cursor-pointer", className)}
    >
      <input
        type="radio"
        name={name}
        value={value}
        checked={selected}
        disabled={off}
        aria-busy={loading || undefined}
        aria-describedby={result !== "default" ? `${id}-state` : undefined}
        onChange={() => onSelect?.(value)}
        className="peer sr-only"
      />
      <span
        className={cn(
          "flex min-h-12 w-full items-center gap-3 rounded-xl border-2 px-4 py-3 text-base text-ink",
          "peer-focus-visible:outline peer-focus-visible:outline-[3px] peer-focus-visible:outline-offset-2 peer-focus-visible:outline-[color:var(--c-focus)]",
          tone,
        )}
      >
        <span
          aria-hidden="true"
          className={cn(
            "flex size-7 shrink-0 items-center justify-center rounded-full border-2 text-sm font-semibold",
            selected ? "border-accent bg-accent text-accent-fg" : "border-input-line text-ink",
          )}
        >
          {marker ?? (selected ? <Icon name="check" size={16} /> : null)}
        </span>
        {loading ? (
          <span aria-hidden="true" className="h-4 w-2/3 rounded bg-surface-2 motion-safe:animate-pulse" />
        ) : (
          <span className="min-w-0 flex-1 [overflow-wrap:anywhere]">{children}</span>
        )}
        {result !== "default" ? (
          <span
            id={`${id}-state`}
            className={cn("inline-flex shrink-0 items-center gap-1 text-sm font-semibold", result === "correct" ? "text-success" : "text-warning")}
          >
            <Icon name={result === "correct" ? "check" : "refresh"} size={16} />
            {stateLabel}
          </span>
        ) : null}
      </span>
    </label>
  );
}
