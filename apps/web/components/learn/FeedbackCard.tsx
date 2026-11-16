import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icons";
import { langProps } from "./lang";

export type FeedbackCardProps = {
  /** look-again is amber ("Not quite, let's look at this"); correct is quiet green. Never red. */
  variant: "look-again" | "correct";
  /** The headline words, for example "Not quite, let's look at this". */
  title: string;
  children?: ReactNode;
  /** Optional next step (a button or link) shown under the text. */
  action?: ReactNode;
  lang?: string;
  className?: string;
};

/**
 * Feedback after an answer: an icon plus words in a role="status" region (announced politely, no shaking, no
 * buzzer). States: look-again and correct.
 */
export function FeedbackCard({ variant, title, children, action, lang, className }: FeedbackCardProps) {
  const good = variant === "correct";
  return (
    <div
      role="status"
      data-variant={variant}
      {...langProps(lang)}
      className={cn(
        "flex gap-3 rounded-[var(--radius-card)] border-2 p-4 text-ink",
        good ? "border-success bg-success-soft" : "border-warning bg-warning-soft",
        className,
      )}
    >
      <span className={cn("mt-0.5 shrink-0", good ? "text-success" : "text-warning")}>
        <Icon name={good ? "check" : "refresh"} size={22} />
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        <p className={cn("m-0 text-base font-semibold", good ? "text-success" : "text-warning")}>{title}</p>
        {children ? <div className="text-base text-ink">{children}</div> : null}
        {action}
      </div>
    </div>
  );
}
