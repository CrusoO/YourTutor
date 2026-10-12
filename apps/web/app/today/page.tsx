"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ensureDevStudent, skipLogin } from "@/lib/dev-auth";
import { setStudentId, startSession, studentId, today } from "@/lib/api";

import { useCopy } from "@/lib/locale";

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
  const [error, setError] = useState("");

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

  async function go(type: string) {
    setError("");
    try {
      const sid = data?.student_id || studentId();
      const session = await startSession(type, sid);
      router.push(`/session/${session.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start");
    }
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
        <button type="button" onClick={() => router.push(`/session/${data.resume?.session_id}`)}>
          {copy.resume}
        </button>
      ) : null}
      <button type="button" onClick={() => go("practice")}>
        {copy.startPractice}
      </button>
      <button type="button" className="secondary" onClick={() => go("diagnostic")}>
        {copy.startDiagnostic}
      </button>
      <button type="button" className="ghost" onClick={() => go("checkpoint")}>
        {copy.startCheckpoint}
      </button>
      {error ? <p className="banner">{error}</p> : null}
    </main>
  );
}
