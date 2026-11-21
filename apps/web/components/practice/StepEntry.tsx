"use client";

import { useRef, useState } from "react";
import { practiceCheckSteps } from "@/lib/api";
import type { SessionCopy } from "@/lib/session/copy";
import {
  KEYS,
  MAX_LINES,
  backspaceAt,
  insertAt,
  lineView,
  readReport,
  refusalOf,
  stepRequest,
  type LineView,
  type StepReport,
} from "@/lib/practice/steps";

type Props = {
  copy: SessionCopy;
  /** The equation read from the question, for example "x² - 7x + 10 = 0". */
  equation: string;
  /** Test seam: replaces the network call. */
  send?: (body: string) => Promise<{ status: number; json: unknown }>;
};

const ICONS: Record<LineView["icon"], React.ReactNode> = {
  check: <path d="M3 8.5l3.2 3L13 4.5" strokeLinecap="round" strokeLinejoin="round" />,
  return: <path d="M13 3v5H4m0 0l3-3m-3 3l3 3" strokeLinecap="round" strokeLinejoin="round" />,
  question: (
    <>
      <circle cx="8" cy="8" r="6" />
      <path d="M6.3 6.4a1.8 1.8 0 113 1.2c-.6.5-1.3.8-1.3 1.6M8 11.4v.1" strokeLinecap="round" />
    </>
  ),
  dots: <path d="M4 8h.01M8 8h.01M12 8h.01" strokeLinecap="round" strokeWidth="2.4" />,
};

function Icon({ name }: { name: LineView["icon"] }) {
  return (
    <svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      {ICONS[name]}
    </svg>
  );
}

const fill = (template: string, n: number) => template.replace("{n}", String(n));

/** Numbered working lines, a small maths keypad and a Check step button. Marks and hints are not part of this slice. */
export default function StepEntry({ copy, equation, send = practiceCheckSteps }: Props) {
  const [lines, setLines] = useState<string[]>([""]);
  const [active, setActive] = useState(0);
  const [checked, setChecked] = useState<{ lines: string[]; report: StepReport } | null>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const inputs = useRef<(HTMLInputElement | null)[]>([]);

  const edit = (apply: (value: string, start: number, end: number) => { value: string; caret: number }) => {
    const el = inputs.current[active];
    const value = lines[active] ?? "";
    const start = el?.selectionStart ?? value.length;
    const end = el?.selectionEnd ?? value.length;
    const next = apply(value, start, end);
    setLines((all) => all.map((l, i) => (i === active ? next.value : l)));
    window.requestAnimationFrame(() => {
      el?.focus();
      el?.setSelectionRange(next.caret, next.caret);
    });
  };

  const refusalText = (kind: ReturnType<typeof refusalOf>) =>
    ({
      disabled: copy.stepRefusalDisabled,
      consent: copy.stepRefusalConsent,
      rate: copy.stepRefusalRate,
      invalid: copy.stepRefusalInvalid,
      failed: copy.stepRefusalFailed,
    })[kind];

  const check = async () => {
    const sent = lines.map((l) => l.trim());
    if (busy || sent.every((l) => !l)) return;
    setBusy(true);
    setNote(null);
    try {
      const res = await send(stepRequest(equation, sent));
      const report = res.status === 200 ? readReport(res.json) : null;
      if (report) {
        setChecked({ lines: sent, report });
        if (sent[sent.length - 1] && sent.length < MAX_LINES) {
          setLines([...sent, ""]);
          setActive(sent.length);
        }
      } else {
        setNote(refusalText(res.status === 200 ? "failed" : refusalOf(res.status, res.json)));
      }
    } catch {
      setNote(copy.stepRefusalFailed);
    } finally {
      setBusy(false);
    }
  };

  // A line shows its state only while it, and every line before it, is still what was checked.
  const stateFor = (i: number) => {
    if (!checked) return null;
    for (let j = 0; j <= i; j++) if ((lines[j] ?? "").trim() !== (checked.lines[j] ?? "")) return null;
    const row = checked.report.lines[i];
    return row ? lineView(row.state) : null;
  };
  const verdictText = (() => {
    if (!checked) return null;
    const unchanged = checked.lines.every((l, i) => l === (lines[i] ?? "").trim());
    if (!unchanged) return null;
    const v = checked.report.verdict;
    if (v === "correct") return { text: copy.verdictCorrect, tone: "good" as const };
    if (v === "wrong") return { text: copy.verdictWrong, tone: "try" as const };
    if (v === "not_final") return { text: copy.verdictNotFinal, tone: "muted" as const };
    if (v === "unchecked") return { text: copy.verdictUnchecked, tone: "muted" as const };
    return null;
  })();

  return (
    <section className="stepentry" data-testid="step-entry" aria-label={copy.stepsTitle}>
      <style>{CSS}</style>
      <h2 className="se-title">{copy.stepsTitle}</h2>
      <p className="se-eq math" data-testid="step-equation">
        <span className="muted">{copy.stepsEquation}: </span>
        {equation}
      </p>
      <p className="muted se-privacy">{copy.stepsPrivacy}</p>
      <ol className="se-lines">
        {lines.map((line, i) => {
          const view = stateFor(i);
          const id = `se-line-${i}`;
          return (
            <li key={i} className="se-row">
              <label htmlFor={id} className="se-num">
                {fill(copy.stepLineLabel, i + 1)}
              </label>
              <input
                id={id}
                ref={(el) => {
                  inputs.current[i] = el;
                }}
                className={`math se-input${view ? ` ${view.tone}` : ""}`}
                data-testid={`step-line-${i}`}
                value={line}
                inputMode="none"
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
                autoComplete="off"
                maxLength={160}
                aria-describedby={view ? `${id}-state` : undefined}
                onFocus={() => setActive(i)}
                onChange={(e) => setLines((all) => all.map((l, k) => (k === i ? e.target.value : l)))}
              />
              {view ? (
                <p id={`${id}-state`} className={`se-state ${view.tone}`} data-testid={`step-state-${i}`} data-state={view.copyKey}>
                  <Icon name={view.icon} />
                  <span>{copy[view.copyKey]}</span>
                </p>
              ) : null}
            </li>
          );
        })}
      </ol>
      <div className="se-keys" role="group" aria-label={copy.stepKeypad} data-testid="step-keypad">
        {KEYS.map((key) => (
          <button
            key={key.id}
            type="button"
            className="secondary se-key"
            data-testid={`key-${key.id}`}
            onClick={() => edit((v, s, e) => insertAt(v, s, e, key.insert))}
          >
            {key.label}
          </button>
        ))}
        <button type="button" className="secondary se-key se-wide" data-testid="key-back" onClick={() => edit(backspaceAt)}>
          {copy.stepBackspace}
        </button>
        <button
          type="button"
          className="secondary se-key se-wide"
          data-testid="key-noroots"
          onClick={() => edit((v, s, e) => insertAt(v, s, e, copy.stepNoRoots))}
        >
          {copy.stepNoRoots}
        </button>
      </div>
      <button type="button" className="se-check" data-testid="step-check" disabled={busy} onClick={check}>
        {busy ? copy.stepChecking : copy.stepCheck}
      </button>
      <div role="status" aria-live="polite">
        {note ? (
          <p className="se-verdict try" data-testid="step-note">
            {note}
          </p>
        ) : null}
        {verdictText ? (
          <p className={`se-verdict ${verdictText.tone}`} data-testid="step-verdict">
            <Icon name={verdictText.tone === "good" ? "check" : verdictText.tone === "try" ? "return" : "question"} />
            {verdictText.text}
          </p>
        ) : null}
      </div>
    </section>
  );
}

