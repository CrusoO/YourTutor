"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Choice } from "@/components/ui/choice";
import { LanguageSwitch } from "@/components/ui/language-switch";
import { getContextOptions, guestStart, locale, today, type ContextOptions } from "@/lib/api";
import { optionLabel } from "@/lib/chat/labels";
import { resolveSetup, stepOptions, type ContextLike } from "@/lib/chat/machine";
import { useCopy } from "@/lib/locale";
import { startFirstQuestion } from "@/lib/quick-start";

/**
 * Guest start, quick version: pick a class, pick a subject, and the first question opens. Nothing else is asked.
 * The board is filled from the one internal default in lib/quick-start.ts and is never shown.
 */
export default function QuickStartForm() {
  const router = useRouter();
  const copy = useCopy();
  const [ctx, setCtx] = useState<ContextLike | null>(null);
  const [grade, setGrade] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getContextOptions()
      .then((options: ContextOptions) => setCtx({ grades: options.grades, curricula: options.curricula }))
      .catch(() => setError(copy.startError));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const allGrades = ctx ? stepOptions(ctx, {}, "grade", true).filter((o) => o.value !== "adult") : [];
  const grades = allGrades.filter((o) => o.available);
  const someSoon = allGrades.length > grades.length;
  const subjects = ctx && grade !== null ? stepOptions(ctx, { grade }, "subject", true) : [];

  async function start(subject: string) {
    if (!ctx || grade === null) return;
    setBusy(true);
    setError("");
    try {
      const setup = resolveSetup(ctx, { grade, subject }, true);
      if (!setup.board) throw new Error("no content for this class");
      await guestStart({
        curriculum_id: setup.board,
        grade,
        subject,
        home_language: locale(),
        device_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      });
      try {
        const me = await today();
        router.push(`/session/${await startFirstQuestion(me.offer)}`);
      } catch {
        router.push("/subjects"); // the guest exists; the subjects page still offers the first lesson
      }
    } catch {
      setError(copy.quickFailed);
      setBusy(false);
    }
  }

  return (
    <>
      <LanguageSwitch />
      <h1>{copy.startTitle}</h1>
      <p className="muted">{copy.quickStartHint}</p>
      <section className="stack" aria-labelledby="quick-class">
        <h2 id="quick-class">{copy.quickClassLabel}</h2>
        <div className="flex flex-wrap gap-2" role="group" aria-labelledby="quick-class" data-testid="quick-grades">
          {grades.map((o) => (
            <Choice
              key={o.value}
              disabled={!o.available || busy}
              tag={o.available ? undefined : copy.chatSoon}
              selected={grade === Number(o.value)}
              onClick={() => setGrade(Number(o.value))}
              data-testid={`quick-grade-${o.value}`}
            >
              {optionLabel(copy, ctx, "grade", o.value, locale())}
            </Choice>
          ))}
        </div>
        {someSoon ? <p className="muted">{copy.quickOtherClassesSoon}</p> : null}
      </section>
      {grade !== null ? (
        <section className="stack" aria-labelledby="quick-subject">
          <h2 id="quick-subject">{copy.quickSubjectLabel}</h2>
          <div className="flex flex-wrap gap-2" role="group" aria-labelledby="quick-subject" data-testid="quick-subjects">
            {subjects.map((o) => (
              <Choice key={o.value} disabled={busy} onClick={() => void start(o.value)} data-testid={`quick-subject-${o.value}`}>
                {optionLabel(copy, ctx, "subject", o.value, locale())}
              </Choice>
            ))}
          </div>
        </section>
      ) : null}
      {busy ? <p className="muted" role="status">{copy.quickStarting}</p> : null}
      {error ? <p className="banner" role="alert">{error}</p> : null}
    </>
  );
}
