"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { ApiError, deskTemplateSummary, inviteReviewer, issueReviewerSignInCode, listReviewers, setReviewerSuspended, staffToken, whoAmI, type DeskReviewer, type DeskReviewerRow, type DeskTemplateSummary } from "@/lib/api";
import { reviewerDeskEnabled } from "@/lib/flags";
import { desk } from "@/lib/reviewDeskCopy";

const t = desk.admin;

/** Admin only, behind NEXT_PUBLIC_REVIEWER_DESK: invite a reviewer by email, suspend or reinstate them. */
export default function ReviewersAdminPage() {
  const router = useRouter();
  const [state, setState] = useState<"loading" | "admin" | "denied">("loading");
  const [email, setEmail] = useState("");
  const [rows, setRows] = useState<DeskReviewerRow[]>([]);
  const [message, setMessage] = useState("");
  const [problem, setProblem] = useState("");
  const [issued, setIssued] = useState<{ id: string; email: string; code: string } | null>(null);
  const [copied, setCopied] = useState(false);
  const [types, setTypes] = useState<DeskTemplateSummary | null>(null);

  useEffect(() => {
    if (!reviewerDeskEnabled()) {
      setState("denied");
      return;
    }
    if (!staffToken()) {
      router.push("/staff/login");
      return;
    }
    whoAmI()
      .then((me: { role?: string }) => {
        setState(me.role === "admin" ? "admin" : "denied");
        if (me.role !== "admin") return;
        listReviewers()
          .then((out) =>
            // the list is the truth, but an invite answered while it loaded must not vanish
            setRows((now) => [...out.reviewers, ...now.filter((r) => !out.reviewers.some((o) => o.id === r.id))]),
          )
          .catch(() => setProblem(t.listFailed));
        // 404 when template approval is off: then there is simply nothing to show
        deskTemplateSummary()
          .then(setTypes)
          .catch(() => setTypes(null));
      })
      .catch(() => setState("denied"));
  }, [router]);

  // an answer from invite, suspend or reinstate has the account only: keep the activity facts we already have
  const keep = (row: DeskReviewer) =>
    setRows((all) => {
      const before = all.find((r) => r.id === row.id);
      const merged: DeskReviewerRow = {
        invited_at: new Date().toISOString(),
        last_decision_at: null,
        decision_count: 0,
        ...before,
        ...row,
      };
      return before ? all.map((r) => (r.id === row.id ? merged : r)) : [merged, ...all];
    });

  async function invite() {
    setMessage("");
    setProblem("");
    try {
      const row = await inviteReviewer(email.trim());
      keep(row);
      setMessage(t.invited(row.email));
      setEmail("");
    } catch (error) {
      setProblem(error instanceof ApiError && error.status === 409 ? t.otherAccount : t.failed);
    }
  }

  async function toggle(row: DeskReviewer) {
    setProblem("");
    try {
      keep(await setReviewerSuspended(row.id, !row.suspended));
    } catch {
      setProblem(t.failed);
    }
  }

  async function makeCode(row: DeskReviewer) {
    setProblem("");
    setCopied(false);
    setIssued(null);
    try {
      const out = await issueReviewerSignInCode(row.id);
      setIssued({ id: row.id, email: row.email, code: out.code });
    } catch (error) {
      const status = error instanceof ApiError ? error.status : 0;
      setProblem(status === 409 ? t.codeSuspended : status === 429 ? t.codeLimit : status === 404 ? t.codeMissing : t.codeFailed);
    }
  }

  async function copyCode() {
    try {
      await navigator.clipboard.writeText(issued?.code ?? "");
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  if (state === "loading") return null;
  if (state === "denied")
    return (
      <main className="stack" data-testid="reviewers-denied">
        <p role="alert">{t.notAdmin}</p>
      </main>
    );
  return (
    <main className="stack mx-auto w-full max-w-2xl" data-testid="reviewers-admin">
      <h1>{t.title}</h1>
      <p className="muted">{t.intro}</p>
      <form
        className="stack"
        onSubmit={(event) => {
          event.preventDefault();
          void invite();
        }}
      >
        <label htmlFor="reviewer-email">{t.email}</label>
        <input id="reviewer-email" type="email" autoComplete="off" value={email} onChange={(e) => setEmail(e.target.value)} />
        <Button type="submit" disabled={!email.includes("@")}>
          {t.invite}
        </Button>
      </form>
      <div role="status" aria-live="polite">
        {message ? <p>{message}</p> : null}
      </div>
      {problem ? <p role="alert">{problem}</p> : null}
      {issued ? (
        <section className="stack rounded-xl border border-line bg-surface p-3" data-testid="signin-code">
          <h2>{t.codeFor(issued.email)}</h2>
          <p className="text-2xl font-bold tracking-widest" data-testid="signin-code-value">
            {issued.code}
          </p>
          <p>{t.codeNote}</p>
          <div className="flex gap-3">
            <Button size="sm" onClick={() => void copyCode()}>
              {copied ? t.copied : t.copy}
            </Button>
            <Button variant="outline" size="sm" onClick={() => setIssued(null)}>
              {t.done}
            </Button>
          </div>
        </section>
      ) : null}
      <h2>{t.listTitle}</h2>
      {rows.length === 0 ? <p>{t.none}</p> : null}
      <ul className="m-0 list-none space-y-2 p-0" data-testid="reviewer-list">
        {rows.map((row) => (
          <li key={row.id} className="flex flex-wrap items-center gap-3 rounded-xl border border-line bg-surface p-3">
            <span className="min-w-0 flex-1 break-all">
              {row.email}
              <span className="block text-xs text-muted">
                {t.invitedOn(new Date(row.invited_at).toLocaleDateString())} · {t.decisionCount(row.decision_count)} ·{" "}
                {t.lastDecision(row.last_decision_at ? new Date(row.last_decision_at).toLocaleDateString() : null)}
              </span>
            </span>
            <span className="text-sm text-muted">{row.suspended ? t.suspended : t.active}</span>
            <Button variant="outline" size="sm" disabled={row.suspended} onClick={() => void makeCode(row)}>
              {t.makeCode}
            </Button>
            <Button variant="outline" size="sm" onClick={() => void toggle(row)}>
              {row.suspended ? t.reinstate : t.suspend}
            </Button>
          </li>
        ))}
      </ul>
      {types ? (
        <section className="stack" data-testid="types-summary">
          <h2>{t.typesTitle}</h2>
          <p className="muted">{t.typesNote}</p>
          <p data-testid="types-totals">{t.typesTotals(types.totals)}</p>
          {types.blocked.length ? <h3>{t.typesFlagged}</h3> : null}
          <ul className="m-0 list-none space-y-2 p-0" data-testid="types-flagged">
            {types.blocked.map((b) => (
              <li key={`${b.template_id}-${b.template_hash}-${b.generator_version}`} className="rounded-xl border border-line bg-surface p-3">
                {t.typesFlaggedLine(b.template_id, b.state, b.questions)}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      <Link href="/staff/review">{t.back}</Link>
    </main>
  );
}
