"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ensureDevStudent, skipLogin } from "@/lib/dev-auth";
import { locale, setLocale, setStudentId, studentLogin, today } from "@/lib/api";
import { type Locale } from "@/lib/messages";
import { useCopy } from "@/lib/locale";
import { LanguageSwitch } from "@/components/ui/language-switch";

export default function LoginPage() {
  const router = useRouter();

  // Login UI skipped while NEXT_PUBLIC_SKIP_LOGIN=true (dev learning-flow testing).
  useEffect(() => {
    if (!skipLogin()) return;
    ensureDevStudent()
      .then(() => router.replace("/subjects"))
      .catch(() => {});
  }, [router]);
  const copy = useCopy();
  const [family, setFamily] = useState("");
  const [pin, setPin] = useState("");
  const [error, setError] = useState("");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await studentLogin(family.trim().toUpperCase(), pin.trim());
      const me = await today();
      setStudentId(me.student_id);
      if (me.locale) setLocale(me.locale);
      router.push("/subjects");
    } catch {
      setError(copy.loginError);
    }
  }

  return (
    <main className="stack">
      <h1>{copy.loginTitle}</h1>
      <LanguageSwitch />
      <form className="stack" onSubmit={onSubmit}>
        <label>
          {copy.familyCode}
          <input
            name="family_code"
            autoComplete="username"
            value={family}
            onChange={(e) => setFamily(e.target.value)}
          />
        </label>
        <label>
          {copy.pin}
          <input
            name="pin"
            type="password"
            inputMode="numeric"
            autoComplete="current-password"
            value={pin}
            onChange={(e) => setPin(e.target.value)}
          />
        </label>
        {error ? <p className="banner">{error}</p> : null}
        <button type="submit">{copy.signIn}</button>
      </form>
      <Link href="/start" className="muted" data-testid="try-guest">
        {copy.tryAsGuest}
      </Link>
    </main>
  );
}
