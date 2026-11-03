"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { calibration, clearSaved, loadSaved, rotated, saveLesson, summarise, type Evidence, type SavedLesson } from "@/lib/lessons/learning-map";
import { useCopy } from "@/lib/locale";
import { BlockTitle, Choice, Note } from "./blocks";

/** Ask one idea again with the options in a different order, so it checks the idea and not the position. */
function RetestRow({ item }: { item: Evidence }) {
  const copy = useCopy();
  const [result, setResult] = useState<"right" | "wrong" | null>(null);
  const order = rotated(item.options.map((text, index) => ({ text, index })));
  return (
    <li className="flex flex-col gap-2" data-testid="retest-row">
      <p className="m-0 text-[0.9375rem] text-ink">{item.question}</p>
      <div className="flex flex-col gap-2" role="group" aria-label={item.question}>
        {order.map((option) => (
          <Choice
            key={option.index}
            state={result === null ? "idle" : option.index === item.correct ? "right" : "idle"}
            disabled={result !== null}
            onClick={() => setResult(option.index === item.correct ? "right" : "wrong")}
          >
            {option.text}
          </Choice>
        ))}
      </div>
      {result ? <Note tone={result === "right" ? "good" : "miss"}>{result === "right" ? copy.lessonRetestNow : copy.lessonRetestStill}</Note> : null}
    </li>
  );
}

/** How a signed-in learner keeps the card in their account: given the device record, and clearing it again. */
export type KeepCard = { save: (records: SavedLesson[]) => Promise<unknown>; clear: () => Promise<unknown> };

/**
 * What the learner showed in this lesson: what went right, what is shaky, how well they read themselves,
 * and a second go at anything they were sure about and got wrong (those return after a week if not
 * revisited). It is kept on this device only, and can be cleared here.
 */
export function LearningCard({ evidence, topic, keep }: { evidence: Evidence[]; topic: string; keep?: KeepCard }) {
  const copy = useCopy();
  const [cleared, setCleared] = useState(false);
  const [kept, setKept] = useState<"idle" | "saving" | "kept" | "failed">("idle");
  const saved = useRef(false);
  const summary = summarise(evidence);
  const line = calibration(summary);

  useEffect(() => {
    if (saved.current || evidence.length === 0) return;
    saved.current = true;
    saveLesson(topic, evidence);
  }, [evidence, topic]);

  if (evidence.length === 0) return null;
  const label = (e: Evidence) =>
    e.right ? copy.lessonCardRight : e.confidence === "sure" ? copy.lessonCardSureWrong : copy.lessonCardShaky;

  return (
    <section className="flex flex-col gap-4 border-0 border-t border-line pt-6" aria-labelledby="learning-card-title" data-testid="learning-card">
      <h2 id="learning-card-title" className="m-0 text-[1.0625rem] font-medium text-ink">
        {copy.lessonCardTitle}
      </h2>
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {evidence.map((e) => (
          <li key={e.id} className="flex flex-col gap-0.5 rounded-xl bg-surface-2 px-4 py-2.5 text-[0.875rem] text-ink" data-testid="learning-row" data-state={e.right ? "right" : e.confidence === "sure" ? "sure-wrong" : "shaky"}>
            <span>
              <strong>{label(e)}</strong> · {e.question}
            </span>
            {!e.right && e.idea ? (
              <span className="text-muted">
                {copy.lessonIdeaBehind} {e.idea}
              </span>
            ) : null}
          </li>
        ))}
      </ul>
      {line === "good" ? <p className="m-0 text-[0.875rem] text-ink" data-testid="calibration">{copy.lessonCardGood}</p> : null}
      {line === "overconfident" ? (
        <p className="m-0 text-[0.875rem] text-ink" data-testid="calibration">
          {copy.lessonCardOverconfident.replace("{n}", String(summary.sureButWrong.length))}
        </p>
      ) : null}
      {summary.sureButWrong.length > 0 ? (
        <div className="flex flex-col gap-3" data-testid="retest">
          <BlockTitle>{copy.lessonRetestTitle}</BlockTitle>
          <ul className="m-0 flex list-none flex-col gap-5 p-0">
            {summary.sureButWrong.map((e) => (
              <RetestRow key={e.id} item={e} />
            ))}
          </ul>
        </div>
      ) : null}
      <div className="flex flex-wrap items-center gap-3">
        <p className="m-0 text-[0.75rem] text-muted" data-testid="learning-where">
          {cleared ? (kept === "kept" ? copy.lessonCardClearedAll : copy.lessonCardCleared) : kept === "kept" ? copy.lessonCardKept : kept === "failed" ? copy.lessonCardKeepFailed : copy.lessonCardOnDevice}
        </p>
        {keep && !cleared && kept !== "kept" ? (
          <Button
            variant="outline"
            size="sm"
            data-testid="learning-keep"
            disabled={kept === "saving"}
            onClick={() => {
              setKept("saving");
              keep
                .save(loadSaved())
                .then(() => setKept("kept"))
                .catch(() => setKept("failed"));
            }}
          >
            {copy.lessonCardKeep}
          </Button>
        ) : null}
        {cleared ? null : (
          <Button
            variant="ghost"
            size="sm"
            data-testid="learning-clear"
            onClick={() => {
              clearSaved();
              setCleared(true);
              if (kept === "kept") void keep?.clear().catch(() => undefined);
            }}
          >
            {copy.lessonCardClear}
          </Button>
        )}
      </div>
    </section>
  );
}
