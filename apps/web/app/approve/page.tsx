"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import AgreementForm from "@/components/agreement/AgreementForm";
import AgreementShell from "@/components/agreement/AgreementShell";
import { approve, ui } from "@/lib/agreement-copy";
import { ApiError, approveChild, declineChild, lookupApproval, type ApprovalView } from "@/lib/agreements-api";
import { getContextOptions, setStaffToken, type ContextOptions } from "@/lib/api";

type State = "loading" | "ready" | "invalid" | "done" | "declined";

/**
 * The guardian's screen, opened from the link we sent. No account is needed first. The token is in the part
 * of the link after "#", so it is never sent to a web server's log; it is only posted to the API.
 */
export default function ApprovePage() {
  const [token, setToken] = useState("");
  const [state, setState] = useState<State>("loading");
  const [view, setView] = useState<ApprovalView | null>(null);
  const [options, setOptions] = useState<ContextOptions | null>(null);
  const [grade, setGrade] = useState("");
  const [board, setBoard] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const found = window.location.hash.replace(/^#/, "");
    if (!found) {
      setState("invalid");
      return;
    }
    setToken(found);
    lookupApproval(found)
      .then((data) => {
        setView(data);
        setGrade(String(data.grade));
        setBoard(data.curriculum_id);
        setState("ready");
      })
      .catch(() => setState("invalid"));
    getContextOptions()
      .then(setOptions)
      .catch(() => setOptions(null));
  }, []);

  async function agree(items: string[], version: string) {
    if (!view) return;
    setBusy(true);
    setError("");
    try {
      const body: Parameters<typeof approveChild>[0] = { token, version, accepted: items };
      if (Number(grade) !== view.grade) body.grade = Number(grade);
      if (board !== view.curriculum_id) body.curriculum_id = board;
      const out = await approveChild(body);
      setStaffToken(out.access_token);
      window.history.replaceState(null, "", window.location.pathname);
      setState("done");
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 409 ? ui.versionChanged : ui.failed);
      setBusy(false);
    }
  }

  async function decline() {
    setBusy(true);
    try {
      await declineChild(token);
      window.history.replaceState(null, "", window.location.pathname);
      setState("declined");
    } catch {
      setError(ui.failed);
      setBusy(false);
    }
  }

  const grades = options?.curricula.find((c) => c.id === board)?.grades ?? [];
  return (
    <AgreementShell title={approve.title}>
      {state === "loading" ? <p>…</p> : null}
      {state === "invalid" ? <p data-testid="approve-invalid">{approve.invalid}</p> : null}
      {state === "declined" ? <p data-testid="approve-declined">{approve.declined}</p> : null}
      {state === "done" ? (
        <section className="stack" data-testid="approve-done">
          <p>{approve.approved}</p>
          <p className="muted">{approve.school}</p>
          <Link href="/guardian">{approve.username}</Link>
        </section>
      ) : null}
      {state === "ready" && view ? (
        <>
          <p>{approve.intro}</p>
          <p data-testid="approve-nickname">
            <strong>{approve.nickname}:</strong> {view.nickname}
          </p>
          <p className="muted">{approve.correct}</p>
          <label>
            {approve.board}
            <select
              value={board}
              onChange={(e) => {
                setBoard(e.target.value);
                setGrade("");
              }}
            >
              {(options?.curricula ?? [{ id: view.curriculum_id }]).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.id}
                </option>
              ))}
            </select>
          </label>
          <label>
            {approve.grade}
            <select value={grade} onChange={(e) => setGrade(e.target.value)}>
              {!grades.some((g) => String(g.grade) === grade) ? <option value={grade}>{grade || ui.chooseOne}</option> : null}
              {grades.map((g) => (
                <option key={g.grade} value={g.grade}>
                  {g.grade}
                </option>
              ))}
            </select>
          </label>
          <AgreementForm
            role="guardian"
            catalog={view.agreement}
            submitLabel={approve.approve}
            busy={busy || !grade}
            onSubmit={(i, v) => void agree(i, v)}
          />
          <button type="button" className="secondary" disabled={busy} onClick={() => void decline()}>
            {approve.decline}
          </button>
          <p className="muted">{approve.contactCaveat}</p>
          {error ? <p className="banner">{error}</p> : null}
        </>
      ) : null}
    </AgreementShell>
  );
}
