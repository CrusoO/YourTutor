"use client";

import { useState } from "react";
import { ApiError, decideItem, type ReviewCard, type ReviewDecision } from "@/lib/api";
import { useCopy } from "@/lib/locale";

type Copy = Record<string, string>;
const fill = (text: string, values: Record<string, string | number>) =>
  text.replace(/\{(\w+)\}/g, (_, key: string) => String(values[key] ?? ""));

/** One item: what a reviewer needs to judge it, and the three decisions. */
export default function ReviewItemCard({ card, onDecided }: { card: ReviewCard; onDecided: (card: ReviewCard) => void }) {
  const copy = useCopy() as unknown as Copy;
  const [note, setNote] = useState(card.my_decision?.note ?? "");
  const [problem, setProblem] = useState("");
  const verdict = { verified: copy.reviewVerified, unchecked: copy.reviewUnchecked, mismatch: copy.reviewMismatch }[
    card.verification.state
  ];

  async function decide(decision: ReviewDecision) {
    if (decision !== "approve" && !note.trim()) {
      setProblem(copy.reviewNeedNote);
      return;
    }
    setProblem("");
    try {
      onDecided(await decideItem(card.id, { content_hash: card.content_hash, decision, note: note.trim() || undefined }));
    } catch (error) {
      setProblem(error instanceof ApiError && error.status === 409 ? copy.reviewStale : copy.reviewFailed);
    }
  }

  return (
    <article className="card stack" data-testid="review-card" aria-labelledby={`stem-${card.id}`}>
      <span className="muted">{card.id}</span>
      <p id={`stem-${card.id}`}>{card.stem}</p>
      {card.hindi.stem ? (
        <p lang="hi">
          <strong>{copy.reviewHindi}:</strong> {card.hindi.stem}
        </p>
      ) : null}
      <p>
        <strong>{copy.reviewAnswer}:</strong> {card.answer_text ?? card.answer}
        <br />
        <span data-testid="review-verdict" data-state={card.verification.state}>
          {verdict}
        </span>
      </p>
      {card.wrong_options.length ? (
        <>
          <h3>{copy.reviewWrong}</h3>
          <ul>
            {card.wrong_options.map((option) => (
              <li key={option.answer}>
                {option.text}: {option.misconceptions.join(", ") || copy.reviewNoMisconception}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      <p data-testid="review-count">
        {fill(copy.reviewCount, { n: card.approvals, total: card.approvals_needed })}
        {card.my_decision ? ` · ${fill(copy.reviewMine, { decision: card.my_decision.decision })}` : ""}
      </p>
      {card.notes.length ? (
        <ul>
          {card.notes.map((row, index) => (
            <li key={index}>
              {row.reviewer} ({row.decision}): {row.note}
            </li>
          ))}
        </ul>
      ) : null}
      <label>
        {copy.reviewNote}
        <textarea value={note} onChange={(event) => setNote(event.target.value)} rows={2} />
      </label>
      {problem ? <p role="alert">{problem}</p> : null}
      <button type="button" onClick={() => void decide("approve")}>
        {copy.reviewApprove}
      </button>
      <button type="button" className="secondary" onClick={() => void decide("fix")}>
        {copy.reviewFix}
      </button>
      <button type="button" className="secondary" onClick={() => void decide("reject")}>
        {copy.reviewReject}
      </button>
    </article>
  );
}
