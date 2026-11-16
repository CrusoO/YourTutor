import { cn } from "@/lib/cn";
import { langProps } from "./lang";
import { ProgressBar } from "./ProgressBar";

export type ContinueCardProps = {
  /** Where the student left off, for example the topic name. */
  title: string;
  /** Small line above the title, for example "Pick up where you left off". */
  eyebrow?: string;
  /** Optional progress through the lesson or set. */
  progress?: { current: number; total: number; label: string };
  /** The primary action's words, for example "Continue". */
  actionLabel: string;
  /** Link target. With onAction instead, the action is a button. Neither: the action is disabled. */
  href?: string;
  onAction?: () => void;
  disabled?: boolean;
  /** Loading: grey bars; the action is not shown. */
  loading?: boolean;
  /** Spoken name while loading. */
  loadingLabel?: string;
  lang?: string;
  className?: string;
};

const ACTION =
  "inline-flex min-h-12 w-full items-center font-[family-name:var(--ff-body)]! normal-case! tracking-normal! justify-center rounded-xl bg-accent px-5 py-3 text-base font-semibold text-accent-fg no-underline focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-[color:var(--c-focus)] sm:w-auto";

/** The resume card: one primary 48 px action. States: default, disabled (no target), loading. */
export function ContinueCard({ title, eyebrow, progress, actionLabel, href, onAction, disabled, loading, loadingLabel, lang, className }: ContinueCardProps) {
  const inert = disabled || (!href && !onAction);
  return (
    <section
      {...langProps(lang)}
      aria-label={loading ? loadingLabel : title}
      aria-busy={loading || undefined}
      data-state={loading ? "loading" : inert ? "disabled" : "default"}
      className={cn("flex flex-col gap-4 rounded-[var(--radius-card)] border border-input-line bg-surface p-5 text-ink shadow-[var(--shadow-card)]", className)}
    >
      {loading ? (
        <div aria-hidden="true" className="flex flex-col gap-3">
          <div className="h-4 w-1/3 rounded bg-surface-2 motion-safe:animate-pulse" />
          <div className="h-6 w-2/3 rounded bg-surface-2 motion-safe:animate-pulse" />
          <div className="h-12 w-full rounded-xl bg-surface-2 motion-safe:animate-pulse" />
        </div>
      ) : (
        <>
          <div className="flex flex-col gap-1">
            {eyebrow ? <p className="m-0 text-sm font-semibold text-muted">{eyebrow}</p> : null}
            <h2 className="m-0 text-xl font-semibold">{title}</h2>
          </div>
          {progress ? <ProgressBar {...progress} lang={lang} /> : null}
          {href && !disabled ? (
            <a href={href} className={ACTION} data-testid="continue-action">
              {actionLabel}
            </a>
          ) : (
            <button type="button" onClick={onAction} disabled={inert} className={cn(ACTION, "cursor-pointer disabled:cursor-not-allowed disabled:opacity-60")} data-testid="continue-action">
              {actionLabel}
            </button>
          )}
        </>
      )}
    </section>
  );
}
