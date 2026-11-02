"use client";

import { useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import type { AiCheck, AiExplain, AiHook, AiPredict, AiRecap, AiTransfer } from "@/lib/lessons/ai-lesson";
import { useCopy } from "@/lib/locale";

export type ChoiceState = "idle" | "picked" | "right" | "miss";

const CHOICE: Record<ChoiceState, string> = {
  idle: "border-line bg-surface text-ink hover:bg-surface-2",
  picked: "border-accent bg-accent-soft text-ink",
  right: "border-success bg-success-soft text-ink",
  // a miss is amber, never red (UI-2b)
  miss: "border-warning bg-warning-soft text-ink",
};

export function Choice({ state, disabled, onClick, children }: { state: ChoiceState; disabled?: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={state !== "idle"}
      disabled={disabled}
      onClick={onClick}
      className={`min-h-12 w-full cursor-pointer rounded-xl border px-4 py-3 text-left text-[0.9375rem] leading-snug transition-colors disabled:cursor-default ${CHOICE[state]}`}
    >
      {children}
    </button>
  );
}

export function BlockTitle({ children }: { children: ReactNode }) {
  return <h2 className="m-0 text-[1.0625rem] font-medium text-ink">{children}</h2>;
}

export function Note({ tone = "info", children }: { tone?: "info" | "good" | "miss"; children: ReactNode }) {
  const style = tone === "good" ? "border-success bg-success-soft" : tone === "miss" ? "border-warning bg-warning-soft" : "border-line bg-surface";
  return (
    <p className={`m-0 rounded-2xl border px-4 py-3 text-[0.9375rem] leading-[1.6] text-ink ${style}`} role="status">
      {children}
    </p>
  );
}

export function HookBlock({ block }: { block: AiHook }) {
  return (
    <section className="flex flex-col gap-3" data-testid="block-hook">
      <p className="m-0 text-[1rem] leading-[1.7] text-ink">{block.text}</p>
      <p className="home-display m-0 text-[clamp(1.25rem,2.2vw,1.65rem)] font-light leading-[1.25] tracking-[-0.02em] text-ink" style={{ fontFamily: "var(--ff-body)" }}>
        {block.question}
      </p>
    </section>
  );
}

export function ExplainBlock({ block }: { block: AiExplain }) {
  const copy = useCopy();
  return (
    <section className="flex flex-col gap-3" data-testid="block-explain">
      <p className="m-0 text-[0.9375rem] leading-[1.7] text-ink">{block.text}</p>
      {block.analogy ? (
        <p className="m-0 border-0 border-l-2 border-solid border-accent pl-4 text-[0.9375rem] leading-[1.6] text-muted">
          <span className="font-medium text-ink">{copy.lessonThinkOf}: </span>
          {block.analogy}
        </p>
      ) : null}
    </section>
  );
}

/** Commit a guess before the reveal. A multiple-choice guess is judged; a free-text one is only revealed against. */
export function PredictBlock({ block, onResult }: { block: AiPredict; onResult: (correct: boolean | null) => void }) {
  const copy = useCopy();
  const [picked, setPicked] = useState<number | null>(null);
  const [text, setText] = useState("");
  const [revealed, setRevealed] = useState(false);
  const options = !block.free_text && block.options ? block.options : null;
  const matched = options && picked !== null && block.correct !== null ? picked === block.correct : null;

  const pick = (i: number) => {
    if (picked !== null) return;
    setPicked(i);
    setRevealed(true);
    onResult(block.correct === null ? null : i === block.correct);
  };
  const reveal = () => {
    setRevealed(true);
    onResult(null);
  };

  return (
    <section className="flex flex-col gap-3" data-testid="block-predict">
      <BlockTitle>{block.prompt}</BlockTitle>
      {options ? (
        <div className="flex flex-col gap-2" role="group" aria-label={block.prompt}>
          {options.map((option, i) => (
            <Choice key={i} state={picked === i ? (matched === false ? "miss" : matched ? "right" : "picked") : "idle"} disabled={picked !== null} onClick={() => pick(i)}>
              {option}
            </Choice>
          ))}
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            readOnly={revealed}
            rows={3}
            aria-label={copy.lessonWriteGuess}
            placeholder={copy.lessonWriteGuess}
            className="w-full resize-y rounded-xl border border-line bg-surface p-3 font-[inherit] text-[0.9375rem] text-ink outline-none focus:border-accent"
          />
          {!revealed ? (
            <div>
              <Button variant="outline" size="sm" disabled={!text.trim()} onClick={reveal}>
                {copy.lessonReveal}
              </Button>
            </div>
          ) : null}
        </div>
      )}
      {revealed ? (
        <Note tone={matched === true ? "good" : matched === false ? "miss" : "info"}>
          {matched === true ? `${copy.lessonGuessMatched} ` : matched === false ? `${copy.lessonGuessMissed} ` : ""}
          {block.reveal_after}
        </Note>
      ) : null}
    </section>
  );
}

const MAX_ATTEMPTS = 3;

/** A four-option check with feedback on every option and a three-step hint ladder. */
export function CheckBlock({ block, onSolved }: { block: AiCheck; onSolved: () => void }) {
  const copy = useCopy();
  const [tried, setTried] = useState<number[]>([]);
  const [last, setLast] = useState<number | null>(null);
  const [hints, setHints] = useState(0);
  const solved = last === block.correct;
  const gaveUp = !solved && tried.length >= MAX_ATTEMPTS;
  const done = solved || gaveUp;
  const hintList = block.hint_ladder.filter(Boolean);

  const pick = (i: number) => {
    if (done || tried.includes(i)) return;
    setLast(i);
    const next = [...tried, i];
    setTried(next);
    if (i === block.correct || next.length >= MAX_ATTEMPTS) onSolved();
  };
  const stateOf = (i: number): ChoiceState => {
    if (done && i === block.correct) return "right";
    if (tried.includes(i)) return i === block.correct ? "right" : "miss";
    return "idle";
  };

  return (
    <section className="flex flex-col gap-3" data-testid="block-check">
      <p className="m-0 text-[0.75rem] text-muted">{copy.lessonCheckYourself}</p>
      <BlockTitle>{block.question}</BlockTitle>
      <div className="flex flex-col gap-2" role="group" aria-label={block.question}>
        {block.options.map((option, i) => (
          <Choice key={i} state={stateOf(i)} disabled={done || tried.includes(i)} onClick={() => pick(i)}>
            {option}
          </Choice>
        ))}
      </div>
      {last !== null ? (
        <Note tone={last === block.correct ? "good" : "miss"}>
          <strong>{last === block.correct ? copy.lessonRightAnswer : copy.lessonNotQuite}</strong> {block.feedback_per_option[last] ?? ""}
          {gaveUp ? ` ${copy.lessonAnswerShown} ${block.feedback_per_option[block.correct] ?? ""}` : ""}
        </Note>
      ) : null}
      {hints > 0 ? (
        <ol className="m-0 flex list-none flex-col gap-2 p-0">
          {hintList.slice(0, hints).map((hint, i) => (
            <li key={i} className="rounded-xl bg-surface-2 px-4 py-2.5 text-[0.875rem] leading-[1.55] text-ink">
              <span className="font-medium">
                {copy.lessonHintLabel} {i + 1}:
              </span>{" "}
              {hint}
            </li>
          ))}
        </ol>
      ) : null}
      {!done && hints < hintList.length ? (
        <div>
          <Button variant="ghost" size="sm" onClick={() => setHints((n) => n + 1)}>
            {copy.lessonHint}
          </Button>
        </div>
      ) : null}
    </section>
  );
}

export function TransferBlock({ block, onShown }: { block: AiTransfer; onShown: () => void }) {
  const copy = useCopy();
  const [text, setText] = useState("");
  const [shown, setShown] = useState(false);
  return (
    <section className="flex flex-col gap-3" data-testid="block-transfer">
      <p className="m-0 text-[0.75rem] text-muted">{copy.lessonTransferTitle}</p>
      <p className="m-0 text-[0.9375rem] leading-[1.7] text-ink">{block.scenario}</p>
      <BlockTitle>{block.question}</BlockTitle>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        readOnly={shown}
        rows={3}
        aria-label={copy.lessonWriteAnswer}
        placeholder={copy.lessonWriteAnswer}
        className="w-full resize-y rounded-xl border border-line bg-surface p-3 font-[inherit] text-[0.9375rem] text-ink outline-none focus:border-accent"
      />
      {!shown ? (
        <div>
          <Button
            variant="outline"
            size="sm"
            disabled={!text.trim()}
            onClick={() => {
              setShown(true);
              onShown();
            }}
          >
            {copy.lessonShowModel}
          </Button>
        </div>
      ) : (
        <Note>
          <strong>{copy.lessonModelAnswer}:</strong> {block.model_answer}
        </Note>
      )}
    </section>
  );
}

export function RecapBlock({ block }: { block: AiRecap }) {
  const copy = useCopy();
  return (
    <section className="flex flex-col gap-3" data-testid="block-recap">
      <BlockTitle>{copy.lessonRecapTitle}</BlockTitle>
      <ul className="m-0 flex list-disc flex-col gap-1.5 pl-5 text-[0.9375rem] leading-[1.6] text-ink">
        {block.three_bullets.map((bullet, i) => (
          <li key={i}>{bullet}</li>
        ))}
      </ul>
      {block.spaced_review_question ? (
        <p className="m-0 text-[0.875rem] leading-[1.6] text-muted">
          <span className="font-medium text-ink">{copy.lessonRevisit}: </span>
          {block.spaced_review_question}
        </p>
      ) : null}
    </section>
  );
}
