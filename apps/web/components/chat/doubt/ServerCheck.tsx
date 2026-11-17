"use client";

import { useState } from "react";
import { MathText } from "@/components/learn/MathText";
import { doubtSolve } from "@/lib/api";
import { doubtServerEnabled } from "@/lib/flags";
import { checkOnServer, toDoubtExpr, type Outcome, type ServerAnswer } from "@/lib/doubt/send";
import { renderStep } from "@/lib/doubt/steps";
import type { MathCandidate } from "@/lib/doubt/types";
import { DOUBT_COPY as T } from "./copy";

const BTN =
  "inline-flex min-h-11 cursor-pointer items-center justify-center rounded-xl border-2 border-input-line bg-surface px-4 py-2 text-base font-semibold text-ink focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-[color:var(--c-focus)] disabled:cursor-not-allowed disabled:opacity-60";

/** Reserved for results the server's kernel accepted in the same response (ADR 0005, point 5). */
const LABEL_CHECKED = "Checked by code";

function answerText(a: ServerAnswer): string {
  if (a.kind === "values") return a.values.map((v) => `x = ${v}`).join(" or ");
  if (a.kind === "pair") return `x = ${a.x}, y = ${a.y}`;
  return "";
}

/**
 * The optional server check, offered only when the device cannot solve the confirmed expression. Nothing is sent
 * until the student taps. The words "Checked by code" appear only for a reply the server's kernel verified.
 */
export default function ServerCheck({ candidate }: { candidate: MathCandidate }) {
  const [state, setState] = useState<"idle" | "busy" | Outcome>("idle");
  if (!doubtServerEnabled() || !toDoubtExpr(candidate)) return null;

  async function run() {
    setState("busy");
    const out = await checkOnServer(candidate, doubtSolve);
    setState(out ?? { ok: false, refusal: "invalid" });
  }

  const done = typeof state === "object" ? state : null;
  return (
    <div className="mt-3 flex flex-col gap-2" data-testid="doubt-server">
      {!done ? (
        <>
          <p className="m-0 text-sm text-muted">{T.serverNote}</p>
          <div>
            <button type="button" className={BTN} disabled={state === "busy"} onClick={run} data-testid="doubt-server-check">
              {T.serverCheck}
            </button>
          </div>
        </>
      ) : null}
      {done && done.ok && done.result.verified ? (
        <div aria-live="polite" data-testid="doubt-server-result">
          <p className="m-0 text-sm font-semibold text-accent-ink" data-testid="doubt-server-label">
            {LABEL_CHECKED}
          </p>
          <p className="m-0 text-base font-semibold">
            <MathText text={answerText(done.result.answer)} />
          </p>
          <div className="mt-1 flex flex-col gap-1 text-base">
            {done.result.steps.map((s, i) => (
              <p key={i} className="m-0 break-words">
                <MathText text={renderStep(s)} />
              </p>
            ))}
          </div>
        </div>
      ) : null}
      {done && done.ok && !done.result.verified ? (
        <p className="m-0 text-base" aria-live="polite" data-testid="doubt-server-unchecked">
          {T.serverUnchecked}
        </p>
      ) : null}
      {done && !done.ok ? (
        <p className="m-0 text-base" aria-live="polite" data-testid="doubt-server-refused">
          {T.serverRefusal[done.refusal]}
        </p>
      ) : null}
    </div>
  );
}
