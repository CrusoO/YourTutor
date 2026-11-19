"use client";

import { useId, useState } from "react";
import { lessonFlowEn as flow } from "@/lib/lessons/copy";

// Kept with the lazy lesson player, never in the global stylesheet, so the homepage stays light.
// Direction is carried by an arrow and by words as well as by colour.
const CSS = `.sh{display:grid;gap:4px;justify-items:center;margin:0 0 8px;}.sh-note{margin:0;font-size:0.95rem;color:var(--c-text);text-align:center;}.sh-link{background:none;border:0;min-height:44px;min-width:44px;padding:8px 6px;color:var(--c-accent-ink);font-size:0.95rem;font-weight:600;text-decoration:underline;text-underline-offset:3px;cursor:pointer;width:auto;}.sh-link:focus-visible{outline:3px solid var(--c-focus);outline-offset:2px;}.sh-panel{width:100%;box-sizing:border-box;margin:0;padding:10px 14px;list-style:none;display:grid;gap:6px;background:var(--c-surface);border:1.5px solid var(--c-line);border-radius:14px;}.sh-panel li{display:flex;align-items:center;gap:8px;font-size:0.95rem;color:var(--c-text);}.sh-panel .a{font-weight:700;font-size:1.1rem;}.sh-panel .r .a{color:var(--c-accent-ink);}.sh-panel .l .a{color:var(--c-teal);}`;

/**
 * A short note at the moment an example first needs it, and a small link that opens the plain explanation of
 * + and −. Never a permanent pair of chips.
 */
export default function SignHelp({ note }: { note: string | null }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <div className="sh" data-testid="sign-help">
      <style>{CSS}</style>
      {note ? (
        <p className="sh-note" data-testid="sign-note">
          {note}
        </p>
      ) : null}
      <button type="button" className="sh-link" aria-expanded={open} aria-controls={id} onClick={() => setOpen((o) => !o)}>
        {open ? flow.signHide : flow.signLink}
      </button>
      {open ? (
        <ul className="sh-panel" id={id} aria-label={flow.signTitle}>
          <li className="r">
            <span className="a" aria-hidden="true">
              {"→"}
            </span>
            {flow.signPlus}
          </li>
          <li className="l">
            <span className="a" aria-hidden="true">
              {"←"}
            </span>
            {flow.signMinus}
          </li>
          <li className="l">
            <span className="a" aria-hidden="true">
              {"←"}
            </span>
            {flow.signAddNeg}
          </li>
        </ul>
      ) : null}
    </div>
  );
}
