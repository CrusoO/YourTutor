"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ensureDevStudent, skipLogin } from "@/lib/dev-auth";
import { locale, setLocale, setStudentId, studentLogin, today } from "@/lib/api";
import { LandingLanguages } from "../brownie/Interactions";
import { LandingLanguageProvider, useLandingLanguage } from "../brownie/LandingLanguage";

function LoginPageContent() {
  const router = useRouter();
  const { copy, language } = useLandingLanguage();

  // Login UI skipped while NEXT_PUBLIC_SKIP_LOGIN=true (dev learning-flow testing).
  useEffect(() => {
    if (!skipLogin()) return;
    ensureDevStudent()
      .then(() => router.replace("/subjects"))
      .catch(() => {});
  }, [router]);
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
      setError(copy.auth.loginError);
    }
  }

  return (
    <main className="stack" lang={language}>
      <Link href="/" className="muted" aria-label={copy.auth.homepage}>
        ← {copy.auth.homepage}
      </Link>
      <h1>{copy.auth.title}</h1>
      <LandingLanguages />
      <form className="stack" onSubmit={onSubmit}>
        <label>
          {copy.auth.familyCode}
          <input
            name="family_code"
            autoComplete="username"
            value={family}
            onChange={(e) => setFamily(e.target.value)}
          />
        </label>
        <label>
          {copy.auth.pin}
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
        <button type="submit">{copy.auth.signIn}</button>
      </form>
      <Link href="/start" className="muted" data-testid="try-guest">
        {copy.auth.tryAsGuest}
      </Link>
    </main>
  );
}

export default function LoginPage() {
  return (
    <LandingLanguageProvider>
      <LoginPageContent />
    </LandingLanguageProvider>
  );
}
