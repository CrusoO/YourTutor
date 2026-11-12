"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  devStaffToken,
  isEmailUnavailable,
  isSmsUnavailable,
  requestStaffCode,
  setStaffToken,
  verifyStaffCode,
  whoAmI,
  type Contact,
} from "@/lib/api";
import { getAuthOptions } from "@/lib/agreements-api";
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
export default function StaffLogin() {
  const router = useRouter();
  const copy = useCopy();
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
    else router.push(me.role === "teacher" || me.role === "admin" ? "/teacher" : "/guardian");
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
      <StorageNotice />
      <h1>{copy.staffLoginTitle}</h1>
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
      {error ? <p className="banner">{error}</p> : null}
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
