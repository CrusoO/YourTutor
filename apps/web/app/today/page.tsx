"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ensureDevStudent, skipLogin } from "@/lib/dev-auth";
import { getChapters, setStudentId, startSession, studentId, today } from "@/lib/api";

import { useCopy } from "@/lib/locale";
import { prefetchSession, useStarting } from "@/lib/useStarting";

type Today = {
  student_id: string;
  display_name: string;
  goal_minutes: number;
  remaining_active_minutes: number;
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
      {starting.status}
      {starting.error ? (
        <p className="banner" role="alert">
          {starting.error}
        </p>
      ) : null}
    </main>
  );
}
