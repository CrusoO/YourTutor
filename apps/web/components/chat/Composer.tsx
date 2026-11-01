"use client";

import { ComposerPrimitive } from "@assistant-ui/react";
import { useState } from "react";
import { Icon } from "@/components/ui/icons";
import { stepOptions } from "@/lib/chat/machine";
import { MODES_BY_ROLE, useChatApi, type Mode } from "./ChatProvider";
import styles from "./ChatHome.module.css";

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

/** The class dropdown starts at this class (the product serves the upper classes first). */
const FIRST_CLASS_SHOWN = 5;

/** Modes that are not built yet: shown, never active. */
const SOON: Mode[] = ["notes", "content"];

/**
 * The composer: a large rounded box that grows to five lines, with the role's mode chips beneath it. It is
 * a deterministic finder, not a chatbot: what is typed is matched against topics on this device and dropped.
 */
export function Composer({ docked = false }: { docked?: boolean }) {
  const { copy, role, mode, setMode, busy, ctx, dispatch } = useChatApi();
  const [empty, setEmpty] = useState(true);
  const [emptyHint, setEmptyHint] = useState(false);
  const [micHint, setMicHint] = useState(false);
  const modes = MODES_BY_ROLE[role];
  const disabled = SOON.includes(mode);
  const placeholder = copy[PLACEHOLDER[mode]];

  return (
    <div className="w-full" data-testid="composer">
      <ComposerPrimitive.Root className={`home-card flex flex-col gap-1 focus-within:border-accent ${styles.composerRoot}`}>
        {/* The mode control: plain tabs. The chosen mode is filled and carries aria-pressed; a mode that is not
            built yet is dimmed and tagged in words. */}
        <div className={`${docked && role === "visitor" ? "hidden" : "-ml-2 flex min-w-0 flex-wrap items-center gap-0.5"} ${styles.modeGroup}`} role="group" aria-label={copy.chatModes}>
          {modes.map((m) => (
            <button
              key={m}
              type="button"
              aria-pressed={mode === m}
              disabled={SOON.includes(m)}
              onClick={() => setMode(m)}
              data-testid={`mode-${m}`}
              className={`inline-flex min-h-8 w-auto cursor-pointer items-center gap-1.5 border-0 text-[0.75rem] font-normal disabled:cursor-not-allowed disabled:opacity-60 ${mode === m ? "bg-surface-2 text-ink" : "bg-transparent text-muted hover:text-ink"} ${styles.modeButton}`}
            >
              {copy[MODE_LABEL[m]]}
              {SOON.includes(m) ? <span className="rounded-full bg-neutral-soft px-1.5 py-0.5 text-[0.625rem] text-muted">{copy.chatSoon}</span> : null}
            </button>
          ))}
        </div>
        <div className="flex items-end gap-3">
          <ComposerPrimitive.Input
            onChange={(e) => {
              setEmpty(!e.target.value.trim());
              setEmptyHint(false);
              setMicHint(false);
            }}
            aria-label={placeholder}
            placeholder={placeholder}
            maxRows={5}
            rows={1}
            disabled={disabled}
            autoComplete="off"
            autoCorrect="off"
            spellCheck={false}
            data-testid="composer-input"
            className={`min-h-[3.25rem] w-full flex-1 resize-none border-0 bg-transparent py-2 font-[inherit] text-[0.9375rem] text-ink outline-none placeholder:text-muted ${styles.composerInput}`}
          />
          {/* Send always looks ready. It is disabled only when sending is impossible (a mode that is not built
              yet), and then the reason is shown in words below. An empty box gets a gentle hint instead. */}
          <button
            type="button"
            aria-disabled="true"
            aria-label={copy.chatMicLabel}
            onClick={() => setMicHint(true)}
            className="grid size-9 shrink-0 cursor-pointer place-items-center rounded-full border-0 bg-transparent text-muted hover:text-ink"
            data-testid="composer-mic"
          >
            <Icon name="mic" size={17} />
          </button>
          <button
            type="submit"
            disabled={disabled || busy}
            aria-label={copy.chatSend}
            onClick={(e) => {
              // An empty box: say what to do instead of looking dead. The form handles a real send.
              if (empty) {
                e.preventDefault();
                setEmptyHint(true);
              }
            }}
            className={`mb-1 grid size-8 shrink-0 cursor-pointer place-items-center border-0 bg-accent text-accent-fg transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:bg-neutral-soft disabled:text-muted ${styles.sendButton}`}
            data-testid="composer-send"
          >
            <Icon name="arrowUp" size={16} />
            <span className="sr-only">{copy.chatSend}</span>
          </button>
        </div>
      </ComposerPrimitive.Root>
      {disabled || emptyHint || micHint ? (
        <p role="status" className="m-0 mt-2 pl-5 text-sm text-muted" data-testid="composer-hint">
          {disabled ? copy.chatSendReasonSoon : micHint ? copy.chatMicSoon : copy.chatSendEmptyHint}
        </p>
      ) : null}
    </div>
  );
}
