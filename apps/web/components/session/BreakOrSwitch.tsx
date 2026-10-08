"use client";

import type { Messages } from "@/lib/messages";

export type BreakChoice = "break" | "switch" | "continue";

type Props = {
  copy: Messages;
  choices: string[];
  onChoose: (choice: BreakChoice) => void;
};

/** A calm offer, never an accusation: a break, a different question, or carry on. */
export default function BreakOrSwitch({ copy, choices, onChoose }: Props) {
  const labels: Record<BreakChoice, string> = {
    break: copy.breakBreak,
    switch: copy.breakSwitch,
    continue: copy.breakContinue,
  };
  return (
    <section className="stack" data-testid="break-or-switch">
      <h1>{copy.breakTitle}</h1>
      <p>{copy.breakText}</p>
      <div className="stack" role="group" aria-label={copy.breakTitle}>
        {(choices as BreakChoice[])
          .filter((choice) => choice in labels)
          .map((choice) => (
            <button
              key={choice}
              type="button"
              className={choice === "continue" ? "ghost" : "secondary"}
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
