"use client";

import * as React from "react";
import { cn } from "@/lib/cn";

/**
 * A tappable option for the setup conversation (class, board, subject, ...). Selected state is shown by
 * a check mark and a border (not colour alone). An unavailable option is disabled and carries a tag
 * such as "coming soon", so the reason is in words.
 */
export interface ChoiceProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, "onSelect"> {
  selected?: boolean;
  tag?: string;
}

export const Choice = React.forwardRef<HTMLButtonElement, ChoiceProps>(
  ({ selected = false, tag, disabled, className, children, ...props }, ref) => (
    <button
      ref={ref}
      type="button"
      aria-pressed={selected}
      disabled={disabled}
      className={cn(
        "inline-flex min-h-12 w-auto cursor-pointer items-center gap-2 rounded-full border px-4 py-2 text-base font-semibold",
        selected
          ? "border-accent bg-accent-soft text-ink"
          : "border-line bg-surface text-ink hover:bg-surface-2",
        "disabled:cursor-not-allowed disabled:opacity-60",
        className,
      )}
      {...props}
    >
      {selected ? <span aria-hidden="true">✓</span> : null}
      <span>{children}</span>
      {tag ? (
        <span className="rounded-full bg-neutral-soft px-2 py-0.5 text-xs font-semibold text-muted">
          {tag}
        </span>
      ) : null}
    </button>
  ),
);
Choice.displayName = "Choice";
