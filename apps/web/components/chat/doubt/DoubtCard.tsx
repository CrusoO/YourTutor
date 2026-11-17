"use client";

import { Suspense, lazy, useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";
import { doubtServerEnabled } from "@/lib/flags";
import { FeedbackCard } from "@/components/learn/FeedbackCard";
import { HintLadder } from "@/components/learn/HintLadder";
import { MathText } from "@/components/learn/MathText";
import { lineHeightFor } from "@/components/learn/lang";
import { checkAnswer, checkStep } from "@/lib/doubt/attempt";
import { LABEL_DEVICE, LABEL_DEVICE_DETAIL } from "@/lib/doubt/copy.en";
import { buildLadder } from "@/lib/doubt/ladder";
import { solve } from "@/lib/doubt/solve";
import type { MathCandidate, Solution } from "@/lib/doubt/types";
import { DOUBT_COPY as T } from "./copy";
import type { DoubtPayload } from "./types";

// Loaded only when the optional server check is on, so the network module stays out of the default path.
const ServerCheck = lazy(() => import("./ServerCheck"));

const BTN =
  "inline-flex min-h-11 cursor-pointer items-center justify-center rounded-xl border-2 px-4 py-2 text-base font-semibold focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-[color:var(--c-focus)] disabled:cursor-not-allowed disabled:opacity-60";
const PRIMARY = `${BTN} border-accent bg-accent text-accent-fg`;
const QUIET = `${BTN} border-input-line bg-surface text-ink`;

type Feedback = { variant: "look-again" | "correct"; text: string; evidence: string[] };

export type DoubtCardProps = {
  doubt: DoubtPayload;
  /** Edit: the typed text goes back into the composer and the card closes. */
  onEdit: (text: string) => void;
  onClose: () => void;
  /** The student tapped to hand an unsupported question to the existing explain path. */
  onExplain: (text: string) => void;
};

/**
 * One doubt in the thread. The reading is confirmed first; only then is anything solved. Every state lives in this
 * component (per-card hint level included): nothing is stored, sent or logged.
 */
export default function DoubtCard({ doubt, onEdit, onClose, onExplain }: DoubtCardProps) {
  const [confirmed, setConfirmed] = useState(false);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const solvedRef = useRef<HTMLHeadingElement>(null);
  const c = doubt.candidate;

  useEffect(() => {
    headingRef.current?.focus();
  }, []);
  useEffect(() => {
    if (confirmed) solvedRef.current?.focus();
  }, [confirmed]);

  const solution = useMemo(() => {
    if (!confirmed || !c) return null;
    try {
      return solve(c);
    } catch {
      return null;
    }
  }, [confirmed, c]);
  const ladder = useMemo(() => (solution && c ? buildLadder(c, solution) : null), [solution, c]);

  const shell = "w-full rounded-[var(--radius-card)] border border-input-line bg-surface p-4 text-ink shadow-[var(--shadow-card)]";
  const style = { lineHeight: lineHeightFor("en") };

  if (doubt.outcome === "unsupported" || (confirmed && (!solution || solution.status === "unsupported"))) {
    return (
      <section className={shell} style={style} lang="en" aria-labelledby="doubt-unsupported" data-testid="doubt-card" data-stage="unsupported">
        <h3 id="doubt-unsupported" ref={headingRef} tabIndex={-1} className="m-0 text-base font-semibold outline-none">
          {T.unsupportedTitle}
        </h3>
        <p className="m-0 mt-2 text-base">{T.unsupportedBody}</p>
        {confirmed && c && doubtServerEnabled() ? (
          <Suspense fallback={null}>
            <ServerCheck candidate={c} />
          </Suspense>
        ) : null}
        <p className="m-0 mt-2 text-sm text-muted">{T.explainNote}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <button type="button" className={PRIMARY} onClick={() => onExplain(doubt.text)} data-testid="doubt-explain">
            {T.explain}
          </button>
          <button type="button" className={QUIET} onClick={onClose} data-testid="doubt-close">
            {T.notNow}
          </button>
        </div>
      </section>
    );
  }
  if (!c) return null;

  if (!confirmed) {
    return (
      <section className={shell} style={style} lang="en" aria-labelledby="doubt-confirm" data-testid="doubt-card" data-stage="confirm">
        <h3 id="doubt-confirm" ref={headingRef} tabIndex={-1} className="m-0 text-base font-semibold outline-none">
          {T.confirmTitle}
        </h3>
        <p className="m-0 mt-3 break-words rounded-xl bg-accent-soft px-4 py-3 text-xl font-semibold" data-testid="doubt-expression">
          <MathText text={c.display} />
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <button type="button" className={PRIMARY} onClick={() => setConfirmed(true)} data-testid="doubt-confirm">
            {T.looksRight}
          </button>
          <button type="button" className={QUIET} onClick={() => onEdit(doubt.text)} data-testid="doubt-edit">
            {T.edit}
          </button>
        </div>
      </section>
    );
  }

  const levels = ladder?.levels ?? [];
  const hints = levels.filter((l) => l.level < 4).map((l) => l.text);
  const full = levels.find((l) => l.level === 4)?.text ?? "";
  const fullLines = full.split("\n").filter((l) => l && l !== LABEL_DEVICE);
  const noAnswer = solution?.status === "no_solution";
  const steps = (
    <div>
      <h4 className="m-0 text-sm font-semibold text-accent-ink">{T.stepsHeading}</h4>
      <div className="mt-1 flex flex-col gap-1 text-base">
        {fullLines.map((l, i) => (
          <p key={i} className="m-0 break-words">
            <MathText text={l} />
          </p>
        ))}
      </div>
    </div>
  );

  return (
    <section className={`${shell} flex flex-col gap-3`} style={style} lang="en" aria-labelledby="doubt-solving" data-testid="doubt-card" data-stage="solving">
      <div>
        <h3 id="doubt-solving" ref={solvedRef} tabIndex={-1} className="m-0 break-words text-lg font-semibold outline-none">
          <MathText text={c.display} />
        </h3>
        <p className="m-0 mt-1 text-sm font-semibold text-accent-ink" data-testid="doubt-label">
          {LABEL_DEVICE}
        </p>
        <p className="m-0 text-xs text-muted">{LABEL_DEVICE_DETAIL}</p>
      </div>
      {noAnswer ? <p className="m-0 text-base font-semibold">{T.noSolutionTitle}</p> : null}
      {hints.length ? (
        <HintLadder hints={hints} steps={steps} labels={{ ...T.hint, hintTitle: T.hintTitle }} lang="en" />
      ) : (
        <FallbackSteps steps={steps} />
      )}
      {doubt.pushback ? (
        <FeedbackCard variant="look-again" title={T.pushbackTitle} lang="en">
          <span data-testid="doubt-pushback">{doubt.pushback}</span>
        </FeedbackCard>
      ) : null}
      {solution && ladder ? <Tried c={c} solution={solution} /> : null}
      <div>
        <button type="button" className={QUIET} onClick={onClose} data-testid="doubt-close">
          {T.close}
        </button>
      </div>
    </section>
  );
}

/** Only if every hint was filtered out: the steps open on a tap. */
function FallbackSteps({ steps }: { steps: ReactNode }) {
  const [open, setOpen] = useState(false);
  return open ? (
    <div aria-live="polite">{steps}</div>
  ) : (
    <button type="button" className={QUIET} onClick={() => setOpen(true)} data-testid="hint-steps">
      {T.hint.steps}
    </button>
  );
}

function Tried({ c, solution }: { c: MathCandidate; solution: Solution }) {
  const canStep = c.kind === "poly_eq";
  const [mode, setMode] = useState<"answer" | "step">("answer");
  const [value, setValue] = useState("");
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  // The line above the student's next step: the equation as read, then the last step that was accepted.
  const [line, setLine] = useState(`${c.lhsText ?? ""} = ${c.rhsText ?? ""}`);

  function submit(e: FormEvent) {
    e.preventDefault();
    const text = value.trim();
    if (!text) return;
    if (mode === "answer") {
      const r = checkAnswer(c, solution, text);
      setFeedback({ variant: r.verdict === "correct" ? "correct" : "look-again", text: r.text, evidence: r.evidence });
    } else {
      const r = checkStep(c, line, text);
      if (r.verdict === "ok") setLine(text);
      setFeedback({ variant: r.verdict === "ok" ? "correct" : "look-again", text: r.text, evidence: [] });
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-2" data-testid="doubt-tried">
      <h4 className="m-0 text-sm font-semibold text-accent-ink">{T.triedTitle}</h4>
      {canStep ? (
        <div role="group" aria-label={T.triedTitle} className="flex gap-2">
          {(["answer", "step"] as const).map((m) => (
            <button
              key={m}
              type="button"
              aria-pressed={mode === m}
              onClick={() => {
                setMode(m);
                setFeedback(null);
              }}
              className={`${BTN} flex-1 ${mode === m ? "border-accent bg-accent-soft" : "border-input-line bg-surface"} text-ink`}
            >
              {m === "answer" ? T.triedAnswer : T.triedStep}
            </button>
          ))}
        </div>
      ) : null}
      <label className="flex flex-col gap-1 text-sm text-muted">
        <span>{mode === "answer" ? T.triedAnswerLabel : T.triedStepLabel}</span>
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          autoComplete="off"
          autoCorrect="off"
          spellCheck={false}
          data-testid="doubt-tried-input"
          className="min-h-11 rounded-xl border-2 border-input-line bg-surface px-3 text-base text-ink focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-[color:var(--c-focus)]"
        />
      </label>
      <button type="submit" className={PRIMARY} data-testid="doubt-tried-check">
        {T.check}
      </button>
      {feedback ? (
        <FeedbackCard variant={feedback.variant} title={feedback.variant === "correct" ? T.rightTitle : T.lookAgainTitle} lang="en">
          <span data-testid="doubt-feedback">{feedback.text}</span>
          {feedback.evidence.length ? (
            <ul className="m-0 mt-1 list-disc pl-5">
              {feedback.evidence.map((ev, i) => (
                <li key={i}>{ev}</li>
              ))}
            </ul>
          ) : null}
        </FeedbackCard>
      ) : null}
    </form>
  );
}
