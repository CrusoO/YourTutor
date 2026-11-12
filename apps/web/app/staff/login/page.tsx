"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import {
  devStaffToken,
  isEmailUnavailable,
  isSmsUnavailable,
  keepTabSession,
  requestStaffCode,
  setStaffToken,
  setStudentId,
  verifyStaffCode,
  whoAmI,
  type Contact,
} from "@/lib/api";
import { adultSession, getAuthOptions } from "@/lib/agreements-api";
import { signin } from "@/app/login/loginCopy";
import { login } from "@/lib/agreement-copy";

import EmailUnavailable from "@/components/EmailUnavailable";
import StorageNotice from "@/components/StorageNotice";
import { useCopy } from "@/lib/locale";

const DEV = process.env.NEXT_PUBLIC_DEV_TOOLS === "true";

/**
 * Sign-in for guardians and teachers. When the deployment has phone sign-in on, a phone number and the code
 * sent to it come first and email stays an option; otherwise it is email only. A new account, or one that has
 * not yet agreed, goes on to the role agreement.
 */
function StaffLoginForm() {
  const router = useRouter();
  const copy = useCopy();
  const asParam = useSearchParams().get("as");
  const who: "guardian" | "teacher" | "adult" | "any" =
    asParam === "guardian" || asParam === "teacher" || asParam === "adult" ? asParam : "any";
  const [phoneOn, setPhoneOn] = useState(false);
  const [mode, setMode] = useState<"phone" | "email">("email");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [mailDown, setMailDown] = useState(false);

  useEffect(() => {
    getAuthOptions()
      .then((o) => {
        setPhoneOn(o.phone_signin);
        if (o.phone_signin) setMode("phone");
      })
      .catch(() => setPhoneOn(false));
  }, []);

  const contact: Contact = mode === "phone" ? { phone: phone.trim() } : { email: email.trim() };
  const filled = mode === "phone" ? phone.trim().length >= 6 : email.includes("@");

  async function go(askAgreement = true) {
    const me = await whoAmI();
    if (askAgreement && me.agreements && me.agreements.length > 0) router.push("/agreement");
    else if (askAgreement && who === "adult" && me.role === "parent" && (await enterAsAdult())) router.push("/brownie-chat");
    else router.push(me.role === "teacher" || me.role === "admin" ? "/teacher" : "/guardian");
  }

  /** A returning adult learner goes straight to the chat on their own profile; no profile yet means the guardian page. */
  async function enterAsAdult(): Promise<boolean> {
    try {
      const out = await adultSession();
      keepTabSession(out.token, out.student_id);
      setStudentId(out.student_id);
      return true;
    } catch {
      return false;
    }
  }

  async function send() {
    setError("");
    try {
      await requestStaffCode(contact);
      setSent(true);
    } catch (caught) {
      if (isEmailUnavailable(caught)) setMailDown(true);
      else if (isSmsUnavailable(caught)) setError(login.smsDown);
      else setError(copy.loadError);
    }
  }

  async function verify() {
    setError("");
    try {
      await verifyStaffCode(contact, code.trim());
      await go();
    } catch {
      setStaffToken("");
      setError(copy.staffWrongCode);
    }
  }

  async function dev(role: "parent" | "teacher", scenario?: string) {
    await devStaffToken(role, scenario);
    await go(false); // the preview accounts skip the agreement so the preview flows stay as they were
  }

  return (
    <main className="stack" data-testid="staff-login">
      <Link href="/login" className="muted" style={{ display: "inline-flex", alignItems: "center", minHeight: 44 }}>
        ← {signin.back}
      </Link>
      <StorageNotice />
      <h1>{who === "any" ? copy.staffLoginTitle : signin.staffTitles[who]}</h1>
      {who === "teacher" ? <p className="muted" data-testid="teacher-note">{signin.teacherNote}</p> : null}
      {who === "guardian" ? <p className="muted">{signin.guardianNote}</p> : null}
      {who === "adult" ? <p className="muted">{signin.adultNote}</p> : null}
      {mode === "phone" ? (
        <label className="stack">
          {login.phoneLabel}
          <input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            autoComplete="tel"
            inputMode="tel"
            disabled={sent}
          />
          <span className="muted">{login.phoneHint}</span>
        </label>
      ) : (
        <label className="stack">
          {copy.staffEmail}
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            disabled={sent}
          />
        </label>
      )}
      {sent ? (
        <label className="stack">
          {copy.staffCode}
          <input value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" autoComplete="one-time-code" />
        </label>
      ) : null}
      {sent ? (
        <button type="button" onClick={() => void verify()}>
          {copy.staffVerify}
        </button>
      ) : (
        <button type="button" disabled={!filled} onClick={() => void send()}>
          {copy.staffSendCode}
        </button>
      )}
      {phoneOn && !sent ? (
        <button
          type="button"
          className="secondary"
          data-testid="switch-contact"
          onClick={() => setMode(mode === "phone" ? "email" : "phone")}
        >
          {mode === "phone" ? login.useEmail : login.usePhone}
        </button>
      ) : null}
      <div aria-live="polite" role="status">
        {error ? <p className="banner">{error}</p> : null}
      </div>
      {mailDown ? <EmailUnavailable /> : null}
      {DEV ? (
        <div className="stack" data-testid="staff-dev">
          <p className="muted">Preview only</p>
          <button type="button" className="secondary" onClick={() => void dev("parent", "wheel_spinning")}>
            Guardian of Wen
          </button>
          <button type="button" className="secondary" onClick={() => void dev("teacher")}>
            Preview teacher
          </button>
        </div>
      ) : null}
    </main>
  );
}

export default function StaffLogin() {
  return (
    <Suspense fallback={null}>
      <StaffLoginForm />
    </Suspense>
  );
}
