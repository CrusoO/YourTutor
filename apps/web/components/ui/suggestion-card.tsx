"use client";

import * as React from "react";
import Link from "next/link";
import { cn } from "@/lib/cn";
import { Icon, type IconName } from "./icons";

export type CardTone = "accent" | "success" | "warning" | "neutral";

const TONE: Record<CardTone, { icon: string; tag: string }> = {
  accent: { icon: "bg-accent-soft text-ink", tag: "bg-accent-soft text-ink" },
  success: { icon: "bg-success-soft text-success", tag: "bg-success-soft text-success" },
  warning: { icon: "bg-warning-soft text-warning", tag: "bg-warning-soft text-warning" },
  neutral: { icon: "bg-neutral-soft text-neutral", tag: "bg-neutral-soft text-neutral" },
};

type Common = {
  tone?: CardTone;
  icon: IconName;
  title: string;
  /** A count, a status, "new" or "soon". Always words, never colour alone. */
  tag?: string;
  description?: string;
  className?: string;
  "data-testid"?: string;
};

type AsButton = Common & { onClick: () => void; href?: undefined; disabled?: boolean };
type AsLink = Common & { href: string; onClick?: undefined; disabled?: undefined };

const base =
  "group flex min-h-12 w-full cursor-pointer flex-col gap-3 rounded-[var(--radius-card)] border border-line bg-surface p-4 text-left text-ink shadow-[var(--shadow-card)] transition hover:-translate-y-px hover:border-accent hover:bg-surface-2 active:translate-y-0 active:opacity-90 aria-disabled:cursor-not-allowed aria-disabled:opacity-60 aria-disabled:hover:translate-y-0 no-underline";

/** One card, one primary action. Pass `onClick` for an action in the page or `href` for a route. */
export function SuggestionCard(props: AsButton | AsLink) {
  const { tone = "accent", icon, title, tag, description, className } = props;
  const body = (
    <>
      <span className="flex items-start justify-between gap-3">
        <span className={cn("grid size-10 shrink-0 place-items-center rounded-xl", TONE[tone].icon)}>
          <Icon name={icon} />
        </span>
        {tag ? (
          <span className={cn("rounded-full px-2.5 py-0.5 text-xs font-semibold", TONE[tone].tag)}>
            {tag}
          </span>
        ) : null}
      </span>
      <span className="text-base font-semibold leading-snug">{title}</span>
      {description ? <span className="text-sm text-muted">{description}</span> : null}
    </>
  );
  const testId = props["data-testid"];
  if (props.href !== undefined) {
    return (
      <Link href={props.href} className={cn(base, className)} data-testid={testId}>
        {body}
      </Link>
    );
  }
  return (
    <button
      type="button"
      onClick={props.onClick}
      disabled={props.disabled}
      aria-disabled={props.disabled || undefined}
      className={cn(base, "w-full", className)}
      data-testid={testId}
    >
      {body}
    </button>
  );
}

/** Placeholder while a card's data loads: same footprint, so nothing jumps. */
export function SuggestionCardSkeleton({ className }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "flex min-h-[7.5rem] w-full animate-pulse flex-col gap-3 rounded-[var(--radius-card)] border border-line bg-surface p-4",
        className,
      )}
    >
      <span className="size-10 rounded-xl bg-surface-2" />
      <span className="h-4 w-2/3 rounded bg-surface-2" />
      <span className="h-3 w-1/2 rounded bg-surface-2" />
    </div>
  );
}
