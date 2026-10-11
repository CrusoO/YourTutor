"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SuggestionCard } from "@/components/ui/suggestion-card";
import { requestStaffCode, setLocale, setStudentId, studentLogin, today, verifyStaffCode, whoAmI } from "@/lib/api";
import type { IdentityView, Role } from "@/lib/chat/machine";
import { useChatApi } from "./ChatProvider";

function Back({ to }: { to?: IdentityView }) {
  const { copy, dispatch } = useChatApi();
  return (
    <Button variant="ghost" size="sm" onClick={() => dispatch({ type: "identity", view: to ?? "choices" })} data-testid="identity-back">
      ← {copy.chatBack}
    </Button>
  );
}

/** Student sign-in: the existing family code and PIN. */
function StudentSignIn({ createFlow }: { createFlow?: boolean }) {
  const { copy, signedIn } = useChatApi();
  const [family, setFamily] = useState("");
  const [pin, setPin] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await studentLogin(family.trim().toUpperCase(), pin.trim());
      const me = await today();
      setStudentId(me.student_id);
      if (me.locale) setLocale(me.locale);
      signedIn("student", me.display_name);
    } catch {
      setError(copy.loginError);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="flex max-w-md flex-col gap-3 pl-11" data-testid="student-sign-in">
      {createFlow ? <p className="m-0 text-sm text-muted">{copy.chatUnder18}</p> : null}
      <label className="flex flex-col gap-1.5 text-sm font-semibold">
        {copy.familyCode}
        <Input value={family} onChange={(e) => setFamily(e.target.value)} autoComplete="off" data-testid="family-code" />
      </label>
      <label className="flex flex-col gap-1.5 text-sm font-semibold">
        {copy.pin}
        <Input value={pin} onChange={(e) => setPin(e.target.value)} type="password" inputMode="numeric" autoComplete="off" data-testid="family-pin" />
      </label>
      {error ? (
        <p role="alert" className="m-0 text-sm text-danger">
          {error}
        </p>
      ) : null}
      <div className="flex flex-wrap items-center gap-2">
        <Button type="submit" disabled={busy || !family || !pin} data-testid="student-sign-in-go">
          {copy.signIn}
        </Button>
        <Back />
      </div>
    </form>
  );
}

/** Parent and teacher sign-in: an email code through the existing guardian and teacher auth. */
function OtpForm({ expect }: { expect: Extract<Role, "parent" | "teacher"> }) {
  const { copy, signedIn } = useChatApi();
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function send(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await requestStaffCode(email.trim());
      setSent(true);
    } catch {
      setError(copy.chatCouldNotLoad);
    } finally {
      setBusy(false);
    }
  }

  async function verify(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await verifyStaffCode(email.trim(), code.trim());
      const who = await whoAmI();
      const actual: Role = who.role === "teacher" ? "teacher" : "parent";
      signedIn(actual);
    } catch {
      setError(copy.chatWrongCode);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={sent ? verify : send} className="flex max-w-md flex-col gap-3 pl-11" data-testid={`${expect}-otp`}>
      <label className="flex flex-col gap-1.5 text-sm font-semibold">
        {copy.chatEmail}
        <Input value={email} onChange={(e) => setEmail(e.target.value)} type="email" autoComplete="email" disabled={sent} data-testid="otp-email" />
      </label>
      {sent ? (
        <label className="flex flex-col gap-1.5 text-sm font-semibold">
          {copy.chatEnterCode}
          <Input value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" autoComplete="one-time-code" data-testid="otp-code" />
        </label>
      ) : null}
      {expect === "teacher" ? <p className="m-0 text-sm text-muted">{copy.chatCreateTeacherHint}</p> : null}
      {error ? (
        <p role="alert" className="m-0 text-sm text-danger">
          {error}
        </p>
      ) : null}
      <div className="flex flex-wrap items-center gap-2">
        <Button type="submit" disabled={busy || !email || (sent && !code)} data-testid="otp-go">
          {sent ? copy.chatVerify : copy.chatSendCode}
        </Button>
        <Back />
      </div>
    </form>
  );
}

/** Where the visitor decides how to continue. Sign-in and account creation happen here, in the chat. */
export function IdentityBlock() {
  const { chat, copy, dispatch, justTry, busy, error } = useChatApi();
  const view = chat.identity;

  if (chat.phase !== "identity" && !(chat.phase === "welcome" && view !== "choices")) return null;

  if (view === "sign_in") return <StudentSignIn />;
  if (view === "parent") return <OtpForm expect="parent" />;
  if (view === "teacher") return <OtpForm expect="teacher" />;

  if (view === "save_progress") {
    return (
      <div className="flex max-w-xl flex-col gap-3 pl-11" data-testid="grown-up">
        <h3 className="m-0 text-base font-semibold">{copy.chatGrownUpTitle}</h3>
        <p className="m-0 text-sm text-muted">{copy.chatGrownUpBody}</p>
        <div className="flex flex-wrap items-center gap-2">
          <Button onClick={() => dispatch({ type: "identity", view: "parent" })} data-testid="grown-up-go">
            {copy.chatGrownUpGo}
          </Button>
          <Back />
        </div>
      </div>
    );
  }

  if (view === "create_account") {
    return (
      <div className="flex max-w-2xl flex-col gap-3 pl-11" data-testid="create-account">
        <h3 className="m-0 text-base font-semibold">{copy.chatCreateAccountTitle}</h3>
        <div className="grid gap-3 sm:grid-cols-3">
          <SuggestionCard tone="accent" icon="user" title={copy.chatCreateStudent} description={copy.chatCreateStudentHint} onClick={() => dispatch({ type: "identity", view: "sign_in" })} data-testid="create-student" />
          <SuggestionCard tone="neutral" icon="users" title={copy.chatCreateTeacher} description={copy.chatCreateTeacherHint} onClick={() => dispatch({ type: "identity", view: "teacher" })} data-testid="create-teacher" />
          <SuggestionCard tone="success" icon="shield" title={copy.chatCreateParent} description={copy.chatCreateParentHint} onClick={() => dispatch({ type: "identity", view: "parent" })} data-testid="create-parent" />
        </div>
        <p className="m-0 text-sm text-muted">{copy.chatUnder18}</p>
        <div>
          <Back />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 pl-11" data-testid="identity-choices">
      <div className="grid max-w-3xl gap-3 sm:grid-cols-2">
        <SuggestionCard tone="accent" icon="play" title={copy.chatJustTry} description={copy.chatJustTryHint} tag={copy.chatNew} disabled={busy} onClick={() => void justTry()} data-testid="just-try" />
        <SuggestionCard tone="neutral" icon="lock" title={copy.chatHaveCode} onClick={() => dispatch({ type: "identity", view: "sign_in" })} data-testid="have-code" />
        <SuggestionCard tone="success" icon="shield" title={copy.chatSaveProgress} description={copy.chatSaveProgressHint} onClick={() => dispatch({ type: "identity", view: "save_progress" })} data-testid="save-progress" />
        <SuggestionCard tone="neutral" icon="users" title={copy.chatImParent} onClick={() => dispatch({ type: "identity", view: "parent" })} data-testid="im-parent" />
        <SuggestionCard tone="neutral" icon="book" title={copy.chatImTeacher} onClick={() => dispatch({ type: "identity", view: "teacher" })} data-testid="im-teacher" />
      </div>
      {error ? (
        <p role="alert" className="m-0 text-sm text-danger">
          {error}
        </p>
      ) : null}
    </div>
  );
}
