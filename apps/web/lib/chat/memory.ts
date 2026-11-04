import type { StudentHomeSnapshot } from "@/lib/chat/home-cache";
import type { Messages } from "@/lib/messages";

export type Memory = {
  /** What the one button does: pick up an open session, start the due review, or go on with the current topic. */
  kind: "resume" | "review" | "continue";
  text: string;
  button: string;
};

type Seen = Pick<StudentHomeSnapshot, "resume" | "due" | "started" | "current">;

/** ", Mina" for a known name, "" for none, so the line reads "Welcome back, Mina." or "Welcome back." */
const withName = (name?: string | null) => {
  const nickname = (name ?? "").trim();
  return nickname ? `, ${nickname}` : "";
};

/**
 * What Brownie says on coming back, from what the home already knows (nothing new is collected). One line and one
 * button, in this order: an open session; reviews that are due (earlier work first, TUTOR_CONSTITUTION rule 12);
 * the topic the learner was on. A first visit gets no line. No streaks, no counts of days missed, no loss language.
 */
export function memoryLine(copy: Messages, seen: Seen, name?: string | null, reviewEnabled = true): Memory | null {
  const who = withName(name);
  if (seen.resume) {
    return { kind: "resume", text: copy.chatMemoryResume.replace("{name}", who), button: copy.homeResume };
  }
  if (reviewEnabled && seen.due > 0) {
    const template = seen.due === 1 ? copy.chatMemoryReviewOne : copy.chatMemoryReviewMany;
    return { kind: "review", text: template.replace("{name}", who).replace("{n}", String(seen.due)), button: copy.chatMemoryReviewGo };
  }
  if (seen.started && seen.current) {
    const topic = seen.current.skill ?? seen.current.chapter.title;
    return { kind: "continue", text: copy.chatMemoryContinue.replace("{name}", who).replace("{topic}", topic), button: copy.chatContinue };
  }
  return null;
}
