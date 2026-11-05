"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import type { AiCheck, AiPredict, UsableBlock } from "@/lib/lessons/ai-lesson";
import type { Evidence } from "@/lib/lessons/learning-map";
import { useCopy } from "@/lib/locale";
import { AskAbout } from "./AskAbout";
import { CheckBlock, ExplainBlock, HookBlock, PredictBlock, RecapBlock, TransferBlock, type AnswerInfo } from "./blocks";
import { LearningCard, type KeepCard } from "./LearningCard";
import { WidgetBlock } from "./widgets";

/** The blocks that need an answer before "Continue" opens. Every other block is ready as soon as it shows. */
const NEEDS_ANSWER = new Set(["predict", "check", "transfer"]);

/**
 * The interactive lesson: blocks appear one at a time, each after the student has done what it asks. Earlier
 * blocks stay on the page (with their answers) so the student can scroll back.
 */
export function LessonBlocks({
  blocks,
  prompt,
  language,
  pending = false,
  art,
  voice,
  offer,
  restFailed = false,
  keep,
  footer,
}: {
  blocks: UsableBlock[];
  prompt: string;
  language: "en" | "hi";
  /** More blocks are on their way: the student can work on what is here and Continue waits for the next. */
  pending?: boolean;
  /** A small picture shown beside block i (a prepared lesson has one for every step). */
  art?: (index: number) => ReactNode;
  /** When the learner slips more than once, Brownie offers the video (ready or still being made) or carrying on. */
  offer?: { ready: boolean; onWatch: () => void };
  /** The voice control shown under the step on screen (index of that step). */
  voice?: (index: number) => ReactNode;
  /** The rest could not be built; what is here is all there is. */
  restFailed?: boolean;
  /** Present only for a signed-in learner: the card can be kept in their account. */
  keep?: KeepCard;
  /** Shown once the lesson is over, after the follow-up box (for example, the way back to asking something else). */
  footer?: ReactNode | ((evidence: Evidence[]) => ReactNode);
}) {
  const copy = useCopy();
  const [shown, setShown] = useState(1);
  const [answered, setAnswered] = useState<ReadonlySet<number>>(new Set());
  // A right guess that was only a hunch ("not sure") is not knowing: it still gets the explanation.
  const [predictedRight, setPredictedRight] = useState<boolean | null>(null);
  const [predictedUnsure, setPredictedUnsure] = useState(false);
  const lastRef = useRef<HTMLLIElement>(null);
  const first = useRef(true);

  const current = blocks[shown - 1]!;
  const ready = !NEEDS_ANSWER.has(current.block.kind) || answered.has(shown - 1);
  const atEnd = shown === blocks.length;
  const finished = atEnd && !pending;
  const waitingForMore = atEnd && pending && ready;
  const checkAt = blocks.findIndex((b) => b.block.kind === "check");
  const canSkip = current.block.kind === "predict" && predictedRight === true && !predictedUnsure && ready && checkAt > shown;

  const mark = (index: number) => setAnswered((prev) => new Set(prev).add(index));

  // Brownie notices a run of wrong answers and offers the video: at the second, and once more at the fourth.
  const [wrongs, setWrongs] = useState<(string | null)[]>([]);
  const [handledAt, setHandledAt] = useState(0);
  const slipped = () => (idea: string | null) => setWrongs((prev) => [...prev, idea]);
  const offerStage = wrongs.length >= 4 ? 4 : wrongs.length >= 2 ? 2 : 0;
  const showOffer = Boolean(offer) && offerStage > handledAt;
  const sameIdea = wrongs.length >= 2 && wrongs[0] && wrongs.every((w) => w === wrongs[0]) ? wrongs[0] : null;

  // What each judged answer showed the first time: kept for the end-of-lesson card (this device only).
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const record = (index: number, block: AiPredict | AiCheck, info: AnswerInfo) => {
    if (info.right === null || !block.options || block.correct === null) return;
    const entry: Evidence = {
      id: String(index),
      kind: block.kind,
      question: block.kind === "predict" ? block.prompt : block.question,
      options: block.options,
      correct: block.correct,
      right: info.right,
      confidence: info.confidence,
      idea: info.idea,
    };
    setEvidence((prev) => (prev.some((e) => e.id === entry.id) ? prev : [...prev, entry]));
  };

  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    lastRef.current?.scrollIntoView?.({ block: "start", behavior: window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }, [shown]);

  return (
    <div className="flex flex-col gap-6" data-testid="lesson-blocks">
      <div
        role="progressbar"
        aria-label={`${copy.lessonStep} ${shown} ${copy.lessonOf} ${blocks.length}`}
        aria-valuemin={1}
        aria-valuemax={blocks.length}
        aria-valuenow={shown}
        className="flex items-center gap-1.5"
      >
        {blocks.map((_, i) => (
          <span key={i} className={`h-1 flex-1 rounded-full transition-colors ${i < shown ? "bg-accent" : "bg-surface-2"}`} />
        ))}
      </div>

      <ol className="m-0 flex list-none flex-col gap-8 p-0">
        {blocks.slice(0, shown).map((entry, i) => {
          const { block } = entry;
          const picture = art?.(i);
          const stacked = block.kind === "widget";
          return (
            <li key={i} ref={i === shown - 1 ? lastRef : undefined} className="scroll-mt-16">
              {picture && stacked ? <div className="mb-3 w-1/2 max-w-[11rem]">{picture}</div> : null}
              <div className={picture && !stacked ? "flex items-start gap-3" : undefined}>
                <div className={picture && !stacked ? "min-w-0 flex-1" : undefined}>
              {block.kind === "hook" ? <HookBlock block={block} /> : null}
              {block.kind === "predict" ? (
                <PredictBlock
                  block={block}
                  onWrong={slipped()}
                  onResult={(info) => {
                    setPredictedRight(info.right);
                    setPredictedUnsure(info.confidence === "unsure");
                    record(i, block, info);
                    mark(i);
                  }}
                />
              ) : null}
              {block.kind === "widget" && "run" in entry ? <WidgetBlock run={entry.run} /> : null}
              {block.kind === "explain" ? <ExplainBlock block={block} /> : null}
              {block.kind === "check" ? <CheckBlock block={block} onFirst={(info) => record(i, block, info)} onSolved={() => mark(i)} onWrong={slipped()} /> : null}
              {block.kind === "transfer" ? <TransferBlock block={block} onShown={() => mark(i)} /> : null}
              {block.kind === "recap" ? <RecapBlock block={block} /> : null}
                </div>
                {picture && !stacked ? <aside className="w-[38%] max-w-[11rem] shrink-0" aria-label="Picture for this step">{picture}</aside> : null}
              </div>
            </li>
          );
        })}
      </ol>

      {showOffer && offer ? (
        <div className="flex flex-col gap-3 rounded-2xl border border-accent bg-accent-soft p-4" role="status" data-testid="help-offer">
          <p className="m-0 text-[0.75rem] font-medium text-accent-ink">Brownie</p>
          <p className="m-0 text-[0.9375rem] leading-[1.6] text-ink">
            That has slipped {wrongs.length === 2 ? "twice" : `${wrongs.length} times`} now{sameIdea ? `, and both times it looked like the same idea: ${sameIdea}` : ", and that is completely fine"}.{" "}
            {offer.ready ? "Your video on this is ready. Would you like to watch it now, or keep going with the questions?" : "I am still putting your video together. Keep going with the questions, and it will be ready soon."}
          </p>
          <div className="flex flex-wrap gap-2">
            {offer.ready ? (
              <Button
                size="sm"
                onClick={() => {
                  setHandledAt(offerStage);
                  offer.onWatch();
                }}
              >
                Watch the video
              </Button>
            ) : null}
            <Button variant="outline" size="sm" onClick={() => setHandledAt(offerStage)}>
              Keep going with the questions
            </Button>
          </div>
        </div>
      ) : null}

      {voice ? <div data-testid="lesson-voice">{voice(shown - 1)}</div> : null}

      {waitingForMore ? (
        <p className="m-0 text-[0.875rem] text-muted" role="status" data-testid="lesson-preparing">
          {copy.lessonPreparing}
        </p>
      ) : !finished ? (
        <div className="flex flex-wrap items-center gap-3">
          <Button onClick={() => setShown((n) => n + 1)} disabled={!ready} data-testid="lesson-continue">
            {copy.lessonContinue}
          </Button>
          {canSkip ? (
            <Button variant="ghost" onClick={() => setShown(checkAt + 1)} data-testid="lesson-skip">
              {copy.lessonSkipToCheck}
            </Button>
          ) : null}
          {!ready ? <p className="m-0 text-[0.8125rem] text-muted">{copy.lessonPickFirst}</p> : null}
        </div>
      ) : (
        <>
          {restFailed ? (
            <p className="m-0 text-[0.875rem] text-muted" role="status" data-testid="lesson-rest-failed">
              {copy.lessonRestFailed}
            </p>
          ) : null}
          <LearningCard evidence={evidence} topic={prompt} keep={keep} />
          <AskAbout prompt={prompt} language={language} />
          {typeof footer === "function" ? footer(evidence) : footer}
        </>
      )}
    </div>
  );
}
