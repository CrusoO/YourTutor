"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { ApiError, inviteReviewer, setReviewerSuspended, staffToken, whoAmI, type DeskReviewer } from "@/lib/api";
import { reviewerDeskEnabled } from "@/lib/flags";
import { desk } from "@/lib/reviewDeskCopy";

const t = desk.admin;

/** Admin only, behind NEXT_PUBLIC_REVIEWER_DESK: invite a reviewer by email, suspend or reinstate them. */
export default function ReviewersAdminPage() {
  const router = useRouter();
  const [state, setState] = useState<"loading" | "admin" | "denied">("loading");
  const [email, setEmail] = useState("");
  const [rows, setRows] = useState<DeskReviewer[]>([]);
  const [message, setMessage] = useState("");
  const [problem, setProblem] = useState("");

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
      .then((me: { role?: string }) => setState(me.role === "admin" ? "admin" : "denied"))
      .catch(() => setState("denied"));
  }, [router]);

  const keep = (row: DeskReviewer) => setRows((all) => [row, ...all.filter((r) => r.id !== row.id)]);

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
      <h2>{t.listTitle}</h2>
      <p className="muted">{t.listNote}</p>
      {rows.length === 0 ? <p>{t.none}</p> : null}
      <ul className="m-0 list-none space-y-2 p-0" data-testid="reviewer-list">
        {rows.map((row) => (
          <li key={row.id} className="flex flex-wrap items-center gap-3 rounded-xl border border-line bg-surface p-3">
            <span className="min-w-0 flex-1 break-all">{row.email}</span>
            <span className="text-sm text-muted">{row.suspended ? t.suspended : t.active}</span>
            <Button variant="outline" size="sm" onClick={() => void toggle(row)}>
              {row.suspended ? t.reinstate : t.suspend}
            </Button>
          </li>
        ))}
      </ul>
      <Link href="/staff/review">{t.back}</Link>
    </main>
  );
}
