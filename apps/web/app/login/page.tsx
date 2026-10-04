"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ensureDevStudent, skipLogin } from "@/lib/dev-auth";
import { locale, setLocale, setStudentId, studentLogin, today } from "@/lib/api";
import { t, type Locale } from "@/lib/messages";

export default function LoginPage() {
  const router = useRouter();

  // Login UI skipped while NEXT_PUBLIC_SKIP_LOGIN=true (dev learning-flow testing).
  useEffect(() => {
    if (!skipLogin()) return;
    ensureDevStudent()
      .then(() => router.replace("/today"))
      .catch(() => {});
  }, [router]);
  const copy = t(locale());
  const [family, setFamily] = useState("");
  const [pin, setPin] = useState("");
  const [error, setError] = useState("");
  const [lang, setLang] = useState<Locale>((locale() as Locale) || "en");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await studentLogin(family.trim().toUpperCase(), pin.trim());
      const me = await today();
      setStudentId(me.student_id);
      if (me.locale) setLocale(me.locale);
      router.push("/today");
    } catch {
      setError(copy.loginError);
    }
  }

  return (
    <main className="stack">
      <h1>{copy.loginTitle}</h1>
      <div className="lang">
        {(["en", "ne", "as"] as Locale[]).map((code) => (
          <button
            key={code}
            type="button"
            className={lang === code ? undefined : "ghost"}
            onClick={() => {
              setLang(code);
              setLocale(code);
            }}
          >
            {code}
          </button>
        ))}
      </div>
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
    </main>
  );
}
