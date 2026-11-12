"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ui } from "@/lib/agreement-copy";
import { ApiError, startAdult } from "@/lib/agreements-api";
import { getContextOptions, keepTabSession, setStudentId, type ContextOptions } from "@/lib/api";

/** The age question for an adult learner (a declaration, or a birth year), then the board and class. */
export default function AdultStart({ accepted, version }: { accepted: string[]; version: string }) {
  const router = useRouter();
  const [options, setOptions] = useState<ContextOptions | null>(null);
  const [declared, setDeclared] = useState(false);
  const [year, setYear] = useState("");
  const [board, setBoard] = useState("");
  const [grade, setGrade] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getContextOptions()
      .then(setOptions)
      .catch(() => setError(ui.failed));
  }, []);

  const grades = options?.curricula.find((c) => c.id === board)?.grades ?? [];
  const birthYear = /^\d{4}$/.test(year.trim()) ? Number(year.trim()) : null;
  const ready = Boolean(board && grade && (declared || birthYear !== null)) && !busy;

  async function go() {
    setBusy(true);
    setError("");
    try {
      const out = await startAdult({
        version,
        accepted,
        declared_adult: declared ? true : birthYear !== null ? null : false,
        birth_year: birthYear,
        grade: Number(grade),
        board,
      });
      keepTabSession(out.token, out.student_id);
      setStudentId(out.student_id);
      router.push("/brownie-chat");
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 403 ? ui.adultNotAdult : ui.failed);
      setBusy(false);
    }
  }

  return (
    <section className="stack" data-testid="adult-start">
      <h2>{ui.adultAgeTitle}</h2>
      <p className="muted">{ui.adultAgeHint}</p>
      <label style={{ flexDirection: "row", alignItems: "center", fontWeight: 400 }}>
        <input
          type="checkbox"
          style={{ width: 24, minHeight: 24, height: 24 }}
          checked={declared}
          onChange={(e) => setDeclared(e.target.checked)}
        />
        {ui.adultDeclared}
      </label>
      <label>
        {ui.adultBirthYear}
        <input inputMode="numeric" maxLength={4} value={year} onChange={(e) => setYear(e.target.value)} />
      </label>
      <label>
        {ui.adultBoard}
        <select
          value={board}
          onChange={(e) => {
            setBoard(e.target.value);
            setGrade("");
          }}
        >
          <option value="">{ui.chooseOne}</option>
          {(options?.curricula ?? []).map((c) => (
            <option key={c.id} value={c.id}>
              {c.id}
            </option>
          ))}
        </select>
      </label>
      <label>
        {ui.adultGrade}
        <select value={grade} disabled={!board} onChange={(e) => setGrade(e.target.value)}>
          <option value="">{ui.chooseOne}</option>
          {grades.map((g) => (
            <option key={g.grade} value={g.grade}>
              {g.grade}
            </option>
          ))}
        </select>
      </label>
      {!declared && birthYear === null ? <p className="muted">{ui.adultNeedsYear}</p> : null}
      <button type="button" disabled={!ready} onClick={() => void go()}>
        {ui.adultStart}
      </button>
      {error ? <p className="banner">{error}</p> : null}
    </section>
  );
}
