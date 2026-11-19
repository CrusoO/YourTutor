"use client";

import { useState } from "react";
import type { SessionCopy } from "@/lib/session/copy";
import { explanationSteps, move, signRuleLines, type IntegerStem } from "@/lib/session/integer-stem";
import MiniNumberLine from "./MiniNumberLine";

/** The sign rule: the general line, and the line for this sum when it adds or takes away a negative. */
function SignRule({ copy, parse }: { copy: SessionCopy; parse: IntegerStem }) {
  const { general, specific } = signRuleLines(parse, copy);
  return (
    <div className="sign-rule" data-testid="sign-rule">
      <p>{general}</p>
      {specific ? <p className="sign-rule-extra">{specific}</p> : null}
    </div>
  );
}

/** On the solution screen: what the sign means, the number line with the landing, and the steps. */
export function SignExplanation({ copy, parse }: { copy: SessionCopy; parse: IntegerStem }) {
  const steps = explanationSteps(parse, copy, true);
  return (
    <section className="sign-card" aria-labelledby="sign-title" data-testid="sign-explanation">
      <h2 id="sign-title" className="sign-title">
        {copy.signTitle}
      </h2>
      <SignRule copy={copy} parse={parse} />
      <MiniNumberLine copy={copy} start={parse.start} delta={move(parse)} showLanding />
      <ol className="sign-steps" aria-label={copy.stepsLabel}>
        {steps.map((row) => (
          <li key={row}>{row}</li>
        ))}
      </ol>
    </section>
  );
}

/** On a practice item: a button that opens the number line. The line shows the start and the move, never the result. */
export function SignHint({
  copy,
  parse,
  defaultOpen = false,
}: {
  copy: SessionCopy;
  parse: IntegerStem;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="sign-hint" data-testid="sign-hint">
      <button
        type="button"
        className="secondary"
        aria-expanded={open}
        aria-controls="sign-hint-body"
        data-testid="sign-hint-button"
        onClick={() => setOpen(!open)}
      >
        {open ? copy.signHintClose : copy.signShowButton}
      </button>
      {open ? (
        <section id="sign-hint-body" className="sign-card" aria-label={copy.signHintTitle} data-testid="sign-hint-body">
          <h2 className="sign-title">{copy.signHintTitle}</h2>
          <SignRule copy={copy} parse={parse} />
          <MiniNumberLine copy={copy} start={parse.start} delta={move(parse)} showLanding={false} />
          <p className="muted">{copy.signHintNote}</p>
        </section>
      ) : null}
    </div>
  );
}
