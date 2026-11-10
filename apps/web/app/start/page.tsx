"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getContextOptions, guestStart, type ContextOptions } from "@/lib/api";

import { ADULT_GRADE, bookGrade, GUEST_GRADES } from "@/lib/chat/machine";
import StorageNotice from "@/components/StorageNotice";
import LegalLinks from "@/components/legal/LegalLinks";
import { useCopy } from "@/lib/locale";

/** Guest start: curriculum, grade, subject and language. Nothing personal is asked or stored. */
export default function StartPage() {
  const router = useRouter();
  const copy = useCopy();
  const [options, setOptions] = useState<ContextOptions | null>(null);
  const [curriculum, setCurriculum] = useState("");
  const [grade, setGrade] = useState("");
  const [subject, setSubject] = useState("");
  const [language, setLanguage] = useState("en");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getContextOptions()
      .then(setOptions)
      .catch(() => setError(copy.startError));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const allGrades = options?.curricula.find((c) => c.id === curriculum)?.grades ?? [];
  const grades = allGrades.filter((g) => GUEST_GRADES.includes(g.grade));
  const adult = grade === "adult";
  const subjects = adult
    ? [...new Map(allGrades.flatMap((g) => g.subjects).map((x) => [x.id, x])).values()]
    : (grades.find((g) => String(g.grade) === grade)?.subjects ?? []);
  const ready = Boolean(curriculum && grade && subject && language) && !busy;

  async function start() {
    setBusy(true);
    setError("");
    try {
      await guestStart({
        curriculum_id: curriculum,
        grade: adult
          ? (bookGrade(options ?? { curricula: [] }, { grade: ADULT_GRADE, board: curriculum, subject }) ?? 0)
          : Number(grade),
        subject,
        home_language: language,
        device_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      });
      router.push("/subjects");
    } catch {
      setError(copy.startError);
      setBusy(false);
    }
  }

  return (
    <main className="stack">
      <StorageNotice />
      <h1>{copy.startTitle}</h1>
      <p className="muted">{copy.startHint}</p>
      <label>
        {copy.curriculumLabel}
        <select
          value={curriculum}
          onChange={(e) => {
            setCurriculum(e.target.value);
            setGrade("");
            setSubject("");
          }}
        >
          <option value="">{copy.chooseOne}</option>
          {(options?.curricula ?? []).map((c) => (
            <option key={c.id} value={c.id}>
              {c.id}
            </option>
          ))}
        </select>
      </label>
      <label>
        {copy.gradeLabel}
        <select
          value={grade}
          disabled={!curriculum}
          onChange={(e) => {
            setGrade(e.target.value);
            setSubject("");
          }}
        >
          <option value="">{copy.chooseOne}</option>
          {grades.map((g) => (
            <option key={g.grade} value={g.grade}>
              {g.grade}
            </option>
          ))}
          <option value="adult">{copy.chatAdult}</option>
        </select>
      </label>
      <label>
        {copy.subjectLabel}
        <select value={subject} disabled={!grade} onChange={(e) => setSubject(e.target.value)}>
          <option value="">{copy.chooseOne}</option>
          {subjects.map((s) => (
            <option key={s.id} value={s.id}>
              {s.id}
            </option>
          ))}
        </select>
      </label>
      <label>
        {copy.languageLabel}
        <select value={language} onChange={(e) => setLanguage(e.target.value)}>
          {(options?.languages ?? [{ code: "en", name: "English" }]).map((l) => (
            <option key={l.code} value={l.code}>
              {l.name}
            </option>
          ))}
        </select>
      </label>
      <button type="button" disabled={!ready} onClick={start}>
        {copy.startButton}
      </button>
      {error ? <p className="banner">{error}</p> : null}
      <LegalLinks />
    </main>
  );
}
