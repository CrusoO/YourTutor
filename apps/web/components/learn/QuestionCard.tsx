import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { langProps } from "./lang";
import { MathText } from "./MathText";

export type QuestionCardProps = {
  /** The question in words. Plain text or any node. */
  stem: ReactNode;
  /** The big equation area. A string is rendered with superscripts/subscripts (`x^2`); a node is shown as given. */
  equation?: ReactNode;
  /** Spoken form of the equation for screen readers (for example "x squared plus 5 x plus 6 equals 0"). */
  equationLabel?: string;
  /** Optional figure (a diagram or number line), shown under the equation. */
  figure?: ReactNode;
  /** Small line above the stem, for example "Question 2". */
  eyebrow?: ReactNode;
  /** Accessible name of the card region. */
  label: string;
  lang?: string;
  /** Loading: grey bars in place of the text. */
  loading?: boolean;
  className?: string;
};

/**
 * The question: eyebrow, an 18 px stem, a large equation area (scrolls sideways instead of clipping at 360 px)
 * and an optional figure. States: default, loading. It never fetches; the caller owns the text.
 */
export function QuestionCard({ stem, equation, equationLabel, figure, eyebrow, label, lang, loading, className }: QuestionCardProps) {
  return (
    <section
      aria-label={label}
      aria-busy={loading || undefined}
      data-state={loading ? "loading" : "default"}
      {...langProps(lang)}
      className={cn(
        "flex min-w-0 flex-col gap-4 rounded-[var(--radius-card)] border border-input-line bg-surface p-5 text-ink shadow-[var(--shadow-card)]",
        className,
      )}
    >
      {loading ? (
        <div aria-hidden="true" className="flex flex-col gap-3">
          <div className="h-5 w-3/4 rounded-md bg-surface-2 motion-safe:animate-pulse" />
          <div className="h-12 w-full rounded-md bg-surface-2 motion-safe:animate-pulse" />
        </div>
      ) : (
        <>
          {eyebrow ? <p className="m-0 text-sm font-semibold text-muted">{eyebrow}</p> : null}
          <p className="m-0 text-lg font-medium" data-testid="question-stem">
            {stem}
          </p>
          {equation ? (
            <div
              role="math"
              aria-label={equationLabel}
              data-testid="question-equation"
              tabIndex={0}
              className="overflow-x-auto rounded-xl bg-surface-2 px-4 py-3 text-center font-display text-2xl font-medium text-ink sm:text-3xl"
            >
              {typeof equation === "string" ? <MathText text={equation} /> : equation}
            </div>
          ) : null}
          {figure ? (
            <div data-testid="question-figure" className="flex justify-center">
              {figure}
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}
