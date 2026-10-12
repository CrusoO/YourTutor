"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  getChapterSkills,
  locale,
  startSession,
  startSkipAhead,
  type ChapterCard,
  type PathSkill,
} from "@/lib/api";

import { useStudent } from "@/lib/useStudent";
import StatusChip from "@/components/flow/StatusChip";
import { useCopy } from "@/lib/locale";

/** Chapter page: the skill path, a start button, and Skip ahead on every skill. */
export default function ChapterPage() {
  const params = useParams<{ id: string }>();
  const chapterId = decodeURIComponent(String(params?.id ?? ""));
  const router = useRouter();
  const copy = useCopy();
  const student = useStudent();
  const [chapter, setChapter] = useState<Omit<ChapterCard, "recommended"> | null>(null);
  const [skills, setSkills] = useState<PathSkill[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!student) return;
    getChapterSkills(student.student_id, chapterId)
      .then((body) => {
        setChapter(body.chapter);
        setSkills(body.skills);
      })
      .catch(() => setError(copy.loadError));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [student, chapterId]);

  async function start() {
    if (!student) return;
    setError("");
    try {
      const session = await startSession("practice", student.student_id, chapterId);
      router.push(`/session/${session.id}`);
    } catch {
      setError(copy.loadError);
    }
  }

  async function skip(skillId: string) {
    if (!student) return;
    setError("");
    try {
      const session = await startSkipAhead(student.student_id, chapterId, skillId);
      router.push(`/session/${session.id}`);
    } catch (err) {
      setError(String(err).includes("test_out_unavailable") ? copy.skipAheadUnavailable : copy.loadError);
    }
  }

  if (!student || (!chapter && !error)) return <p>…</p>;

  return (
    <main className="stack">
      <p>
        <Link href="/chapters">← {copy.chapterBack}</Link>
      </p>
      {chapter ? (
        <>
          <h1>{chapter.title}</h1>
          <StatusChip status={chapter.status} copy={copy} />
          <button type="button" onClick={start}>
            {copy.startChapter}
          </button>
          <h2>{copy.skillPathTitle}</h2>
          <ol className="path plain stack">
            {skills.map((skill) => (
              <li
                key={skill.id}
                className={`card skill${skill.current ? " current" : ""}${skill.unlocked ? "" : " dim"}`}
                data-testid={`skill-${skill.id}`}
                data-unlocked={skill.unlocked}
              >
                <div className="row">
                  <strong>{skill.title}</strong>
                  <StatusChip status={skill.status} copy={copy} />
                </div>
                <span className="muted">
                  {skill.current ? `${copy.upNext} · ` : ""}
                  {!skill.unlocked ? `${copy.locked} · ` : ""}
                  {skill.has_lesson ? copy.hasLesson : copy.practiceOnly}
                </span>
                {skill.level < 4 ? (
                  <button type="button" className="ghost" onClick={() => skip(skill.id)}>
                    {copy.skipAhead}
                  </button>
                ) : null}
              </li>
            ))}
          </ol>
          <p className="muted">{copy.skipAheadWhy}</p>
        </>
      ) : null}
      {error ? (
        <p className="banner" role="alert">
          {error}
        </p>
      ) : null}
    </main>
  );
}
