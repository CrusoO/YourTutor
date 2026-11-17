"use client";

import { useEffect, useId, useState } from "react";
import { getConsentText, type ConsentText } from "@/lib/agreements-api";
import { items as copyItems, scopeUi, ui, withdrawal, type ConsentTextScope, type Role } from "@/lib/agreement-copy";
import styles from "./Agreement.module.css";

/**
 * One optional consent scope as a switch: its plain label, the exact approved guardian wording
 * (loaded from the server, with the wording version), the child's version on request, and a
 * withdrawal that says what gets deleted before it does anything. Loaded lazily by the settings
 * screen, so no other screen carries it.
 */
export default function ScopeToggle({
  role,
  scope,
  on,
  disabled,
  onChange,
}: {
  role: Role;
  scope: ConsentTextScope;
  on: boolean;
  disabled?: boolean;
  onChange: (on: boolean) => void;
}) {
  const id = useId();
  const [text, setText] = useState<ConsentText | null>(null);
  const [missing, setMissing] = useState(false);
  const [showChild, setShowChild] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const words = copyItems[role][scope];

  useEffect(() => {
    let live = true;
    getConsentText(scope)
      .then((t) => live && setText(t))
      .catch(() => live && setMissing(true));
    return () => {
      live = false;
    };
  }, [scope]);

  // Without verified wording nobody can switch it on; a scope already on can still be switched off.
  const canSwitchOn = text !== null;
  return (
    <section className={styles.scope} data-testid={`scope-${scope}`} aria-labelledby={`${id}-label`}>
      <label className={styles.tick}>
        <input
          type="checkbox"
          role="switch"
          checked={on}
          disabled={disabled || (!on && !canSwitchOn)}
          aria-describedby={`${id}-words`}
          onChange={(e) => {
            if (e.target.checked) onChange(true);
            else setConfirming(true);
          }}
        />
        <span className={styles.text}>
          <span id={`${id}-label`} className={styles.label}>
            {words.label}
            <span className={styles.tag}>({on ? scopeUi.status.on : scopeUi.status.off})</span>
          </span>
        </span>
      </label>
      <div id={`${id}-words`}>
        {text ? (
          <>
            <h3>{scopeUi.guardianHeading}</h3>
            <blockquote className={styles.words} data-testid={`guardian-text-${scope}`}>
              {text.guardian.text}
            </blockquote>
            <p className="muted">
              {scopeUi.textVersion}: {text.version}
            </p>
            <button
              type="button"
              className="secondary"
              aria-expanded={showChild}
              aria-controls={`${id}-child`}
              onClick={() => setShowChild((v) => !v)}
            >
              {showChild ? scopeUi.hideChild : scopeUi.showChild}
            </button>
            {showChild ? (
              <div id={`${id}-child`}>
                <h3>{scopeUi.childHeading}</h3>
                <blockquote className={styles.words} data-testid={`child-text-${scope}`}>
                  {text.child.text}
                </blockquote>
              </div>
            ) : null}
          </>
        ) : null}
        {missing ? <p className="muted">{scopeUi.textMissing}</p> : null}
      </div>
      {confirming ? (
        <div
          role="alertdialog"
          aria-labelledby={`${id}-ct`}
          aria-describedby={`${id}-cd`}
          className={styles.confirm}
          data-testid={`confirm-${scope}`}
        >
          <strong id={`${id}-ct`}>{scopeUi.confirmTitle}</strong>
          <p id={`${id}-cd`}>
            {scopeUi.confirmDelete} {withdrawal[scope]}
          </p>
          <div className={styles.row}>
            <button
              type="button"
              disabled={disabled}
              onClick={() => {
                setConfirming(false);
                onChange(false);
              }}
            >
              {scopeUi.confirmGo}
            </button>
            <button type="button" className="secondary" autoFocus onClick={() => setConfirming(false)}>
              {scopeUi.confirmKeep}
            </button>
          </div>
        </div>
      ) : null}
      {disabled ? <span className="muted">{ui.saving}</span> : null}
    </section>
  );
}
