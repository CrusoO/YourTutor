"use client";

import { useEffect, useState } from "react";
import { JoinError, joinClass, leaveClass, myClasses, type MyClass } from "@/lib/api";
import { useCopy } from "@/lib/locale";

const FAILURE: Record<string, string> = {
  bad_code: "joinBad",
  slow: "joinSlow",
  guest: "joinGuest",
  signed_out: "joinSignIn",
};

/** A student joins a class with the code their teacher gave them. Nothing is shared until a guardian agrees. */
export default function JoinPage() {
  const copy = useCopy() as unknown as Record<string, string>;
  const [code, setCode] = useState("");
  const [label, setLabel] = useState("");
  const [message, setMessage] = useState("");
  const [classes, setClasses] = useState<MyClass[]>([]);
  const [busy, setBusy] = useState(false);

  const refresh = () =>
    myClasses()
      .then((data) => setClasses(data.classes))
      .catch(() => setClasses([]));

  useEffect(() => {
    void refresh();
  }, []);

  async function join(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const out = await joinClass(code, label);
      setMessage(
        out.status === "pending" ? copy.joinPending : out.shared ? copy.joinActiveShared : copy.joinActive,
      );
      setCode("");
      await refresh();
    } catch (error) {
      const reason = error instanceof JoinError ? error.reason : "bad_code";
      setMessage(copy[FAILURE[reason]]);
    } finally {
      setBusy(false);
    }
  }

  async function leave(id: string) {
    await leaveClass(id);
    await refresh();
  }

  return (
    <main className="stack" data-testid="join-page">
      <h1>{copy.joinTitle}</h1>
      <p className="muted">{copy.joinHint}</p>
      <form className="stack" onSubmit={(e) => void join(e)}>
        <label>
          {copy.joinCodeLabel}
          <input
            value={code}
            onChange={(e) => setCode(e.target.value)}
            autoComplete="off"
            autoCapitalize="characters"
            spellCheck={false}
            maxLength={20}
            inputMode="text"
            required
          />
        </label>
        <label>
          {copy.joinNameLabel}
          <input value={label} onChange={(e) => setLabel(e.target.value)} autoComplete="off" maxLength={24} />
        </label>
        <button type="submit" disabled={busy || code.trim() === ""}>
          {copy.joinButton}
        </button>
      </form>
      <p role="status" aria-live="polite" data-testid="join-message">
        {message}
      </p>
      {classes.length ? (
        <section className="stack" aria-labelledby="join-classes-h">
          <h2 id="join-classes-h">{copy.joinYourClasses}</h2>
          {classes.map((klass) => (
            <div key={klass.class_id} className="card stack">
              <strong>{klass.name}</strong>
              <span className="muted">{klass.status === "pending" ? copy.joinWaiting : copy.joinJoined}</span>
              {klass.status === "pending" ? <span>{copy.joinPending}</span> : null}
              <button type="button" className="secondary" onClick={() => void leave(klass.class_id)}>
                {copy.joinLeave}
              </button>
            </div>
          ))}
        </section>
      ) : null}
    </main>
  );
}
