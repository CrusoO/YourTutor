"use client";

import { useEffect, useState } from "react";
import { readAloudOn, speak, storeReadAloud, storedReadAloud, type BandUi } from "@/lib/ui";

// S1b-style English strings until the locale registry carries the player copy for this widget.
const COPY = { toggle: "Read aloud", listen: "Listen" } as const;

// Small labelled icon buttons: quiet, always named in words as well as the picture. Kept here (not in the
// global stylesheet) so the homepage stays light.
const CSS = `.ra-btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;width:auto;min-height:44px;min-width:44px;padding:6px 12px;border:1.5px solid var(--c-line,var(--line));border-radius:999px;background:transparent;color:var(--c-muted,var(--muted));font-size:0.875rem;font-weight:600;}.ra-btn[aria-pressed="true"]{border-color:var(--c-accent-ink,var(--blue));color:var(--c-accent-ink,var(--blue));}.ra-btn svg{width:18px;height:18px;flex:none;}`;

function Speaker() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 9v6h4l5 4V5L8 9H4z" />
      <path d="M16.5 8.5a5 5 0 0 1 0 7" />
    </svg>
  );
}

function Play() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="currentColor">
      <path d="M8 5v14l11-7z" />
    </svg>
  );
}

/** A small speaker control. Reads the text on its own when the band (or the student) says so. */
export default function ReadAloud({ text, lang, ui }: { text: string; lang: string; ui?: BandUi }) {
  const [on, setOn] = useState(() => readAloudOn(ui, storedReadAloud()));
  const synth = typeof window === "undefined" ? undefined : window.speechSynthesis;

  useEffect(() => {
    if (on) speak(text, lang, synth);
    return () => synth?.cancel?.();
  }, [on, text, lang, synth]);

  if (!synth) return null;
  return (
    <div className="read-aloud">
      <style>{CSS}</style>
      <button
        type="button"
        className="secondary ra-btn"
        aria-pressed={on}
        aria-label={COPY.toggle}
        onClick={() => {
          storeReadAloud(!on);
          setOn(!on);
        }}
      >
        <Speaker />
        {COPY.toggle}
      </button>
      {!on ? (
        <button type="button" className="secondary ra-btn" onClick={() => speak(text, lang, synth)}>
          <Play />
          {COPY.listen}
        </button>
      ) : null}
    </div>
  );
}
