"use client";

import { ComposerPrimitive } from "@assistant-ui/react";
import { useState } from "react";
import { Icon } from "@/components/ui/icons";
import { stepOptions } from "@/lib/chat/machine";
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
  const placeholder = role === "visitor" ? copy.chatPlaceholderGuest : copy[PLACEHOLDER[mode]];

  return (
    <div className={docked ? "w-full" : "w-full max-w-3xl"} data-testid="composer">
      <ComposerPrimitive.Root className="home-card flex flex-col gap-2 rounded-[1.75rem] p-3 pl-5 shadow-[var(--shadow-card)] focus-within:border-accent">
        {/* Visitors pick their class here; choosing one starts the setup at the next question. */}
        {role === "visitor" && !docked && ctx ? (
          <div className="flex items-center" data-testid="class-picker">
            <label className="sr-only" htmlFor="class-select">
              {copy.chatClassPick}
            </label>
            <select
              id="class-select"
              value=""
              onChange={(e) => {
                if (!e.target.value) return;
                dispatch({ type: "start_setup", intent: null });
                dispatch({ type: "pick", step: "grade", value: e.target.value });
              }}
              data-testid="class-select"
              className="min-h-11 w-auto cursor-pointer rounded-full border border-input-line bg-transparent px-4 text-sm font-normal text-ink"
            >
              <option value="">{copy.chatClassPick}</option>
              {stepOptions(ctx, {}, "grade")
                .filter((o) => Number(o.value) >= FIRST_CLASS_SHOWN)
                .map((o) => (
                  <option key={o.value} value={o.value} disabled={!o.available}>
                    {copy.chatClassN.replace("{n}", o.value)}
                    {o.available ? "" : ` (${copy.chatSoon})`}
                  </option>
                ))}
            </select>
          </div>
        ) : null}
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
          className="min-h-[4.25rem] w-full flex-1 resize-none @xl:min-h-12 border-0 bg-transparent py-2.5 font-[inherit] text-base text-ink outline-none placeholder:text-muted"
        />
        <div className="flex items-center justify-between gap-3">
          {/* The mode control: a segmented pill. The chosen mode is filled and carries aria-pressed; a mode
              that is not built yet is dimmed and tagged in words. */}
          <div
            className={docked && role === "visitor" ? "hidden" : "flex min-w-0 flex-wrap gap-1 rounded-full bg-surface-2 p-1"}
            role="group"
            aria-label={copy.chatModes}
          >
            {modes.map((m) => (
              <button
                key={m}
                type="button"
                aria-pressed={mode === m}
                disabled={SOON.includes(m)}
                onClick={() => setMode(m)}
                data-testid={`mode-${m}`}
                className={`inline-flex min-h-10 w-auto cursor-pointer items-center gap-1.5 rounded-full border-0 px-3.5 text-sm font-normal disabled:cursor-not-allowed disabled:opacity-60 ${mode === m ? "bg-card-solid text-ink shadow-[var(--shadow-card)] ring-1 ring-line" : "bg-transparent text-muted hover:text-ink"}`}
              >
                {copy[MODE_LABEL[m]]}
                {SOON.includes(m) ? <span className="rounded-full bg-neutral-soft px-1.5 py-0.5 text-[0.625rem] text-muted">{copy.chatSoon}</span> : null}
              </button>
            ))}
          </div>
          {/* Send always looks ready. It is disabled only when sending is impossible (a mode that is not built
              yet), and then the reason is shown in words below. An empty box gets a gentle hint instead. */}
          <button
            type="button"
            aria-disabled="true"
            aria-label={copy.chatMicLabel}
            onClick={() => setMicHint(true)}
            className="ml-auto grid size-12 shrink-0 cursor-pointer place-items-center rounded-full border border-input-line bg-transparent text-muted"
            data-testid="composer-mic"
          >
            <Icon name="mic" size={20} />
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
            className="grid size-12 shrink-0 cursor-pointer place-items-center rounded-full border-0 bg-accent text-accent-fg transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:bg-neutral-soft disabled:text-muted"
            data-testid="composer-send"
          >
            <Icon name="arrowUp" size={22} />
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
