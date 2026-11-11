"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import AdultStart from "@/components/agreement/AdultStart";
import AgreementForm from "@/components/agreement/AgreementForm";
import AgreementShell from "@/components/agreement/AgreementShell";
import { ui, type Role } from "@/lib/agreement-copy";
import { ApiError, acceptAgreement } from "@/lib/agreements-api";
import { staffToken, whoAmI } from "@/lib/api";

type Step = "loading" | "signin" | "choose" | "form" | "adult-age";

/**
 * Shown once, after the first sign-in, for the role the person has: teachers accept the terms, and a new
 * account chooses guardian or adult learner. A guardian's one screen covers every child's consent.
 */
export default function AgreementPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("loading");
  const [needed, setNeeded] = useState<string[]>([]);
  const [role, setRole] = useState<Role>("guardian");
  const [adultItems, setAdultItems] = useState<{ items: string[]; version: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!staffToken()) {
      setStep("signin");
      return;
    }
    whoAmI()
      .then((me: { role: string; agreements?: string[] }) => {
        const list = me.agreements ?? [];
        if (list.length === 0) {
          router.replace(me.role === "teacher" || me.role === "admin" ? "/teacher" : "/guardian");
          return;
        }
        setNeeded(list);
        if (list.length === 1) {
          setRole(list[0] as Role);
          setStep("form");
        } else setStep("choose");
      })
      .catch(() => setStep("signin"));
  }, [router]);

  async function accept(items: string[], version: string) {
    setBusy(true);
    setError("");
    if (role === "adult") {
      setAdultItems({ items, version });
      setStep("adult-age");
      setBusy(false);
      return;
    }
    try {
      await acceptAgreement(role, version, items);
      router.push(role === "teacher" ? "/teacher" : "/guardian");
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 409 ? ui.versionChanged : ui.failed);
      setBusy(false);
    }
  }

  return (
    <AgreementShell title="Before you start">
      {step === "loading" ? <p>…</p> : null}
      {step === "signin" ? (
        <p>
          {ui.signInFirst} <Link href="/staff/login">{ui.signInLink}</Link>
        </p>
      ) : null}
      {step === "choose" ? (
        <section className="stack" data-testid="choose-role">
          <h2>{ui.chooseRole}</h2>
          {needed.includes("guardian") ? (
            <button
              type="button"
              onClick={() => {
                setRole("guardian");
                setStep("form");
              }}
            >
              {ui.roleGuardian}
            </button>
          ) : null}
          {needed.includes("adult") ? (
            <button
              type="button"
              className="secondary"
              onClick={() => {
                setRole("adult");
                setStep("form");
              }}
            >
              {ui.roleAdult}
            </button>
          ) : null}
        </section>
      ) : null}
      {step === "form" ? <AgreementForm role={role} busy={busy} onSubmit={(i, v) => void accept(i, v)} /> : null}
      {step === "adult-age" && adultItems ? <AdultStart accepted={adultItems.items} version={adultItems.version} /> : null}
      {error ? <p className="banner">{error}</p> : null}
    </AgreementShell>
  );
}
