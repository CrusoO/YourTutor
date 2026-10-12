"use client";

import Link from "next/link";
import { notFound } from "next/navigation";
import { useEffect, useState } from "react";
import { listDevLessons, type DevLessonRow } from "@/lib/api";
import { devToolsEnabled } from "@/lib/dev";

export default function DevLessonsPage() {
  if (!devToolsEnabled()) notFound();
  const [lessons, setLessons] = useState<DevLessonRow[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    listDevLessons()
      .then((body) => setLessons(body.lessons))
      .catch(() =>
        setError("Could not load lessons. Start the API with DEV_TOOLS=true and ALLOW_DRAFT_CONTENT=true."),
      );
  }, []);

  return (
    <main className="stack">
      <h1>Lessons</h1>
      {error ? <p role="alert">{error}</p> : null}
      {lessons && lessons.length === 0 ? <p>No lessons found in content/lessons.</p> : null}
      <ul className="stack">
        {(lessons ?? []).map((l) => (
          <li key={l.id} className="[overflow-wrap:anywhere]">
            <Link href={`/dev/lessons/${encodeURIComponent(l.id)}`}>{l.title}</Link>
            <div>
              {l.id} · {l.skill_id} · {l.status} · {l.beats.join(" → ")}
            </div>
            <div>{l.source_ref}</div>
          </li>
        ))}
      </ul>
      <p>
        <Link href="/dev">Back to scenarios</Link>
      </p>
    </main>
  );
}
