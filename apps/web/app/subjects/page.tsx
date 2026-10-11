"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import FirstRun, { type Choice } from "@/components/flow/FirstRun";
import { answerOnboarding, locale, startSession } from "@/lib/api";
import { t } from "@/lib/messages";
import { useStudent } from "@/lib/useStudent";

/** Subjects. Maths is the only one for now. */
export default function SubjectsPage() {
  const router = useRouter();
  const copy = t(locale());
  const student = useStudent();
  const [answered, setAnswered] = useState(false);
  if (!student) return <p>…</p>;

  async function choose(choice: Choice) {
    setAnswered(true);
    const { next } = await answerOnboarding(choice);
    if (choice === "not_now" || !student) return;
    const session = await startSession(next.session_type, student.student_id);
    router.push(`/session/${session.id}`);
  }

  return (
    <main className="stack">
      <p className="muted">
        {copy.hello} {student.display_name}
      </p>
      <h1>{copy.subjectsTitle}</h1>
      {answered ? null : <FirstRun offer={student.offer} onChoose={choose} />}
      {student.resume ? (
        <button
          type="button"
          className="secondary"
          onClick={() => router.push(`/session/${student.resume?.session_id}`)}
        >
          {copy.resume}
        </button>
      ) : null}
      <Link href="/chapters" className="card subject" data-testid="subject-math">
        <strong>{copy.subjectMath}</strong>
        <span className="muted">{copy.subjectMathHint}</span>
      </Link>
      <p className="muted">
        {student.remaining_active_minutes} {copy.doneMinutes}
      </p>
    </main>
  );
}
