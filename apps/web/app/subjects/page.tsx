"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { locale } from "@/lib/api";
import { t } from "@/lib/messages";
import { useStudent } from "@/lib/useStudent";

/** Subjects. Maths is the only one for now. */
export default function SubjectsPage() {
  const router = useRouter();
  const copy = t(locale());
  const student = useStudent();
  if (!student) return <p>…</p>;
  return (
    <main className="stack">
      <p className="muted">
        {copy.hello} {student.display_name}
      </p>
      <h1>{copy.subjectsTitle}</h1>
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
