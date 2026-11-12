"use client";

import Link from "next/link";

/** The action types that must show a question. If one arrives with no question text, the screen explains itself. */
const QUESTION_TYPES = new Set(["show_item", "similar_item", "warmup_item", "check_your_work", "hint"]);

type Shown = { type: string; text?: string | null; item?: { stem?: string; prediction?: string; options?: unknown[] } | null };

export function hasNoQuestion(action: Shown): boolean {
  const item = action.item;
  if (action.type === "predict") return !(action.text ?? "").trim() && !(item?.prediction ?? "").trim();
  if (action.type === "worked_example") return !(action.text ?? "").trim() && !(item?.stem ?? "").trim();
  if (!QUESTION_TYPES.has(action.type)) return false;
  return !item || (!(item.stem ?? "").trim() && !(item.options ?? []).length);
}

const COPY = {
  noQuestionTitle: "This question did not load",
  noQuestionBody:
    "Brownie could not find the question for this step. That is a problem on our side, not something you did. Nothing you did before is lost.",
  gapTitle: "This part is not ready yet",
  gapBody: "There is no practice for this step yet. We are still adding it. You can ask Brownie about something else.",
  next: "What you can do now",
  chat: "Back to the chat",
  chapters: "See the chapters",
} as const;

/**
 * Shown instead of a bare answer box when a practice step has no question to show, or when the step has no
 * content yet. It says what happened in plain words and gives two ways forward.
 */
export default function BlockedState({ kind }: { kind: "no_question" | "content_gap" }) {
  const gap = kind === "content_gap";
  return (
    <main className="stack column" data-testid="blocked-state" data-kind={kind}>
      <h1>{gap ? COPY.gapTitle : COPY.noQuestionTitle}</h1>
      <p role="status">{gap ? COPY.gapBody : COPY.noQuestionBody}</p>
      <h2 className="muted" style={{ fontSize: "1rem" }}>{COPY.next}</h2>
      <div className="stack">
        <Link href="/brownie-chat" className="btn-link" data-testid="blocked-chat" style={linkButton(true)}>
          {COPY.chat}
        </Link>
        <Link href="/chapters" data-testid="blocked-chapters" style={linkButton(false)}>
          {COPY.chapters}
        </Link>
      </div>
    </main>
  );
}

function linkButton(primary: boolean): React.CSSProperties {
  return {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    minHeight: 48,
    borderRadius: 12,
    fontWeight: 700,
    textDecoration: "none",
    border: primary ? "none" : "1px solid var(--c-input-line)",
    background: primary ? "var(--c-accent)" : "var(--c-surface-2)",
    color: primary ? "var(--c-accent-fg)" : "var(--c-text)",
  };
}
