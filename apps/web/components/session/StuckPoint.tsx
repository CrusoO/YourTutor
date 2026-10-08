"use client";

import type { Messages } from "@/lib/messages";

export type StuckChoice = "start" | "step" | "restate" | "might_be_right";

type PointProps = {
  copy: Messages;
  stem: string | undefined;
  choices: string[];
  onChoose: (choice: StuckChoice) => void;
};

/** "Where are you stuck?" Ask before telling: the student picks, then gets the smallest help. */
export function StuckPoint({ copy, stem, choices, onChoose }: PointProps) {
  const labels: Record<StuckChoice, string> = {
    start: copy.stuckStart,
    step: copy.stuckStep,
    restate: copy.stuckRestate,
    might_be_right: copy.stuckMight,
  };
  return (
    <section className="stack" data-testid="stuck-point">
      <h1>{copy.stuckTitle}</h1>
      {stem ? <p className="stem">{stem}</p> : null}
      <div className="stack" role="group" aria-label={copy.stuckTitle}>
        {(choices as StuckChoice[])
          .filter((choice) => choice in labels)
          .map((choice) => (
            <button
              key={choice}
              type="button"
              className="secondary"
              data-choice={choice}
              onClick={() => onChoose(choice)}
            >
              {labels[choice]}
            </button>
          ))}
      </div>
    </section>
  );
}

type StepProps = {
  copy: Messages;
  stem: string | undefined;
  count: number;
  onPick: (index: number) => void;
};

/** Which step? Numbered buttons only: the steps themselves would give the solution away. */
export function StuckStep({ copy, stem, count, onPick }: StepProps) {
  return (
    <section className="stack" data-testid="stuck-step">
      <h1>{copy.stuckStepTitle}</h1>
      {stem ? <p className="stem">{stem}</p> : null}
      <div className="stack" role="group" aria-label={copy.stuckStepTitle}>
        {Array.from({ length: count }, (_, index) => (
          <button
            key={index}
            type="button"
            className="secondary"
            data-step={index}
            onClick={() => onPick(index)}
          >
            {copy.stepLabel} {index + 1}
          </button>
        ))}
      </div>
    </section>
  );
}

/** What to look at again after a slip. Never says what the right answer is. */
export function checkText(copy: Messages, kind: string | undefined): string {
  switch (kind) {
    case "sign_flip":
      return copy.checkSign;
    case "off_by":
      return copy.checkArithmetic;
    case "values":
      return copy.checkValue;
    case "recheck":
      return copy.checkRecheck;
    default:
      return copy.checkGeneric;
  }
}
