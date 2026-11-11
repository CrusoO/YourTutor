"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AgreementForm from "@/components/agreement/AgreementForm";
import AgreementShell from "@/components/agreement/AgreementShell";
import { child, ui } from "@/lib/agreement-copy";
import {
  ApiError,
  childStatus,
  getAuthOptions,
  resendChildLink,
  startChild,
  type ChildStatus,
} from "@/lib/agreements-api";
import { getContextOptions, hasStudentToken, keepTabSession, setStudentId, type ContextOptions } from "@/lib/api";

type Phase = "loading" | "off" | "fields" | "notice" | "pending";

/**
 * A child starts a limited-mode profile: a nickname (not a real name), the board and class, and their
 * guardian's phone number or email. Nothing else is asked. It behaves like a guest until the guardian says yes.
 */
export default function ChildStartPage() {
  const router = useRouter();
  const [phase, setPhase] = useState<Phase>("loading");
  const [options, setOptions] = useState<ContextOptions | null>(null);
  const [nickname, setNickname] = useState("");
  const [board, setBoard] = useState("");
  const [grade, setGrade] = useState("");
  const [contact, setContact] = useState("");
  const [status, setStatus] = useState<ChildStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");

  useEffect(() => {
    getAuthOptions()
      .then(async (o) => {
        if (!o.child_profiles) return setPhase("off");
        setOptions(await getContextOptions());
        if (hasStudentToken()) {
          const s = await childStatus().catch(() => null);
          if (s && s.state !== "none") {
            setStatus(s);
            return setPhase("pending");
          }
        }
        setPhase("fields");
      })
      .catch(() => setPhase("off"));
  }, []);

  const grades = options?.curricula.find((c) => c.id === board)?.grades ?? [];
  const ready = Boolean(nickname.trim() && board && grade && contact.trim());

  async function send(acknowledged: string[]) {
    setBusy(true);
    setError("");
    try {
      const out = await startChild({
        nickname: nickname.trim(),
        curriculum_id: board,
        grade: Number(grade),
        home_language: "en",
        guardian_contact: contact.trim(),
        acknowledged,
        device_timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      });
      keepTabSession(out.token, out.student_id);
      setStudentId(out.student_id);
      setStatus({ state: "pending" });
      setNote(child.sent);
      setPhase("pending");
    } catch (caught) {
      const code = caught instanceof ApiError ? caught.code : "";
      setError(
        caught instanceof ApiError && caught.status === 429
          ? child.tooMany
          : code === "notice_unavailable"
            ? child.noticeDown
            : child.failed,
      );
      setPhase("fields");
    }
    setBusy(false);
  }

  async function refresh() {
    setStatus(await childStatus());
  }

  async function again() {
    try {
      await resendChildLink();
      setNote(child.resent);
    } catch {
      setError(child.failed);
    }
  }

  const approved = phase === "pending" && status?.state === "approved";
  return (
    <AgreementShell title={approved ? child.approvedTitle : child.title}>
      {phase === "loading" ? <p>…</p> : null}
      {phase === "off" ? <p data-testid="child-off">{child.off}</p> : null}
      {phase === "fields" ? (
        <section className="stack" data-testid="child-fields">
          <p>{child.intro}</p>
          <label>
            {child.nickname}
            <input value={nickname} maxLength={30} onChange={(e) => setNickname(e.target.value)} autoComplete="off" />
            <span className="muted">{child.nicknameHint}</span>
          </label>
          <label>
            {child.board}
            <select
              value={board}
              onChange={(e) => {
                setBoard(e.target.value);
                setGrade("");
              }}
            >
              <option value="">{ui.chooseOne}</option>
              {(options?.curricula ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.id}
                </option>
              ))}
            </select>
          </label>
          <label>
            {child.grade}
            <select value={grade} disabled={!board} onChange={(e) => setGrade(e.target.value)}>
              <option value="">{ui.chooseOne}</option>
              {grades.map((g) => (
                <option key={g.grade} value={g.grade}>
                  {g.grade}
                </option>
              ))}
            </select>
          </label>
          <label>
            {child.contact}
            <input value={contact} onChange={(e) => setContact(e.target.value)} autoComplete="off" />
            <span className="muted">{child.contactHint}</span>
          </label>
          <button type="button" disabled={!ready} onClick={() => setPhase("notice")}>
            {ui.agree}
          </button>
          {error ? <p className="banner">{error}</p> : null}
        </section>
      ) : null}
      {phase === "notice" ? (
        <AgreementForm role="child" busy={busy} submitLabel={child.start} onSubmit={(items) => void send(items)} />
      ) : null}
      {phase === "pending" && status ? (
        <section className="stack" data-testid="child-status">
          {approved ? (
            <>
              <p>{child.approvedBody}</p>
              <button type="button" onClick={() => router.push("/subjects")}>
                {child.ok}
              </button>
            </>
          ) : (
            <>
              <h2>{status.state === "expired" ? child.expired : child.pendingTitle}</h2>
              <p>{child.pendingBody}</p>
              {note ? <p role="status">{note}</p> : null}
              <button type="button" onClick={() => router.push("/subjects")}>
                {child.whileWaiting}
              </button>
              <button type="button" className="secondary" onClick={() => void refresh()}>
                {child.checkAgain}
              </button>
              <button type="button" className="secondary" onClick={() => void again()}>
                {child.resend}
              </button>
              <p className="muted">{child.schoolBody}</p>
              {error ? <p className="banner">{error}</p> : null}
            </>
          )}
        </section>
      ) : null}
    </AgreementShell>
  );
}
