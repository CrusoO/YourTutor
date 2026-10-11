"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import {
  devStaffToken,
  locale,
  requestStaffCode,
  setStaffToken,
  verifyStaffCode,
  whoAmI,
} from "@/lib/api";
import { t } from "@/lib/messages";

const DEV = process.env.NEXT_PUBLIC_DEV_TOOLS === "true";

/** Sign-in for guardians and teachers: an email, then the code that arrives by email. */
export default function StaffLogin() {
  const router = useRouter();
  const copy = t(locale());
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  async function go() {
    const me = await whoAmI();
    router.push(me.role === "teacher" || me.role === "admin" ? "/teacher" : "/guardian");
  }

  async function send() {
    setError("");
    try {
      await requestStaffCode(email.trim());
      setSent(true);
    } catch {
      setError(copy.loadError);
    }
  }

  async function verify() {
    setError("");
    try {
      await verifyStaffCode(email.trim(), code.trim());
      await go();
    } catch {
      setStaffToken("");
      setError(copy.staffWrongCode);
    }
  }

  async function dev(role: "parent" | "teacher", scenario?: string) {
    await devStaffToken(role, scenario);
    await go();
  }

  return (
    <main className="stack" data-testid="staff-login">
      <h1>{copy.staffLoginTitle}</h1>
      <label className="stack">
        {copy.staffEmail}
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
        />
      </label>
      {sent ? (
        <label className="stack">
          {copy.staffCode}
          <input value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" />
        </label>
      ) : null}
      {sent ? (
        <button type="button" onClick={() => void verify()}>
          {copy.staffVerify}
        </button>
      ) : (
        <button type="button" disabled={!email.includes("@")} onClick={() => void send()}>
          {copy.staffSendCode}
        </button>
      )}
      {error ? <p className="banner">{error}</p> : null}
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
