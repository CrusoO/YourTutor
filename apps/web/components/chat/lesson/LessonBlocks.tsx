"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import type { UsableBlock } from "@/lib/lessons/ai-lesson";
import { useCopy } from "@/lib/locale";
import { AskAbout } from "./AskAbout";
import { CheckBlock, ExplainBlock, HookBlock, PredictBlock, RecapBlock, TransferBlock } from "./blocks";
import { WidgetBlock } from "./widgets";

/** The blocks that need an answer before "Continue" opens. Every other block is ready as soon as it shows. */
const NEEDS_ANSWER = new Set(["predict", "check", "transfer"]);

/**
 * The interactive lesson: blocks appear one at a time, each after the student has done what it asks. Earlier
 * blocks stay on the page (with their answers) so the student can scroll back.
 */
export function LessonBlocks({ blocks, prompt, language }: { blocks: UsableBlock[]; prompt: string; language: "en" | "hi" }) {
  const copy = useCopy();
  const [shown, setShown] = useState(1);
  const [answered, setAnswered] = useState<ReadonlySet<number>>(new Set());
  const [predictedRight, setPredictedRight] = useState<boolean | null>(null);
  const lastRef = useRef<HTMLLIElement>(null);
  const first = useRef(true);

  const current = blocks[shown - 1]!;
  const ready = !NEEDS_ANSWER.has(current.block.kind) || answered.has(shown - 1);
  const finished = shown === blocks.length;
  const checkAt = blocks.findIndex((b) => b.block.kind === "check");
  const canSkip = current.block.kind === "predict" && predictedRight === true && ready && checkAt > shown;

  const mark = (index: number) => setAnswered((prev) => new Set(prev).add(index));

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
                  onResult={(correct) => {
                    setPredictedRight(correct);
                    mark(i);
                  }}
                />
              ) : null}
              {block.kind === "widget" && "run" in entry ? <WidgetBlock run={entry.run} /> : null}
              {block.kind === "explain" ? <ExplainBlock block={block} /> : null}
              {block.kind === "check" ? <CheckBlock block={block} onSolved={() => mark(i)} /> : null}
              {block.kind === "transfer" ? <TransferBlock block={block} onShown={() => mark(i)} /> : null}
              {block.kind === "recap" ? <RecapBlock block={block} /> : null}
            </li>
          );
        })}
      </ol>

      {!finished ? (
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
        <AskAbout prompt={prompt} language={language} />
      )}
    </div>
  );
}
