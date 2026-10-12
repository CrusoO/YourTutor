"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  deleteFamily,
  familyExport,
  getContextOptions,
  guardianView,
  locale,
  setChildLanguage,
  setStaffToken,
  staffToken,
} from "@/lib/api";

import { isLiveLocale, useCopy } from "@/lib/locale";

type Child = { id: string; display_name: string };
type Skill = { id: string; title: string; level: number; status: string };
type View = {
  student: { id: string; display_name: string; grade: number; home_language: string };
  language: string;
  chapters: { id: string; title: string; live: boolean; status: string; skills: Skill[] }[];
  this_week: {
    learned: { skill_id: string; title: string }[];
    practised: string[];
    sessions: number;
    days_active: number;
    active_minutes: number;
    questions_answered: number;
  };
};

const STATUS_KEY: Record<string, string> = {
  not_started: "statusNotStarted",
  learning: "statusLearning",
  can_do_it: "statusCanDoIt",
  solid: "statusSolid",
  review_due: "statusReviewDue",
  coming_soon: "comingSoon",
};

/** The guardian's page: where the child is in each chapter, what changed this week. */
export default function GuardianPage() {
  const router = useRouter();
  const copy = (useCopy() as unknown as Record<string, string>);
  const [children, setChildren] = useState<Child[]>([]);
  const [current, setCurrent] = useState("");
  const [view, setView] = useState<View | null>(null);
  const [languages, setLanguages] = useState<{ code: string; name: string }[]>([]);

  useEffect(() => {
    if (!staffToken()) {
      router.push("/staff/login");
      return;
    }
    familyExport()
      .then((data) => {
        setChildren(data.students);
        setCurrent(data.students[0]?.id ?? "");
      })
      .catch(() => router.push("/staff/login"));
    getContextOptions().then((o) => setLanguages(o.languages.filter((l) => isLiveLocale(l.code))));
  }, [router]);

  useEffect(() => {
    if (current) void guardianView(current).then(setView);
  }, [current]);

  async function changeLanguage(code: string) {
    await setChildLanguage(current, code);
    setView(await guardianView(current, code));
  }

  async function download() {
    const data = await familyExport();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "yourtutor-data.json";
    link.click();
  }

  async function remove() {
    if (!window.confirm(copy.guardianDeleteConfirm)) return;
    await deleteFamily();
    setStaffToken("");
    router.push("/staff/login");
  }

  if (!view) return <p>…</p>;
  const week = view.this_week;
  const status = (key: string) => copy[STATUS_KEY[key] ?? ""] ?? key;
  return (
    <main className="stack" data-testid="guardian-page">
      <h1>{copy.guardianTitle.replace("{name}", view.student.display_name)}</h1>
      {children.length > 1 ? (
        <div className="stack">
          {children.map((child) => (
            <button
              key={child.id}
              type="button"
              className={child.id === current ? "" : "secondary"}
              onClick={() => setCurrent(child.id)}
            >
              {child.display_name}
            </button>
          ))}
        </div>
      ) : null}

      <section className="card stack" data-testid="guardian-week">
        <h2>{copy.guardianWeek}</h2>
        {week.sessions === 0 ? (
          <p>{copy.guardianNothingThisWeek}</p>
        ) : (
          <>
            <p>
              {week.days_active} {copy.guardianDays} · {week.active_minutes} {copy.guardianMinutes} ·{" "}
              {week.questions_answered} {copy.guardianQuestions}
            </p>
            <h3>{copy.guardianLearned}</h3>
            {week.learned.length ? (
              <ul>
                {week.learned.map((row) => (
                  <li key={row.skill_id}>{row.title}</li>
                ))}
              </ul>
            ) : (
              <p className="muted">{copy.guardianLearnedNone}</p>
            )}
            {week.practised.length ? (
              <p className="muted">
                {copy.guardianPractised}: {week.practised.join(", ")}
              </p>
            ) : null}
          </>
        )}
      </section>

      <section className="stack" data-testid="guardian-chapters">
        <h2>{copy.guardianChapters}</h2>
        {view.chapters.map((chapter) => (
          <div key={chapter.id} className="card stack">
            <strong>{chapter.title}</strong>
            <span className="muted">{status(chapter.status)}</span>
            {chapter.skills.length ? (
              <ul>
                {chapter.skills.map((skill) => (
                  <li key={skill.id}>
                    {skill.title}: {status(skill.status)}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ))}
      </section>

      <label className="stack">
        {copy.guardianLanguage}
        <select value={view.language} onChange={(e) => void changeLanguage(e.target.value)}>
          {languages.map((l) => (
            <option key={l.code} value={l.code}>
              {l.name}
            </option>
          ))}
        </select>
      </label>
      <button type="button" className="secondary" onClick={() => void download()}>
        {copy.guardianExport}
      </button>
      <button type="button" className="secondary" onClick={() => void remove()}>
        {copy.guardianDelete}
      </button>
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
