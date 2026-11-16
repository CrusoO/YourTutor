import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Icon, type IconName } from "@/components/ui/icons";
import { langProps } from "./lang";

/**
 * A calm "nothing here yet" panel: icon, title, one sentence, optional action. For a practice step that has no
 * question at all, use the existing BlockedState (re-exported from this folder) instead of this.
 */
export function EmptyState({
  title,
  children,
  action,
  icon = "inbox",
  lang,
  className,
}: {
  title: string;
  children?: ReactNode;
  action?: ReactNode;
  icon?: IconName;
  lang?: string;
  className?: string;
}) {
  return (
    <section
      {...langProps(lang)}
      aria-label={title}
      className={cn("flex flex-col items-center gap-3 rounded-[var(--radius-card)] border border-input-line bg-surface p-6 text-center text-ink", className)}
    >
      <span className="text-accent-ink">
        <Icon name={icon} size={28} />
      </span>
      <h2 className="m-0 text-lg font-semibold">{title}</h2>
      {children ? <p className="m-0 text-base text-muted">{children}</p> : null}
      {action}
    </section>
  );
}
