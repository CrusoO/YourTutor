import type { SessionCopy } from "@/lib/session/copy";

const MAX_DOTS = 10;

/**
 * Where the student is in this practice set. The server gives no total, so this never shows a percentage: it says which
 * question this is and draws one dot for each one finished (at most ten), then a ring for the current one.
 */
export default function ProgressHeader({ copy, done }: { copy: SessionCopy; done: number }) {
  const finished = Math.max(0, Math.floor(done));
  const dots = Math.min(finished, MAX_DOTS);
  return (
    <header className="prog" data-testid="progress">
      <span className="prog-label">{copy.practiceLabel}</span>
      <span className="prog-dots" aria-hidden="true">
        {Array.from({ length: dots }, (_, i) => (
          <i key={i} className="prog-dot done" />
        ))}
        <i className="prog-dot now" />
      </span>
      <span className="prog-count" data-testid="progress-count">
        {copy.questionNumber.replace("{n}", String(finished + 1))}
      </span>
    </header>
  );
}

/** A feedback block: an icon and words, never colour alone. Right is green, not yet is amber; neither is red. */
export function FeedbackBlock({
  copy,
  correct,
}: {
  copy: SessionCopy;
  correct: boolean;
}) {
  return (
    <div className={correct ? "fbk ok" : "fbk try"} role="status" data-testid="feedback">
      <svg className="fbk-icon" viewBox="0 0 24 24" width="28" height="28" aria-hidden="true" focusable="false">
        {correct ? (
          <path d="M5 12.5l4.5 4.5L19 7.5" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
        ) : (
          <g fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 18h6M10 21h4" />
            <path d="M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2V16h5v-.1c0-.8.4-1.5 1-2A6 6 0 0 0 12 3z" />
          </g>
        )}
      </svg>
      <div>
        <p className="fbk-title">{correct ? copy.feedbackCorrect : copy.feedbackWrong}</p>
        <p className="fbk-body">{correct ? copy.feedbackCorrectBody : copy.feedbackWrongBody}</p>
      </div>
    </div>
  );
}

/** A small amber icon + words heading above a hint. */
export function HintHeading({ copy, afterWrong }: { copy: SessionCopy; afterWrong: boolean }) {
  return (
    <p className="hint-heading" data-testid="hint-heading">
      <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">
        <g fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 18h6M10 21h4" />
          <path d="M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2V16h5v-.1c0-.8.4-1.5 1-2A6 6 0 0 0 12 3z" />
        </g>
      </svg>
      {afterWrong ? copy.hintHeadingWrong : copy.hintHeading}
    </p>
  );
}
