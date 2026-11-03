"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { openGroup, type GroupLesson } from "@/lib/api";
import { usableBlocks, type UsableBlock } from "@/lib/lessons/ai-lesson";
import { useCopy } from "@/lib/locale";
import { useChatApi } from "../ChatProvider";
import { LessonBlocks } from "./LessonBlocks";
import { SendResults } from "./SendResults";

/**
 * A lesson someone shared by link. It is the lesson they generated and checked, shown as it is: no model is
 * asked, so it opens at once. At the end the learner may choose to send how they did, with no name.
 */
export function GroupLessonBody({ code }: { code: string }) {
  const copy = useCopy();
  const { closeLesson } = useChatApi();
  const [state, setState] = useState<"loading" | "missing" | { group: GroupLesson; blocks: UsableBlock[] }>("loading");

  useEffect(() => {
    let live = true;
    openGroup(code)
      .then((group) => {
        if (!live) return;
        const blocks = usableBlocks({ kind: "lesson", level: "", objectives: [], blocks: group.blocks });
        setState(blocks ? { group, blocks } : "missing");
      })
      .catch(() => live && setState("missing"));
    return () => {
      live = false;
    };
  }, [code]);

  const leave = () => {
    closeLesson();
    requestAnimationFrame(() => document.querySelector<HTMLTextAreaElement>('[data-testid="composer-input"]')?.focus());
  };

  return (
    <div className="flex min-h-0 w-full flex-1 justify-center overflow-y-auto px-4 pb-8 pt-2 lg:pt-8" data-testid="group-lesson">
      <article className="flex w-full max-w-[40rem] min-w-0 flex-col gap-7" aria-busy={state === "loading"}>
        {state === "missing" ? (
          <div className="flex flex-col gap-4" data-testid="group-missing">
            <p className="m-0 rounded-2xl border border-line bg-surface px-4 py-3 text-[0.9375rem] text-ink" role="status">
              {copy.groupMissing}
            </p>
            <div>
              <Button onClick={leave}>{copy.lessonAskElse}</Button>
            </div>
          </div>
        ) : state === "loading" ? (
          <p className="m-0 text-[0.9375rem] text-muted" role="status">
            {copy.lessonWriting}
          </p>
        ) : (
          <>
            <header className="flex flex-col gap-2">
              <div className="flex items-center justify-between gap-3">
                <p className="m-0 text-[0.75rem] text-muted">{copy.groupShared}</p>
                <Button variant="ghost" size="sm" onClick={leave} data-testid="lesson-new-top">
                  {copy.lessonNewQuestion}
                </Button>
              </div>
              <p className="m-0 break-words text-[0.9375rem] text-ink" data-testid="lesson-prompt">
                {state.group.prompt}
              </p>
              <p className="m-0 text-[0.75rem] text-muted" data-testid="group-note">
                {copy.groupNote}
              </p>
            </header>
            <LessonBlocks
              blocks={state.blocks}
              prompt={state.group.prompt}
              language={state.group.language}
              footer={(evidence) => (
                <div className="flex flex-col gap-4">
                  <SendResults code={state.group.code} evidence={evidence} open={state.group.results_open} closed={state.group.closed} />
                  <div>
                    <Button onClick={leave} data-testid="lesson-new">
                      {copy.lessonAskElse}
                    </Button>
                  </div>
                </div>
              )}
            />
          </>
        )}
      </article>
    </div>
  );
}