const CSS = `
.stepentry { display: grid; gap: 10px; padding: 16px; border: 1px solid var(--s-border-subtle); border-radius: 16px; background: var(--s-surface-card); }
.se-title { margin: 0; font-size: 1.125rem; }
.se-eq { margin: 0; font-size: 1.125rem; font-weight: 600; }
.se-privacy { margin: 0; font-size: 0.8125rem; }
.se-lines { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.se-row { display: grid; gap: 4px; }
.se-num { font-size: 0.8125rem; font-weight: 700; color: var(--s-text-subtle); }
.se-input { min-height: 48px; width: 100%; box-sizing: border-box; font-size: 1.125rem; padding: 8px 12px; border-width: 2px; }
.se-input.good { border-color: var(--c-success); }
.se-input.try { border-color: var(--c-warning); }
.se-input.muted { border-color: var(--s-text-subtle); border-style: dashed; }
.se-state, .se-verdict { display: flex; gap: 8px; align-items: flex-start; margin: 0; padding: 8px 12px; border-radius: 10px; font-weight: 600; }
.se-state.good, .se-verdict.good { background: var(--c-success-soft); color: var(--c-success); }
.se-state.try, .se-verdict.try { background: var(--c-warning-soft); color: var(--c-warning); }
.se-state.muted, .se-verdict.muted { background: transparent; color: var(--s-text-subtle); border: 1px dashed var(--s-text-subtle); }
.se-state svg { flex: none; margin-top: 2px; }
.se-keys { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.se-key { min-height: 48px; min-width: 48px; font-size: 1.125rem; padding: 4px; }
.se-wide { grid-column: span 2; font-size: 1rem; }
.se-check { min-height: 48px; }
`;
