"use client";

import { ComposerPrimitive } from "@assistant-ui/react";
import { Choice } from "@/components/ui/choice";
import { Icon } from "@/components/ui/icons";
import { MODES_BY_ROLE, useChatApi, type Mode } from "./ChatProvider";

const MODE_LABEL = {
  learn: "chatModeLearn",
  practise: "chatModePractise",
  revise: "chatModeRevise",
  notes: "chatModeNotes",
  class: "chatModeClass",
  alerts: "chatModeAlerts",
  content: "chatModeContent",
  progress: "chatModeProgress",
  privacy: "chatModePrivacy",
} as const;

const PLACEHOLDER = {
  learn: "chatPlaceholderLearn",
  practise: "chatPlaceholderPractise",
  revise: "chatPlaceholderRevise",
  notes: "chatPlaceholderNotes",
  class: "chatPlaceholderClass",
  alerts: "chatPlaceholderAlerts",
  content: "chatPlaceholderContent",
  progress: "chatPlaceholderProgress",
  privacy: "chatPlaceholderPrivacy",
} as const;

/** Modes that are not built yet: shown, never active. */
const SOON: Mode[] = ["notes", "content"];

/**
 * The composer: a large rounded box that grows to five lines, with the role's mode chips beneath it. It is
 * a deterministic finder, not a chatbot: what is typed is matched against topics on this device and dropped.
 */
export function Composer({ docked = false }: { docked?: boolean }) {
  const { copy, role, mode, setMode } = useChatApi();
  const modes = MODES_BY_ROLE[role];
  const disabled = SOON.includes(mode);
  const placeholder = role === "visitor" ? copy.chatPlaceholderGuest : copy[PLACEHOLDER[mode]];

  return (
    <div className={docked ? "w-full" : "w-full max-w-3xl"} data-testid="composer">
      <ComposerPrimitive.Root className="flex items-end gap-2 rounded-[1.75rem] border border-input-line bg-surface p-2 pl-5 shadow-[var(--shadow-card)] focus-within:border-accent">
        <ComposerPrimitive.Input
          aria-label={placeholder}
          placeholder={placeholder}
          maxRows={5}
          rows={1}
          disabled={disabled}
          autoComplete="off"
          autoCorrect="off"
          spellCheck={false}
          data-testid="composer-input"
          className="min-h-11 w-full flex-1 resize-none border-0 bg-transparent py-2.5 font-[inherit] text-base text-ink outline-none placeholder:text-muted"
        />
        <ComposerPrimitive.Send
          disabled={disabled}
          className="inline-flex min-h-11 w-auto cursor-pointer items-center gap-2 rounded-full border-0 bg-accent px-5 text-base font-semibold text-accent-fg disabled:cursor-not-allowed disabled:opacity-50"
          data-testid="composer-send"
        >
          <Icon name="send" />
          {copy.chatSend}
        </ComposerPrimitive.Send>
      </ComposerPrimitive.Root>
      <div className={docked && role === "visitor" ? "hidden" : "mt-3 flex flex-wrap gap-2"} role="group" aria-label={copy.chatModes}>
        {modes.map((m) => (
          <Choice
            key={m}
            selected={mode === m}
            disabled={SOON.includes(m)}
            tag={SOON.includes(m) ? copy.chatSoon : undefined}
            onClick={() => setMode(m)}
            data-testid={`mode-${m}`}
          >
            {copy[MODE_LABEL[m]]}
          </Choice>
        ))}
      </div>
    </div>
  );
}
