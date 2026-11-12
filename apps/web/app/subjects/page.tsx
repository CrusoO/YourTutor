"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import FirstRun, { type Choice } from "@/components/flow/FirstRun";
import { answerOnboarding, startSession } from "@/lib/api";

import { useStudent } from "@/lib/useStudent";
import { useCopy } from "@/lib/locale";
import { prefetchSession, useStarting } from "@/lib/useStarting";

/** Subjects. Maths is the only one for now. */
export default function SubjectsPage() {
  const router = useRouter();
  const copy = useCopy();
  const student = useStudent();
  const [answered, setAnswered] = useState(false);
  const starting = useStarting();
  useEffect(() => {
    prefetchSession(router);
  }, [router]);
  if (!student) return <p>…</p>;

  function choose(choice: Choice) {
    if (choice === "not_now") {
      setAnswered(true);
      void answerOnboarding(choice).catch(() => undefined);
      return;
    }
    void starting.run(choice, async () => {
      const { next } = await answerOnboarding(choice);
      if (!student) return;
      const session = await startSession(next.session_type, student.student_id);
      router.push(`/session/${session.id}`);
    });
  }

  return (
    <main className="stack">
      <p className="muted">
        {copy.hello} {student.display_name}
      </p>
      <h1>{copy.subjectsTitle}</h1>
      {answered ? null : <FirstRun offer={student.offer} onChoose={choose} busy={starting.pending as Choice | null} />}
      {student.resume ? (
        <button
          type="button"
          className="secondary"
          onClick={() => void starting.run("resume", async () => router.push(`/session/${student.resume?.session_id}`))}
          {...starting.buttonProps("resume")}
        >
          {starting.label("resume", copy.resume)}
        </button>
      ) : null}
      {starting.status}
      {starting.error ? (
        <p className="banner" role="alert">
          {starting.error}
        </p>
      ) : null}
      <Link href="/chapters" className="card subject" data-testid="subject-math">
        <strong>{copy.subjectMath}</strong>
        <span className="muted">{copy.subjectMathHint}</span>
      </Link>
      <Link href="/join" className="muted" data-testid="join-link">
        {copy.joinLink}
      </Link>
      <Link href="/offline" className="muted" data-testid="offline-link">
        {copy.offlineTitle}
      </Link>
      <p className="muted">
        {student.remaining_active_minutes} {copy.doneMinutes}
      </p>
    </main>
  );
}
