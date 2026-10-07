"use client";

import Link from "next/link";
import { notFound, useParams } from "next/navigation";
import { useEffect, useState } from "react";
import LessonPlayer from "@/components/lessons/LessonPlayer";
import { getDevLesson, locale, verifyDevWidget } from "@/lib/api";
import { devToolsEnabled } from "@/lib/dev";
import type { Lesson } from "@/lib/lessons/types";

/** Dev only: play one lesson with no login. Widget results are still checked by the server. */
export default function DevLessonPage() {
  if (!devToolsEnabled()) notFound();
  const params = useParams<{ id: string }>();
  const id = decodeURIComponent(String(params?.id ?? ""));
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getDevLesson(id)
      .then(setLesson)
      .catch(() => setError("Could not load this lesson. Is the API running with DEV_TOOLS=true?"));
  }, [id]);

  if (error) {
    return (
      <main className="stack">
        <p role="alert">{error}</p>
        <Link href="/dev/lessons">All lessons</Link>
      </main>
    );
  }
  if (!lesson) return <main className="stack">Loading…</main>;
  return (
    <>
      <p className="lp-src">
        <Link href="/dev/lessons">← All lessons</Link>
      </p>
      <LessonPlayer
        lesson={lesson}
        locale={locale()}
        mode="preview"
        onWidgetResult={async (r) => (await verifyDevWidget(lesson.id, r.widget_id, r.final_state)).ok}
      />
    </>
  );
}
