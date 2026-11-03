"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { sendGroupResults, type GroupAnswer } from "@/lib/api";
import type { Evidence } from "@/lib/lessons/learning-map";
import { useCopy } from "@/lib/locale";

/** What is sent: how each judged question went, first try, with how sure the learner said they were. Nothing else. */
export function answersFrom(evidence: readonly Evidence[]): GroupAnswer[] {
  return evidence.map((e) => ({ question: e.question, kind: e.kind, right: e.right, confidence: e.confidence, idea: e.idea }));
}

/**
 * Offered at the end of a shared lesson: the learner may send how they did to the person who shared it. It
 * says plainly what goes (the answers, no name, no account), it is a choice not a default, and sending
 * again replaces the first.
 */
export function SendResults({ code, evidence, open, closed }: { code: string; evidence: Evidence[]; open: boolean; closed: boolean }) {
  const copy = useCopy();
  const [state, setState] = useState<"idle" | "sending" | "sent" | "failed">("idle");
  if (evidence.length === 0) return null;
  if (!open) return closed ? <p className="m-0 text-[0.8125rem] text-muted" data-testid="group-closed">{copy.groupClosed}</p> : null;

  async function send() {
    setState("sending");
    try {
      await sendGroupResults(code, answersFrom(evidence));
      setState("sent");
    } catch {
      setState("failed");
    }
  }

  return (
    <section className="flex flex-col gap-2 border-0 border-t border-line pt-5" aria-labelledby="send-results-title" data-testid="send-results">
      <h2 id="send-results-title" className="m-0 text-[1rem] font-medium text-ink">
        {copy.groupSendTitle}
      </h2>
      <p className="m-0 text-[0.875rem] text-muted">{copy.groupSendBody}</p>
      <div className="flex flex-wrap items-center gap-3">
        <Button variant="outline" size="sm" onClick={send} disabled={state === "sending" || state === "sent"} data-testid="send-results-button">
          {copy.groupSend}
        </Button>
        <span className="text-[0.8125rem] text-muted" role="status" data-testid="send-results-status">
          {state === "sent" ? copy.groupSent : state === "failed" ? copy.groupSendFailed : ""}
        </span>
      </div>
    </section>
  );
}
