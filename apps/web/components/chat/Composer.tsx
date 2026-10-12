"use client";

import { ComposerPrimitive, useAui, useAuiState } from "@assistant-ui/react";
import { useState } from "react";
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
  const { copy, role, mode, setMode, busy } = useChatApi();
  const aui = useAui();
  const text = useAuiState((state) => state.composer.text);
  const [emptyHint, setEmptyHint] = useState(false);
  const modes = MODES_BY_ROLE[role];
  const disabled = SOON.includes(mode);
  const placeholder = role === "visitor" ? copy.chatPlaceholderGuest : copy[PLACEHOLDER[mode]];

  return (
    <div className={docked ? "w-full" : "w-full max-w-3xl"} data-testid="composer">
      <ComposerPrimitive.Root className="flex items-end gap-2 rounded-[1.75rem] border border-input-line bg-surface p-2 pl-5 shadow-[var(--shadow-card)] focus-within:border-accent">
        <ComposerPrimitive.Input
          onChange={() => setEmptyHint(false)}
          aria-label={placeholder}
          placeholder={placeholder}
          maxRows={5}
          rows={1}
          disabled={disabled}
          autoComplete="off"
          autoCorrect="off"
          spellCheck={false}
          data-testid="composer-input"
          className="min-h-12 w-full flex-1 resize-none border-0 bg-transparent py-2.5 font-[inherit] text-base text-ink outline-none placeholder:text-muted"
        />
        {/* Send always looks ready. It is disabled only when sending is impossible (a mode that is not built
            yet), and then the reason is shown in words below. An empty box gets a gentle hint instead. */}
        <button
          type="button"
          disabled={disabled || busy}
          onClick={() => {
            if (!text.trim()) return setEmptyHint(true);
            setEmptyHint(false);
            aui.composer().send();
          }}
          className="inline-flex min-h-12 w-auto cursor-pointer items-center gap-2 rounded-full border-0 bg-accent px-5 text-base font-semibold text-accent-fg transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:bg-neutral-soft disabled:text-muted"
          data-testid="composer-send"
        >
          <Icon name="send" />
          {copy.chatSend}
        </button>
      </ComposerPrimitive.Root>
      {disabled || emptyHint ? (
        <p role="status" className="m-0 mt-2 pl-5 text-sm text-muted" data-testid="composer-hint">
          {disabled ? copy.chatSendReasonSoon : copy.chatSendEmptyHint}
        </p>
      ) : null}
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
