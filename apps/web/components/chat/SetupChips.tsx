"use client";

import { Choice } from "@/components/ui/choice";
import { nextStep, stepOptions, type SetupStep } from "@/lib/chat/machine";
import { optionLabel } from "@/lib/chat/labels";
import { locale } from "@/lib/api";
import { useChatApi } from "./ChatProvider";

const ASK = { grade: "chatAskGrade", state: "chatAskState", board: "chatAskBoard", medium: "chatAskMedium", subject: "chatAskSubject" } as const;

/** The question being asked right now, as tappable chips. An option without live content says "coming soon". */
export function SetupChips() {
  const { chat, ctx, copy, dispatch } = useChatApi();
  if (!ctx || chat.phase !== "context") return null;
  const step: SetupStep | null = nextStep(ctx, chat.setup);
  if (!step) return null;
  const options = stepOptions(ctx, chat.setup, step);
  return (
    <div className="flex flex-wrap gap-2 pl-11" role="group" aria-label={copy[ASK[step]]} data-testid={`setup-${step}`}>
      {options.map((option) => (
        <Choice
          key={option.value}
          disabled={!option.available}
          tag={option.available ? undefined : copy.chatSoon}
          onClick={() => dispatch({ type: "pick", step, value: option.value })}
          data-testid={`choice-${step}-${option.value}`}
        >
          {optionLabel(copy, ctx, step, option.value, locale())}
        </Choice>
      ))}
    </div>
  );
}

/** Earlier answers can be changed by tapping them: the later questions are asked again. */
export function EditableAnswers() {
  const { chat, ctx, copy, dispatch } = useChatApi();
  if (!ctx || chat.phase !== "identity") return null;
  const entries = (Object.entries(chat.setup) as [SetupStep, string | number][]).filter(([, v]) => v !== undefined);
  return (
    <ul className="m-0 flex list-none flex-wrap gap-2 p-0 pl-11" aria-label={copy.chatBack}>
      {entries.map(([step, value]) => (
        <li key={step}>
          <button
            type="button"
            className="min-h-12 w-auto cursor-pointer rounded-full border border-line bg-surface px-3 text-sm font-semibold text-ink hover:bg-surface-2"
            onClick={() => dispatch({ type: "pick", step, value: String(value) })}
            data-testid={`edit-${step}`}
          >
            {optionLabel(copy, ctx, step, value, locale())}
          </button>
        </li>
      ))}
    </ul>
  );
}
