"use client";

import { useEffect, useRef } from "react";

export type LessonMode = "read" | "listen" | "watch";

const MODES: { id: LessonMode; label: string }[] = [
  { id: "read", label: "Read" },
  { id: "listen", label: "Listen" },
  { id: "watch", label: "Watch video" },
];

/** Read, Listen or Watch: three ways into the same lesson. Listen plays Brownie's voice for each step; Watch opens the video. */
export function ModeBar({ mode, onChange }: { mode: LessonMode; onChange: (m: LessonMode) => void }) {
  return (
    <div role="group" aria-label="How do you want to learn this?" className="grid grid-cols-3 gap-2" data-testid="mode-bar">
      {MODES.map((m) => (
        <button
          key={m.id}
          type="button"
          aria-pressed={mode === m.id}
          onClick={() => onChange(m.id)}
          data-testid={`mode-${m.id}`}
          className={`min-h-10 cursor-pointer rounded-full border px-2 text-[0.8125rem] transition-colors ${mode === m.id ? "border-accent bg-accent-soft text-ink" : "border-line bg-surface text-muted hover:bg-surface-2"}`}
        >
          {m.label}
        </button>
      ))}
    </div>
  );
}

/**
 * Brownie's voice for one step: a recording made beforehand with the same voice as the lesson video. In Listen mode it starts by itself
 * when the step appears (the student's tap on Continue allows that); in Read mode it waits for a tap.
 */
export function StepVoice({ src, autoPlay }: { src: string; autoPlay: boolean }) {
  const ref = useRef<HTMLAudioElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (autoPlay) el.play().catch(() => undefined); // a browser may refuse until the student taps: the controls are right there
    return () => el.pause();
  }, [src, autoPlay]);
  return (
    <div className="flex flex-col gap-1" data-testid="step-voice">
      <p className="m-0 text-[0.75rem] text-muted">{autoPlay ? "Brownie is reading this step to you." : "Listen to Brownie read this step."}</p>
      {/* eslint-disable-next-line jsx-a11y/media-has-caption -- the same words are on the screen */}
      <audio ref={ref} src={src} controls preload="auto" className="h-10 w-full" aria-label="Brownie reading this step" />
    </div>
  );
}
