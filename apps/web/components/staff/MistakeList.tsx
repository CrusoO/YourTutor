"use client";

import { useEffect, useState } from "react";
import { classMistakes, classWarmup, type MistakeList as Mistakes, type Warmup } from "@/lib/api";
import { useCopy } from "@/lib/locale";

type Copy = Record<string, string>;
const fill = (text: string, values: Record<string, string | number>) =>
  text.replace(/\{(\w+)\}/g, (_, key: string) => String(values[key] ?? ""));

/** The class's common mistakes (counts only, never names) and a warm-up built from existing items. */
export default function MistakeList({ classId }: { classId: string }) {
  const copy = useCopy() as unknown as Copy;
  const [list, setList] = useState<Mistakes | null>(null);
  const [warmup, setWarmup] = useState<Warmup | null>(null);
  const [round, setRound] = useState(0);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setList(null);
    setWarmup(null);
    setRound(0);
    setFailed(false);
    classMistakes(classId)
      .then(setList)
      .catch(() => setFailed(true));
  }, [classId]);

  async function build() {
    const next = round + 1;
    setRound(next);
    try {
      setWarmup(await classWarmup(classId, String(next)));
      setFailed(false);
    } catch {
      setFailed(true);
    }
  }

  const min = list?.minimum_students ?? 5;
  return (
    <section className="stack" data-testid="teacher-mistakes" aria-labelledby="mistakes-title">
      <h2 id="mistakes-title">{copy.mistakesTitle}</h2>
      {failed ? <p role="alert">{copy.mistakesLoadError}</p> : null}
      {list ? <p className="muted">{fill(copy.mistakesHint, { days: list.window_days, min })}</p> : null}
      {list?.state === "not_enough_students" ? (
        <p data-testid="mistakes-not-enough">{fill(copy.mistakesNotEnough, { min })}</p>
      ) : null}
      {list?.state === "none" ? <p data-testid="mistakes-none">{fill(copy.mistakesNone, { min })}</p> : null}
      {list?.state === "ok" ? (
        <>
          <ol className="stack" data-testid="mistakes-list">
            {list.mistakes.map((row) => (
              <li key={row.misconception_id} className="card stack">
                <strong>{row.label}</strong>
                <span>
                  {fill(copy.mistakesStudents, { n: row.students })} ·{" "}
                  {fill(copy.mistakesTimes, { n: row.occurrences })}
                </span>
                <span className="muted">
                  {copy.mistakesSkill}: {row.skill_title}
                  {row.chapter ? ` (${row.chapter})` : ""}
                </span>
                {row.example ? (
                  <details>
                    <summary style={{ minHeight: 44 }}>{copy.mistakesRight}</summary>
                    <p>{row.example.stem}</p>
                    <ol>
                      {row.example.steps.map((step, i) => (
                        <li key={i}>{step}</li>
                      ))}
                    </ol>
                  </details>
                ) : null}
              </li>
            ))}
          </ol>
          <button type="button" style={{ minHeight: 44 }} onClick={() => void build()}>
            {warmup ? copy.mistakesWarmupAnother : copy.mistakesWarmupButton}
          </button>
        </>
      ) : null}

      {warmup ? (
        <div className="stack" data-testid="mistakes-warmup" aria-live="polite">
          <h3>{copy.mistakesWarmupTitle}</h3>
          {warmup.state === "no_items" ? <p>{copy.mistakesWarmupNone}</p> : null}
          {warmup.state === "ok" && warmup.short_by > 0 ? (
            <p role="status">{fill(copy.mistakesWarmupShort, { n: warmup.items.length })}</p>
          ) : null}
          {warmup.state === "ok" ? <p className="muted">{copy.mistakesWarmupNote}</p> : null}
          <ol className="stack">
            {warmup.items.map((item) => (
              <li key={item.item_id} className="card stack">
                <span className="muted">{fill(copy.mistakesWarmupAims, { label: item.targets.label })}</span>
                <p>{item.stem}</p>
                {item.options.length ? (
                  <ul>
                    {item.options.map((o) => (
                      <li key={o.id}>{o.text}</li>
                    ))}
                  </ul>
                ) : null}
                <details>
                  <summary style={{ minHeight: 44 }}>{copy.mistakesWarmupAnswer}</summary>
                  <p>{item.answer}</p>
                  <ol>
                    {item.steps.map((step, i) => (
                      <li key={i}>{step}</li>
                    ))}
                  </ol>
                </details>
              </li>
            ))}
          </ol>
        </div>
      ) : null}
    </section>
  );
}
