"use client";

import { useEffect, useState } from "react";
import { readAloudOn, speak, storeReadAloud, storedReadAloud, type BandUi } from "@/lib/ui";

// S1b-style English strings until the locale registry carries the player copy for this widget.
const COPY = { toggle: "Read aloud", listen: "Listen" } as const;

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
      <button
        type="button"
        className="secondary"
        aria-pressed={on}
        aria-label={COPY.toggle}
        onClick={() => {
          storeReadAloud(!on);
          setOn(!on);
        }}
      >
        {COPY.toggle}
      </button>
      {!on ? (
        <button type="button" className="secondary" onClick={() => speak(text, lang, synth)}>
          {COPY.listen}
        </button>
      ) : null}
    </div>
  );
}
