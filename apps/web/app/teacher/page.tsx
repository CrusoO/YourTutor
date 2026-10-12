"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  classView,
  decideReview,
  locale,
  reviewQueue,
  setStaffToken,
  staffToken,
  teacherClasses,
} from "@/lib/api";

import { useCopy } from "@/lib/locale";

type Heat = {
  skills: { id: string; title: string }[];
  students: { id: string; display_name: string; levels: Record<string, number> }[];
};
type Stuck = { students: { student_id: string; display_name: string; skill_title: string }[] };
type Alerts = {
  alerts: { id: string; display_name: string; skill_title: string; label: string; type: string }[];
};
type Review = { id: string; display_name: string; purpose: string; text: string }[];

/** Lighter for a low level, darker for a high one. A colour scale, not a score. */
function shade(level: number): string {
  const light = 96 - level * 9;
  return `hsl(150 45% ${light}%)`;
}

/** The teacher's page: only students whose family chose to share appear. */
export default function TeacherPage() {
  const router = useRouter();
  const copy = (useCopy() as unknown as Record<string, string>);
  const [classes, setClasses] = useState<{ id: string; name: string }[]>([]);
  const [current, setCurrent] = useState("");
  const [heat, setHeat] = useState<Heat | null>(null);
  const [stuck, setStuck] = useState<Stuck | null>(null);
  const [alerts, setAlerts] = useState<Alerts | null>(null);
  const [review, setReview] = useState<Review>([]);

  useEffect(() => {
    if (!staffToken()) {
      router.push("/staff/login");
      return;
    }
    teacherClasses()
      .then((data) => {
        setClasses(data.classes);
        setCurrent(data.classes[0]?.id ?? "");
      })
      .catch(() => router.push("/staff/login"));
    void reviewQueue().then((data) => setReview(data.items));
  }, [router]);

  useEffect(() => {
    if (!current) return;
    void classView(current, "heatmap").then(setHeat);
    void classView(current, "stuck").then(setStuck);
    void classView(current, "alerts").then(setAlerts);
  }, [current]);

  async function decide(id: string, decision: "ok" | "bad") {
    await decideReview(id, decision);
    setReview((rows) => rows.filter((row) => row.id !== id));
  }

  return (
    <main className="stack" data-testid="teacher-page">
      <h1>{copy.teacherTitle}</h1>
      {classes.length > 1 ? (
        <div className="stack">
          {classes.map((klass) => (
            <button
              key={klass.id}
              type="button"
              className={klass.id === current ? "" : "secondary"}
              onClick={() => setCurrent(klass.id)}
            >
              {klass.name}
            </button>
          ))}
        </div>
      ) : null}

      <section className="stack" data-testid="teacher-heatmap">
        <h2>{copy.teacherHeatmap}</h2>
        <p className="muted">{copy.teacherHeatmapHint}</p>
        {heat && heat.students.length === 0 ? <p>{copy.teacherNoStudents}</p> : null}
        {heat && heat.students.length ? (
          <div style={{ overflowX: "auto" }} tabIndex={0} role="region" aria-label={copy.teacherHeatmap}>
            <table>
              <thead>
                <tr>
                  <th />
                  {heat.skills.map((skill, index) => (
                    <th key={skill.id} title={skill.title}>
                      {index + 1}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {heat.students.map((student) => (
                  <tr key={student.id}>
                    <th scope="row">{student.display_name}</th>
                    {heat.skills.map((skill) => {
                      const level = student.levels[skill.id] ?? 0;
                      return (
                        <td
                          key={skill.id}
                          style={{ background: shade(level), textAlign: "center", minWidth: 28 }}
                          aria-label={`${student.display_name}, ${skill.title}: level ${level}`}
                        >
                          {level}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
            <ol className="muted">
              {heat.skills.map((skill) => (
                <li key={skill.id}>{skill.title}</li>
              ))}
            </ol>
          </div>
        ) : null}
      </section>

      <section className="stack" data-testid="teacher-stuck">
        <h2>{copy.teacherStuck}</h2>
        {stuck && stuck.students.length === 0 ? <p>{copy.teacherStuckNone}</p> : null}
        <ul>
          {stuck?.students.map((row) => (
            <li key={row.student_id}>
              {row.display_name}: {row.skill_title}
            </li>
          ))}
        </ul>
      </section>

      <section className="stack" data-testid="teacher-alerts">
        <h2>{copy.teacherAlerts}</h2>
        {alerts && alerts.alerts.length === 0 ? <p>{copy.teacherAlertsNone}</p> : null}
        <ul>
          {alerts?.alerts.map((row) => (
            <li key={row.id}>
              {row.display_name}: {row.skill_title} — {row.label}
            </li>
          ))}
        </ul>
      </section>

      <section className="stack" data-testid="teacher-review">
        <h2>{copy.teacherReview}</h2>
        {review.length === 0 ? <p>{copy.teacherReviewNone}</p> : null}
        {review.map((row) => (
          <div key={row.id} className="card stack">
            <span className="muted">
              {row.display_name} · {row.purpose}
            </span>
            <p>{row.text}</p>
            <button type="button" onClick={() => void decide(row.id, "ok")}>
              {copy.teacherReviewOk}
            </button>
            <button type="button" className="secondary" onClick={() => void decide(row.id, "bad")}>
              {copy.teacherReviewBad}
            </button>
          </div>
        ))}
      </section>
      <button
        type="button"
        className="secondary"
        onClick={() => {
          setStaffToken("");
          router.push("/staff/login");
        }}
      >
        {copy.staffSignOut}
      </button>
    </main>
  );
}
