/**
 * Quick start (Plan A, slice A1): a first visit asks only the class and the subject.
 *
 * Board, state and study language are not asked on the first visit. The API still needs a board to pick the
 * book, so the one default lives here and nowhere else. It is an internal content tag: it is never shown to a
 * student and says nothing about who runs the content.
 */
import { answerOnboarding, startSession, studentId } from "@/lib/api";
import type { ContextLike, Setup } from "@/lib/chat/machine";

/** The content tag used when the visitor has not chosen a board. Internal only. */
export const QUICK_START_DEFAULT_BOARD = "cbse";

/** The registry narrowed to the default board, so a guest is offered only what that board really teaches. */
export function quickContext(ctx: ContextLike): ContextLike {
  const preferred = ctx.curricula.find((c) => c.id === QUICK_START_DEFAULT_BOARD);
  return preferred ? { ...ctx, curricula: [preferred] } : ctx;
}

/** The board to start in: the default if it has the class and subject, else the first board that does. */
export function quickBoard(ctx: ContextLike, setup: Pick<Setup, "grade" | "subject">): string | undefined {
  const has = (c: ContextLike["curricula"][number]) =>
    c.grades.some(
      (g) =>
        (setup.grade === undefined || setup.grade === 0 || g.grade === setup.grade) &&
        (setup.subject === undefined || g.subjects.some((s) => s.id === setup.subject)),
    );
  const preferred = ctx.curricula.find((c) => c.id === QUICK_START_DEFAULT_BOARD && has(c));
  return (preferred ?? ctx.curricula.find(has))?.id;
}

/**
 * Start the first question for a guest who was just created: the warm-up when it is on offer, else a practice
 * session. Returns the session id; the caller decides how to show it.
 */
export async function startFirstQuestion(offer: unknown): Promise<string> {
  let type = "practice";
  if (offer) type = (await answerOnboarding("warmup")).next.session_type;
  const session = await startSession(type, studentId());
  return String(session.id);
}
