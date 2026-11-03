"use client";

import { useState } from "react";
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
    <div className="stack" role="group" aria-label={copy.confidenceLabel} data-testid="confidence">
      <p className="muted">{copy.confidenceLabel}</p>
      <div className="row">
        {options.map((option) => (
          <button
            key={option.id}
            type="button"
            className={value === option.id ? "" : "secondary"}
            aria-pressed={value === option.id}
            data-testid={`confidence-${option.id}`}
            onClick={() => onChange(value === option.id ? null : option.id)}
          >
            {option.label}
          </button>
        ))}
      </div>
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
  diagnosis: { class?: string } | undefined;
  onNotWhy: (diagnosed: string) => void;
}) {
  const [noted, setNoted] = useState(false);
  const kind = diagnosis?.class ?? "";
  const key = WHY[kind];
  if (!key) return null;
  return (
    <div className="stack" data-testid="why-wrong" data-class={kind}>
      <p className="muted">{copy.whyTitle}</p>
      <p>{copy[key]}</p>
      {noted ? (
        <p className="muted" role="status">
          {copy.whyNoted}
        </p>
      ) : (
        <button
          type="button"
          className="ghost"
          data-testid="not-why"
          onClick={() => {
            setNoted(true);
            onNotWhy(kind);
          }}
        >
          {copy.whyNotWhy}
        </button>
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
