"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { setLocale, setStudentId, studentLogin, today } from "@/lib/api";
import { signin } from "./loginCopy";
import styles from "./login.module.css";

/** Turns a failed sign-in into one kind sentence. Lockouts and rate limits are said plainly, never retried or hidden. */
export function loginErrorText(caught: unknown, mismatch: string): string {
  const status = (caught as { status?: number } | null)?.status;
  if (status === 423) return signin.errors.locked;
  if (status === 429) return signin.errors.slowDown;
  if (status === 401 || status === 404) return mismatch;
  return signin.errors.other;
}

/**
 * The child sign-in: a family code or username and a PIN. The form posts (never GETs) and the button stays off
 * until the page has loaded its script, so a PIN can never end up in the address bar.
 */
export default function StudentForm({
  mismatch,
  labels,
}: {
  mismatch: string;
  labels?: { code: string; pin: string; submit: string };
}) {
  const router = useRouter();
  const [family, setFamily] = useState("");
  const [pin, setPin] = useState("");
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => setReady(true), []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!ready || busy) return;
    setError("");
    setBusy(true);
    try {
      await studentLogin(family.trim(), pin.trim());
    } catch (caught) {
      setError(loginErrorText(caught, mismatch));
      setBusy(false);
      return;
    }
    try {
      const me = await today();
      setStudentId(me.student_id);
      if (me.locale) setLocale(me.locale);
      router.push("/brownie-chat");
    } catch (caught) {
      // The code and PIN were accepted; only the step after failed. Say which, so a server problem is not a "wrong PIN".
      const status = (caught as { status?: number } | null)?.status;
      setError(status === 401 ? signin.errors.afterRejected : signin.errors.afterFailed);
      setBusy(false);
    }
  }

  const s = signin.student;
  const filled = family.trim().length > 0 && pin.trim().length > 0;
  return (
    <section className={styles.panel} aria-labelledby="student-title" data-testid="student-form">
      <h2 id="student-title">{s.title}</h2>
      <p className={styles.hint}>{s.intro}</p>
      <form method="post" onSubmit={onSubmit} className={styles.form} noValidate>
        <label className={styles.fieldLabel}>
          {labels?.code ?? s.codeLabel}
          <input
            className={styles.field}
            name="family_code"
            autoComplete="username"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            value={family}
            onChange={(e) => setFamily(e.target.value)}
            aria-describedby="code-hint"
          />
          <span id="code-hint" className={styles.hint}>{s.codeHint}</span>
        </label>
        <label className={styles.fieldLabel}>
          {labels?.pin ?? s.pinLabel}
          <input
            className={styles.field}
            name="pin"
            type="password"
            inputMode="numeric"
            autoComplete="current-password"
            value={pin}
            onChange={(e) => setPin(e.target.value)}
          />
        </label>
        <div aria-live="polite" role="status">
          {error ? <p className={styles.error} data-testid="login-error">{error}</p> : null}
        </div>
        <button type="submit" className={styles.submit} disabled={!ready || busy || !filled}>
          {!ready ? s.waiting : busy ? s.working : (labels?.submit ?? s.submit)}
        </button>
      </form>
      <div className={styles.links}>
        <Link href="/join" className={styles.link}>{s.haveCode}</Link>
        <Link href="/start/child" className={styles.link}>{s.newHere}</Link>
      </div>
    </section>
  );
}
