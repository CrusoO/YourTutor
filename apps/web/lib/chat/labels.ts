import type { Messages } from "@/lib/messages";
import type { ContextLike, Msg, SetupStep } from "./machine";

/** "sample_board" -> "Sample board": the fallback when the registry gives an option no display title. */
export function prettify(id: string): string {
  const spaced = id.replace(/[_-]+/g, " ").trim();
  return spaced ? spaced.charAt(0).toUpperCase() + spaced.slice(1) : id;
}

/** A board's display title in the visitor's language, then English, then a readable id. */
export function boardLabel(ctx: ContextLike | null, id: string, language: string): string {
  const titles = ctx?.curricula.find((c) => c.id === id)?.titles ?? {};
  return titles[language] ?? titles.en ?? prettify(id);
}

export function stateLabel(ctx: ContextLike | null, id: string, language: string): string {
  const titles = ctx?.states?.find((s) => s.id === id)?.titles ?? {};
  return titles[language] ?? titles.en ?? prettify(id);
}

/** The words for one option of one setup step. Class numbers go through the locale string. */
export function optionLabel(
  copy: Messages,
  ctx: ContextLike | null,
  step: SetupStep,
  value: string | number,
  language: string,
): string {
  const text = String(value);
  if (step === "grade") return copy.chatClassN.replace("{n}", text);
  if (step === "board") return boardLabel(ctx, text, language);
  if (step === "state") return stateLabel(ctx, text, language);
  return prettify(text);
}

/** What a thread message says. System bookkeeping messages say nothing (they are not shown). */
export function messageText(copy: Messages, ctx: ContextLike | null, msg: Msg, language: string): string {
  switch (msg.key) {
    case "ask_grade":
      return copy.chatAskGrade;
    case "ask_state":
      return copy.chatAskState;
    case "ask_board":
      return copy.chatAskBoard;
    case "ask_medium":
      return copy.chatAskMedium;
    case "ask_subject":
      return copy.chatAskSubject;
    case "identity_intro":
      return copy.chatIdentityIntro;
    case "user_choice":
      return msg.data?.step && msg.data.value !== undefined
        ? optionLabel(copy, ctx, msg.data.step, msg.data.value, language)
        : "";
    default:
      return "";
  }
}
