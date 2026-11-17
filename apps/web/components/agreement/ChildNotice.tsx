"use client";

import { useEffect, useId, useState } from "react";
import { getConsentText } from "@/lib/agreements-api";
import { scopeUi, type ConsentTextScope } from "@/lib/agreement-copy";
import styles from "./Agreement.module.css";

/**
 * The child-friendly notice for a scope, shown to the child at the moment the feature is used. It
 * shows the approved child wording from the server and is never stored; the child can accept or
 * cancel. Not used by any screen yet: later steps place it before each feature runs.
 */
export default function ChildNotice({
  scope,
  onAccept,
  onCancel,
}: {
  scope: ConsentTextScope;
  onAccept: () => void;
  onCancel?: () => void;
}) {
  const id = useId();
  const [text, setText] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let live = true;
    getConsentText(scope)
      .then((t) => live && setText(t.child.text))
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
    };
  }, [scope]);

  // No verified wording, no notice and no way to continue: the feature must not run unannounced.
  if (failed) return null;
  if (text === null) return <p>…</p>;
  return (
    <section
      role="alertdialog"
      aria-labelledby={`${id}-t`}
      aria-describedby={`${id}-b`}
      className={styles.confirm}
      data-testid={`child-notice-${scope}`}
    >
      <strong id={`${id}-t`}>{scopeUi.childNoticeTitle}</strong>
      <p id={`${id}-b`} className={styles.words}>
        {text}
      </p>
      <div className={styles.row}>
        <button type="button" autoFocus onClick={onAccept}>
          {scopeUi.childNoticeOk}
        </button>
        {onCancel ? (
          <button type="button" className="secondary" onClick={onCancel}>
            {scopeUi.childNoticeCancel}
          </button>
        ) : null}
      </div>
    </section>
  );
}
