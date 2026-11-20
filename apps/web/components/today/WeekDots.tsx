"use client";

import { useEffect, useId, useState } from "react";
import { weekEn } from "@/lib/today/copy";
import { clearWeek, dateKey, loadWeek, practisedCount, saveWeek, weekCells, type DayStatus, type WeekState } from "@/lib/today/week";

const STYLES = `
.wd{border:1px solid var(--s-border-subtle);background:var(--s-surface-card);color:var(--s-text-default);border-radius:12px;padding:var(--s-pad-card);display:flex;flex-direction:column;gap:var(--s-gap-stack)}
.wd-switch{display:flex;align-items:center;gap:.75rem;min-height:var(--s-control-min);background:none;border:0;padding:0;color:inherit;font:inherit;text-align:left;cursor:pointer;width:100%}
.wd-track{flex:none;width:44px;height:28px;border-radius:14px;border:2px solid var(--s-border-control);background:var(--s-surface-raised);position:relative;box-sizing:border-box}
.wd-track::after{content:"";position:absolute;top:2px;left:2px;width:20px;height:20px;border-radius:50%;background:var(--s-text-subtle);transition:transform var(--s-dur) ease}
.wd-switch[aria-checked="true"] .wd-track{background:var(--s-action-primary);border-color:var(--s-action-primary)}
.wd-switch[aria-checked="true"] .wd-track::after{transform:translateX(16px);background:var(--s-action-primary-fg)}
.wd-switch:focus-visible{outline:3px solid var(--s-focus-ring);outline-offset:2px;border-radius:8px}
.wd-hint{margin:0;color:var(--s-text-subtle);font-size:.875rem}
.wd-list{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(7,1fr);gap:.25rem}
.wd-day{display:flex;flex-direction:column;align-items:center;gap:.25rem;font-size:.75rem;color:var(--s-text-subtle)}
.wd-dot{width:32px;height:32px;border-radius:50%;border:2px solid var(--s-border-control);display:flex;align-items:center;justify-content:center;font-size:1rem;line-height:1;box-sizing:border-box}
.wd-dot[data-s="practised"]{background:var(--s-action-primary);border-color:var(--s-action-primary);color:var(--s-action-primary-fg)}
.wd-dot[data-s="rest"]{border-style:dashed;color:var(--s-text-subtle)}
.wd-dot[data-s="today"]{border-color:var(--s-action-primary)}
.wd-dot[data-s="later"]{border-color:var(--s-border-subtle)}
.wd-line{margin:0;font-size:.9375rem}
@media (prefers-reduced-motion:reduce){.wd-track::after{transition:none}}
:root[data-motion="reduce"] .wd-track::after{transition:none}
`;

const GLYPH: Record<DayStatus, string> = { practised: "✓", rest: "–", none: "", today: "", later: "" };

/** Seven dots for the current week, shown only after the student switches it on. Device only; nothing is sent. */
export default function WeekDots({ learnerId, practisedToday, now }: { learnerId: string; practisedToday: boolean; now?: Date }) {
  const copy = weekEn;
  const [state, setState] = useState<WeekState | null>(null);
  const hintId = useId();

  useEffect(() => {
    setState(loadWeek(learnerId));
  }, [learnerId]);

  const todayKey = dateKey(now ?? new Date());
  // A day is recorded only while the view is on. The signal is the Today answer: active time used today is above zero.
  useEffect(() => {
    if (!state?.on || !practisedToday || state.days.includes(todayKey)) return;
    const next = { on: true, days: [...state.days, todayKey] };
    saveWeek(learnerId, next);
    setState(next);
  }, [state, practisedToday, todayKey, learnerId]);

  if (!state) return null;

  function toggle() {
    if (!state) return;
    if (state.on) {
      clearWeek(learnerId);
      setState({ on: false, days: [] });
    } else {
      const next = { on: true, days: practisedToday ? [todayKey] : [] };
      saveWeek(learnerId, next);
      setState(next);
    }
  }

  const cells = state.on ? weekCells(state.days, now ?? new Date()) : [];
  const count = practisedCount(cells);
  const rest = cells.find((c) => c.status === "rest");

  return (
    <section className="wd" aria-label={copy.title}>
      <style>{STYLES}</style>
      <button type="button" role="switch" aria-checked={state.on} aria-describedby={hintId} className="wd-switch" onClick={toggle}>
        <span className="wd-track" aria-hidden="true" />
        <span>{copy.switchLabel}</span>
      </button>
      {!state.on ? (
        <p className="wd-hint" id={hintId}>
          {copy.switchHint}
        </p>
      ) : (
        <>
          <span id={hintId} hidden>
            {copy.switchHint}
          </span>
          <ul className="wd-list" aria-label={copy.listLabel}>
            {cells.map((c) => {
              const word =
                c.status === "practised" ? copy.practised : c.status === "rest" ? copy.rest : c.status === "none" ? copy.noPractice : copy.notYet;
              return (
                <li key={c.key} className="wd-day">
                  <span className="wd-dot" data-s={c.status} role="img" aria-label={`${copy.dayNames[c.index]}, ${word}`}>
                    {GLYPH[c.status]}
                  </span>
                  <span aria-hidden="true">{copy.dayShort[c.index]}</span>
                </li>
              );
            })}
          </ul>
          {count >= 3 ? <p className="wd-line">{copy.rhythm.replace("{n}", String(count))}</p> : null}
          {rest ? <p className="wd-line">{copy.restLine.replace("{day}", copy.dayNames[rest.index])}</p> : null}
        </>
      )}
    </section>
  );
}
