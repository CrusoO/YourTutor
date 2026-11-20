"use client";

import { lazy, Suspense, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ensureDevStudent, skipLogin } from "@/lib/dev-auth";
import { getChapters, setStudentId, startSession, studentId, today } from "@/lib/api";

import { weekDotsEnabled } from "@/lib/flags";
import { useCopy } from "@/lib/locale";
import { prefetchSession, useStarting } from "@/lib/useStarting";

// The week view loads only on this page and only when the flag is on, so it never adds to the homepage bundle.
const WeekDots = lazy(() => import("@/components/today/WeekDots"));

type Today = {
  student_id: string;
  display_name: string;
  goal_minutes: number;
  remaining_active_minutes: number;
  /** Active time already used today in the student's own day; above zero means they practised today. */
  used_active_ms?: number;
  resume?: { session_id: string; type: string } | null;
};

export default function TodayPage() {
  const router = useRouter();
  const copy = useCopy();
  const [data, setData] = useState<Today | null>(null);
  const starting = useStarting();

  useEffect(() => {
    ensureDevStudent()
      .then(() => today())
      .then((row) => {
        setData(row);
        setStudentId(row.student_id);
      })
      .catch(() => {
        if (!skipLogin()) router.push("/login");
      });
  }, [router]);

  useEffect(() => {
    prefetchSession(router);
  }, [router]);

  function go(type: string) {
    void starting.run(
      type,
      async () => {
      const sid = data?.student_id || studentId();
      if (type === "practice") {
        // Practice follows the student's chapter; say so plainly when none is ready instead of starting nothing.
        const chapters = await getChapters(sid).then((r) => r.chapters).catch(() => null);
        if (chapters && chapters.length > 0 && !chapters.some((c) => c.live)) {
          return copy.chapterNotReady;
        }
      }
      const session = await startSession(type, sid);
      router.push(`/session/${session.id}`);
      },
      (err) => (err instanceof Error ? err.message : "Could not start"),
    );
  }

  if (!data) return <p>{copy.todayTitle}…</p>;

  return (
    <main className="stack">
      <h1>{copy.todayTitle}</h1>
      <p>{data.display_name}</p>
      <p>
        {copy.goal}: {data.goal_minutes} {copy.minutes}
      </p>
      <p>
        {copy.remaining}: {data.remaining_active_minutes} {copy.minutes}
      </p>
      {data.resume ? (
        <button
          type="button"
          onClick={() => void starting.run("resume", async () => router.push(`/session/${data.resume?.session_id}`))}
          {...starting.buttonProps("resume")}
        >
          {starting.label("resume", copy.resume)}
        </button>
      ) : null}
      <button type="button" onClick={() => go("practice")} {...starting.buttonProps("practice")}>
        {starting.label("practice", copy.startPractice)}
      </button>
      <button type="button" className="secondary" onClick={() => go("diagnostic")} {...starting.buttonProps("diagnostic")}>
        {starting.label("diagnostic", copy.startDiagnostic)}
      </button>
      <button type="button" className="ghost" onClick={() => go("checkpoint")} {...starting.buttonProps("checkpoint")}>
        {starting.label("checkpoint", copy.startCheckpoint)}
      </button>
      {weekDotsEnabled() ? (
        <Suspense fallback={null}>
          <WeekDots learnerId={data.student_id || studentId()} practisedToday={(data.used_active_ms ?? 0) > 0} />
        </Suspense>
      ) : null}
      {starting.status}
      {starting.error ? (
        <p className="banner" role="alert">
          {starting.error}
        </p>
      ) : null}
    </main>
  );
}
