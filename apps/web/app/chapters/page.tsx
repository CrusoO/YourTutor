"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getChapters, locale, type ChapterCard } from "@/lib/api";
import { t } from "@/lib/messages";
import { useStudent } from "@/lib/useStudent";
import StatusChip from "@/components/flow/StatusChip";

/** Chapter map: one recommended chapter, coming-soon cards, no locks between live chapters. */
export default function ChaptersPage() {
  const copy = t(locale());
  const student = useStudent();
  const [chapters, setChapters] = useState<ChapterCard[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!student) return;
    getChapters(student.student_id)
      .then((body) => setChapters(body.chapters))
      .catch(() => setError(true));
  }, [student]);

  if (error) {
    return (
      <main className="stack">
        <p className="banner" role="alert">
          {copy.loadError}
        </p>
        <Link href="/subjects">{copy.chaptersBack}</Link>
      </main>
    );
  }
  if (!student || !chapters) return <p>…</p>;

  return (
    <main className="stack">
      <p>
        <Link href="/subjects">← {copy.chaptersBack}</Link>
      </p>
      <h1>{copy.chaptersTitle}</h1>
      <ul className="plain stack grid-cards">
        {chapters.map((chapter) => {
          const body = (
            <>
              {chapter.recommended ? <span className="flag">{copy.recommended}</span> : null}
              <strong>{chapter.title}</strong>
              <StatusChip status={chapter.status} copy={copy} />
              {chapter.live ? (
                <span className="muted">
                  {chapter.skills_can_do_it}/{chapter.skills_total} {copy.skillsCount}
                </span>
              ) : null}
            </>
          );
          return (
            <li key={chapter.id}>
              {chapter.live ? (
                <Link
                  href={`/chapters/${encodeURIComponent(chapter.id)}`}
                  className={`card chapter${chapter.recommended ? " recommended" : ""}`}
                  data-testid={`chapter-${chapter.id}`}
                >
                  {body}
                </Link>
              ) : (
                <div className="card chapter soon" aria-disabled="true" data-testid={`chapter-${chapter.id}`}>
                  {body}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </main>
  );
}
