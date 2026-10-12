import { useEffect } from "react";
import type { Messages } from "@/lib/messages";
import { reasonCopy, type DoneSummary } from "@/lib/flow";
import StatusChip from "./StatusChip";

type Props = {
  copy: Messages;
  reason: string | null | undefined;
  summary: DoneSummary | null | undefined;
  /** Authored encouragement for a session that ended well (never after a failure). */
  encouragement?: string | null;
  onKeepGoing: (chapterId: string) => void;
  onChapters: () => void;
};

/** End of a session: what moved, where every skill stands, what is next. No streaks or ranks. */
export default function DoneScreen({
  copy,
  reason,
  summary,
  encouragement,
  onKeepGoing,
  onChapters,
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
          {summary.learned.length > 0 ? (
            <section className="card" aria-label={copy.doneLearned}>
              <h2>{copy.doneLearned}</h2>
              <ul className="plain">
                {summary.learned.map((row) => (
                  <li key={row.id}>
                    {row.title} <StatusChip status={row.status} copy={copy} />
                  </li>
                ))}
              </ul>
            </section>
          ) : summary.practised.length > 0 ? (
            <section className="card" aria-label={copy.donePractised}>
              <h2>{copy.donePractised}</h2>
              <ul className="plain">
                {summary.practised.map((row) => (
                  <li key={row.id}>
                    {row.title} <StatusChip status={row.status} copy={copy} />
                  </li>
                ))}
              </ul>
            </section>
          ) : (
            <p>{copy.doneNothingNew}</p>
          )}
          <section className="card" aria-label={copy.doneSkills}>
            <h2>{copy.doneSkills}</h2>
            <ul className="plain">
              {summary.skills.map((row) => (
                <li key={row.id}>
                  {row.title} <StatusChip status={row.status} copy={copy} />
                </li>
              ))}
            </ul>
          </section>
          {summary.next ? (
            <p>
              <strong>{copy.doneNext}:</strong> {summary.next.title}
            </p>
          ) : null}
          <p className="muted">
            {summary.remaining_active_minutes} {copy.doneMinutes}
          </p>
        </>
      ) : null}
      {chapterId ? (
        <button type="button" onClick={() => onKeepGoing(chapterId)}>
          {copy.doneContinue}
        </button>
      ) : null}
      <button type="button" className={chapterId ? "secondary" : undefined} onClick={onChapters}>
        {copy.doneChapters}
      </button>
    </main>
  );
}
