import type { AiBlock } from "./ai-lesson";

const end = (s: string): string => (/[.?!]$/.test(s.trim()) ? s.trim() : `${s.trim()}.`);
const join = (parts: (string | undefined)[]): string => parts.filter((p): p is string => Boolean(p && p.trim())).map(end).join(" ");

/** The words to read aloud for one lesson block. Pure text; a widget says only what to notice. */
export function blockSpeech(block: AiBlock): string {
  switch (block.kind) {
    case "hook":
      return join([block.text, block.question]);
    case "predict":
      return join([block.prompt, ...(block.options ?? [])]);
    case "explain":
      return join([block.text, block.analogy]);
    case "check":
      return join([block.question, ...block.options]);
    case "transfer":
      return join([block.scenario, block.question]);
    case "recap":
      return join([...block.three_bullets, block.spaced_review_question]);
    case "widget":
      return join([block.what_to_notice]);
  }
}
