"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { browserShareEnv, shareLesson } from "@/lib/chat/share";
import { useCopy } from "@/lib/locale";

/**
 * Send this lesson's question to someone as a link. A teacher can send one to a class and a manager to a team;
 * it opens straight into a lesson, with no sign-up, and carries only the question.
 */
export function ShareLesson({ prompt, ghost = false }: { prompt: string; ghost?: boolean }) {
  const copy = useCopy();
  const [outcome, setOutcome] = useState<"shared" | "copied" | "cancelled" | "failed" | null>(null);
  const [busy, setBusy] = useState(false);

  async function share() {
    setBusy(true);
    setOutcome(await shareLesson(prompt, `${copy.appName}: ${prompt}`, browserShareEnv()));
    setBusy(false);
  }

  const message = outcome === "copied" ? copy.lessonShareCopied : outcome === "shared" ? copy.lessonShareDone : outcome === "failed" ? copy.lessonShareFailed : null;
  return (
    <div className="flex flex-wrap items-center gap-3" data-testid="share-lesson">
      <Button variant={ghost ? "ghost" : "outline"} size="sm" onClick={share} disabled={busy} data-testid="share-button">
        {copy.lessonShare}
      </Button>
      <span className="text-[0.75rem] text-muted" role="status" data-testid="share-status">
        {message ?? (ghost ? "" : copy.lessonShareNote)}
      </span>
    </div>
  );
}
