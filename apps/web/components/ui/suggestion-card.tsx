"use client";

import * as React from "react";
import Link from "next/link";
import { cn } from "@/lib/cn";
import { Icon, type IconName } from "./icons";

export type CardTone = "accent" | "success" | "warning" | "neutral";

const TONE: Record<CardTone, { icon: string; tag: string }> = {
  accent: { icon: "bg-accent-soft text-accent-ink", tag: "bg-accent-soft text-accent-ink" },
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
  "home-card group flex min-h-12 w-full cursor-pointer flex-col rounded-2xl px-4 py-3.5 text-left text-ink transition hover:border-accent active:opacity-90 aria-disabled:cursor-not-allowed aria-disabled:opacity-60 no-underline";

/** One card, one primary action. Pass `onClick` for an action in the page or `href` for a route. */
export function SuggestionCard(props: AsButton | AsLink) {
  const { tone = "accent", icon, title, tag, description, className } = props;
  const body = (
    <span className="flex w-full items-center gap-3">
      <span className={cn("grid size-9 shrink-0 place-items-center rounded-[10px]", TONE[tone].icon)}>
        <Icon name={icon} size={16} />
      </span>
      <span className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className="text-[0.8125rem] font-medium leading-snug">{title}</span>
        {description ? <span className="text-[0.6875rem] leading-snug text-muted">{description}</span> : null}
      </span>
      {tag ? <span className={cn("shrink-0 rounded-full px-2.5 py-0.5 text-[0.6875rem] font-medium", TONE[tone].tag)}>{tag}</span> : null}
      <Icon name="arrowUp" size={13} className="shrink-0 rotate-45 text-muted transition-colors group-hover:text-ink" />
    </span>
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
        "glass-flat flex min-h-[4.25rem] w-full animate-pulse items-center gap-3 rounded-2xl px-4 py-3.5",
        className,
      )}
    >
      <span className="size-9 rounded-[10px] bg-surface-2" />
      <span className="h-4 w-2/3 rounded bg-surface-2" />
    </div>
  );
}
