import { useEffect } from "react";
import type { Messages } from "@/lib/messages";
import { reasonCopy, type DoneSummary } from "@/lib/flow";
import { fill, flowEn } from "@/lib/flow-copy";
import StatusChip from "./StatusChip";

type Props = {
  copy: Messages;
  reason: string | null | undefined;
  summary: DoneSummary | null | undefined;
  /** Authored encouragement for a session that ended well (never after a failure). */
  encouragement?: string | null;
  onKeepGoing: (chapterId: string) => void;
  onChapters: () => void;
  /** "Done for today": leave the flow. Falls back to the chapter list. */
  onFinish?: () => void;
};

/** End of a session: what moved, where every skill stands, what is next. No streaks or ranks. */
export default function DoneScreen({
  copy,
  reason,
  summary,
  encouragement,
  onKeepGoing,
  onChapters,
  onFinish,
}: Props) {
  const chapterId = summary?.chapter?.id ?? summary?.recommended_chapter ?? null;

  // Inside the workspace panel, tell the chat that this workflow ended (titles only, no answers).
  useEffect(() => {
    if (typeof window === "undefined" || window.name !== "yt-embed" || window.parent === window) return;
    const row = summary?.learned[0] ?? summary?.practised[0];
    window.parent.postMessage(
      {
        type: "yt:done",
        summary: {
          skill: row?.title ?? summary?.chapter?.title,
          status: row?.status ?? summary?.chapter?.status,
          next: summary?.next?.title,
        },
      },
      window.location.origin,
    );
  }, [summary]);

  const moved = summary?.learned.length ? summary.learned : (summary?.practised ?? []);
  const learnedLine = summary?.learned.length ? flowEn.doneMoved : flowEn.donePractisedLine;
  const learnedMore = summary?.learned.length ? flowEn.doneMovedMore : flowEn.donePractisedMore;

  return (
    <main className="stack done">
      <h1>{copy.doneTitle}</h1>
      <p className="muted">{reasonCopy(copy, reason)}</p>
      {encouragement ? (
        <p className="banner good" data-testid="encouragement">
          {encouragement}
        </p>
      ) : null}
      {summary ? (
        <>
          {moved.length > 0 ? (
            <p data-testid="done-moved">
              {moved.length === 1
                ? fill(learnedLine, { title: moved[0].title })
                : fill(learnedMore, { title: moved[0].title, n: moved.length - 1 })}
            </p>
          ) : null}
          {summary.next ? (
            <p>
              <strong>{copy.doneNext}:</strong> {summary.next.title}
            </p>
          ) : null}
          <p className="muted">{fill(flowEn.doneMinutesLeft, { n: summary.remaining_active_minutes })}</p>
        </>
      ) : null}
      <p className="muted" data-testid="done-tomorrow">
        {flowEn.doneTomorrow}
      </p>
      <button type="button" onClick={onFinish ?? onChapters} data-testid="done-finish">
        {flowEn.doneFinish}
      </button>
      {chapterId ? (
        <button type="button" className="secondary" onClick={() => onKeepGoing(chapterId)} data-testid="done-one-more">
          {flowEn.doneOneMore}
        </button>
      ) : null}
      <details className="card" data-testid="done-covered">
        <summary>{flowEn.doneSeeCovered}</summary>
        {summary ? (
          <section aria-label={copy.doneSkills}>
            <h2>{copy.doneSkills}</h2>
            <ul className="plain">
              {summary.skills.map((row) => (
                <li key={row.id}>
                  {row.title} <StatusChip status={row.status} copy={copy} />
                </li>
              ))}
            </ul>
          </section>
        ) : null}
        <button type="button" className="secondary" onClick={onChapters}>
          {copy.doneChapters}
        </button>
      </details>
    </main>
  );
}
