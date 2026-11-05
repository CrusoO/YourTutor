"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import type { AiCheck, AiPredict, UsableBlock } from "@/lib/lessons/ai-lesson";
import type { Evidence } from "@/lib/lessons/learning-map";
import { useCopy } from "@/lib/locale";
import { AskAbout } from "./AskAbout";
import ReadAloud from "@/components/flow/ReadAloud";
import { blockSpeech } from "@/lib/lessons/block-speech";
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
  readAloud = false,
  restFailed = false,
  keep,
  footer,
}: {
  blocks: UsableBlock[];
  prompt: string;
  language: "en" | "hi";
  /** More blocks are on their way: the student can work on what is here and Continue waits for the next. */
  pending?: boolean;
  /** Offer to read the block on screen aloud (the browser's own voice). */
  readAloud?: boolean;
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
          return (
            <li key={i} ref={i === shown - 1 ? lastRef : undefined} className="scroll-mt-16">
              {block.kind === "hook" ? <HookBlock block={block} /> : null}
              {block.kind === "predict" ? (
                <PredictBlock
                  block={block}
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
              {block.kind === "check" ? <CheckBlock block={block} onFirst={(info) => record(i, block, info)} onSolved={() => mark(i)} /> : null}
              {block.kind === "transfer" ? <TransferBlock block={block} onShown={() => mark(i)} /> : null}
              {block.kind === "recap" ? <RecapBlock block={block} /> : null}
            </li>
          );
        })}
      </ol>

      {readAloud ? (
        <div data-testid="lesson-read-aloud">
          <ReadAloud key={shown} text={blockSpeech(current.block)} lang="en" />
        </div>
      ) : null}

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
