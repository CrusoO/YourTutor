"use client";

import { useEffect, useRef, useState } from "react";
import { plainMistake } from "@/lib/plain-diagnosis";
import type { Messages } from "@/lib/messages";

export type Confidence = "sure" | "unsure";

/** One optional tap before answering: how sure the learner is. Tapping the chosen one again clears it. */
export function ConfidenceTap({
  copy,
  value,
  onChange,
}: {
  copy: Messages;
  value: Confidence | null;
  onChange: (next: Confidence | null) => void;
}) {
  const options: { id: Confidence; label: string }[] = [
    { id: "sure", label: copy.confidenceSure },
    { id: "unsure", label: copy.confidenceUnsure },
  ];
  return (
    <div
      className="flex flex-wrap items-center gap-2"
      style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 8 }}
      role="group"
      aria-label={copy.confidenceLabel}
      data-testid="confidence"
    >
      <span className="text-[0.8125rem] text-muted">{copy.confidenceLabel}</span>
      {options.map((option) => (
        <button
          key={option.id}
          type="button"
          className={`min-h-9 cursor-pointer rounded-full border px-3.5 py-1 text-[0.8125rem] ${
            value === option.id ? "border-accent bg-accent-soft text-ink" : "border-line bg-transparent text-muted hover:text-ink"
          }`}
          style={{ width: "auto", minHeight: 36 }}
          aria-pressed={value === option.id}
          data-testid={`confidence-${option.id}`}
          onClick={() => onChange(value === option.id ? null : option.id)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

/**
 * Shown AFTER the learner has given an answer, in the place of the answer box. The answer is only sent
 * once one of the three buttons is pressed; Skip sends it with no confidence. While it is being sent
 * every button is disabled, so one answer can never be sent twice.
 */
export function ConfidenceAsk({
  copy,
  answer,
  busy,
  onChoose,
  onChange,
}: {
  copy: Messages;
  answer: string;
  busy: boolean;
  onChoose: (value: Confidence | null) => void;
  onChange?: () => void;
}) {
  const first = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    first.current?.focus();
  }, []);
  return (
    <div className="stack" role="group" aria-label={copy.confidencePrompt} data-testid="confidence">
      <div aria-live="polite" className="stack">
        <p className="muted" data-testid="confidence-answer">
          {copy.confidenceYourAnswer} <strong>{answer}</strong>
        </p>
        <p className="stem">{busy ? copy.confidenceSending : copy.confidencePrompt}</p>
      </div>
      <button ref={first} type="button" disabled={busy} data-testid="confidence-sure" onClick={() => onChoose("sure")}>
        {copy.confidenceSure}
      </button>
      <button
        type="button"
        className="secondary"
        disabled={busy}
        data-testid="confidence-unsure"
        onClick={() => onChoose("unsure")}
      >
        {copy.confidenceUnsure}
      </button>
      <button type="button" className="ghost" disabled={busy} data-testid="confidence-skip" onClick={() => onChoose(null)}>
        {copy.confidenceSkip}
      </button>
      {onChange ? (
        <button type="button" className="ghost" disabled={busy} data-testid="confidence-change" onClick={onChange}>
          {copy.confidenceChange}
        </button>
      ) : null}
    </div>
  );
}

const WHY: Record<string, keyof Messages> = {
  misconception: "whyMisconception",
  slip: "whySlip",
  prerequisite_gap: "whyPrerequisite",
  incomplete_procedure: "whyIncomplete",
};

/**
 * Why the last answer may have gone wrong, in plain words, with a way to say "that's not why". The
 * class comes from the diagnosis; a class we have no words for shows nothing rather than a guess.
 */
export function WhyWrong({
  copy,
  diagnosis,
  onNotWhy,
}: {
  copy: Messages;
  diagnosis: { class?: string; description?: string; misconception_text?: string } | undefined;
  onNotWhy: (diagnosed: string) => void;
}) {
  const [noted, setNoted] = useState<"yes" | "no" | null>(null);
  const kind = diagnosis?.class ?? "";
  const key = WHY[kind];
  if (!key) return null;
  const mistake = plainMistake(diagnosis);
  return (
    <div className="stack" data-testid="why-wrong" data-class={kind}>
      <h2>{copy.whyTitle}</h2>
      {mistake ? (
        <>
          <p>{copy.whyIntro}</p>
          <p className="banner" data-testid="why-mistake">{mistake}</p>
        </>
      ) : (
        <p data-testid="why-generic">{kind === "misconception" ? copy.whyGeneric : copy[key]}</p>
      )}
      {!mistake && kind === "misconception" ? null : noted ? (
        <p className="muted" role="status">
          {noted === "yes" ? copy.whyYesNoted : copy.whyNoted}
        </p>
      ) : (
        <>
          <button type="button" className="secondary" data-testid="yes-why" onClick={() => setNoted("yes")}>
            {copy.whyYes}
          </button>
          <button
            type="button"
            className="ghost"
            data-testid="not-why"
            onClick={() => {
              setNoted("no");
              onNotWhy(kind);
            }}
          >
            {copy.whyNotWhy}
          </button>
        </>
      )}
    </div>
  );
}

const GRADE: Record<string, keyof Messages> = {
  good: "gradeGood",
  partly: "gradePartly",
  not_yet: "gradeNotYet",
};

/** The formative grade of an explain-back. Formative only: it never changes mastery. */
export function ExplainGrade({ copy, grade }: { copy: Messages; grade: string | null | undefined }) {
  const key = grade ? GRADE[grade] : undefined;
  if (!key) return null;
  return (
    <div className="stack" data-testid="explain-grade" data-grade={grade}>
      <p className="muted">{copy.gradeTitle}</p>
      <p className="banner">{copy[key]}</p>
    </div>
  );
}
