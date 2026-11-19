"use client";

import type { Messages } from "@/lib/messages";
import type { Way } from "@/lib/session/ways";

const LABEL: Record<Way, keyof Messages> = {
  picture: "wayPicture",
  steps: "waySteps",
  worked: "wayWorked",
  video: "wayVideo",
};

/**
 * "Want to try it another way?": the kinds of help Brownie thinks may suit this mistake, best first.
 * Choosing one is the student's call; nothing is forced and nothing is graded.
 */
export function AnotherWay({
  copy,
  ways,
  busy,
  onChoose,
}: {
  copy: Messages;
  ways: Way[];
  busy: boolean;
  onChoose: (way: Way) => void;
}) {
  if (ways.length === 0) return null;
  return (
    <section className="stack" data-testid="another-way" aria-label={copy.anotherWayTitle}>
      <h2>{copy.anotherWayTitle}</h2>
      <p className="muted">{copy.anotherWayNote}</p>
      {ways.map((way, index) => (
        <button
          key={way}
          type="button"
          className={index === 0 ? "secondary" : "ghost"}
          disabled={busy}
          data-testid={`way-${way}`}
          onClick={() => onChoose(way)}
        >
          {copy[LABEL[way]]}
        </button>
      ))}
    </section>
  );
}
