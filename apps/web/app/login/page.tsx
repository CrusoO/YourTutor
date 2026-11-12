"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { ensureDevStudent, skipLogin } from "@/lib/dev-auth";
import { DRAFT_BANNER } from "@/lib/legal-copy";
import { Brand } from "@/components/ui/brand";
import StorageNotice from "@/components/StorageNotice";
import LegalLinks from "@/components/legal/LegalLinks";
import { LandingLanguageProvider, useLandingLanguage } from "../brownie/LandingLanguage";
import { AdultIcon, Chevron, GuardianIcon, StudentIcon, TeacherIcon } from "./icons";
import { signin, type SigninRole } from "./loginCopy";
import StudentForm from "./StudentForm";
import styles from "./login.module.css";

const CARDS: { role: SigninRole; icon: ReactNode; href?: string }[] = [
  { role: "student", icon: <StudentIcon /> },
  { role: "guardian", icon: <GuardianIcon />, href: "/staff/login?as=guardian" },
  { role: "teacher", icon: <TeacherIcon />, href: "/staff/login?as=teacher" },
  { role: "adult", icon: <AdultIcon />, href: "/staff/login?as=adult" },
];

/** English, Hindi, Nepali: the same landing-language setting the homepage uses, with 44 px targets. */
function Languages() {
  const { language, setLanguage, copy } = useLandingLanguage();
  return (
    <div className={styles.langs} role="group" aria-label={copy.hero.languageLabel}>
      {copy.hero.languageOptions.map((option) => (
        <button
          key={option.id}
          type="button"
          lang={option.id}
          aria-pressed={language === option.id}
          className={styles.lang}
          onClick={() => setLanguage(option.id as typeof language)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

function LoginPageContent() {
  const router = useRouter();
  const { copy, language } = useLandingLanguage();
  const [role, setRole] = useState<"student" | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const chosen = useRef(false);

  // Login UI skipped while NEXT_PUBLIC_SKIP_LOGIN=true (dev learning-flow testing).
  useEffect(() => {
    if (!skipLogin()) return;
    ensureDevStudent()
      .then(() => router.replace("/brownie-chat"))
      .catch(() => {});
  }, [router]);

  // Move focus to the new step's heading so a keyboard or screen-reader user lands on it.
  useEffect(() => {
    if (chosen.current) heading.current?.focus();
  }, [role]);

  return (
    <div className={styles.page}>
      <main className={styles.column} lang={language} data-testid="login-page">
        <div className={styles.top}>
          <Link href="/" className={styles.home} aria-label={copy.auth.homepage}>
            <Brand showName={false} />
            <span className={styles.name}>Brownie</span>
          </Link>
          <Languages />
        </div>
        <aside className={styles.draft} role="note" aria-label={signin.draft} data-testid="draft-banner" lang="en">
          <strong>{DRAFT_BANNER}</strong>
        </aside>
        <StorageNotice />
        <h1 className={styles.heading} tabIndex={-1} ref={heading}>
          {copy.auth.title}
        </h1>

        {role === "student" ? (
          <>
            <button
              type="button"
              className={styles.backButton}
              onClick={() => {
                chosen.current = true;
                setRole(null);
              }}
              data-testid="back-to-roles"
            >
              ← {signin.back}
            </button>
            <StudentForm
              mismatch={copy.auth.loginError}
              labels={{ code: copy.auth.familyCode, pin: copy.auth.pin, submit: copy.auth.signIn }}
            />
          </>
        ) : (
          <>
            <p className={styles.lead} id="who-lead">
              <strong>{signin.who}</strong> {signin.whoHint}
            </p>
            <ul className={styles.cards} aria-labelledby="who-lead" data-testid="role-cards">
              {CARDS.map(({ role: r, icon, href }) => {
                const text = signin.roles[r];
                const body = (
                  <>
                    <span className={styles.icon}>{icon}</span>
                    <span className={styles.cardText}>
                      <span className={styles.cardName}>{text.name}</span>
                      <span className={styles.cardHint}>{text.hint}</span>
                    </span>
                    <span className={styles.chevron}><Chevron /></span>
                  </>
                );
                return (
                  <li key={r}>
                    {href ? (
                      <Link href={href} className={styles.card} data-testid={`role-${r}`}>
                        {body}
                      </Link>
                    ) : (
                      <button
                        type="button"
                        className={styles.card}
                        data-testid={`role-${r}`}
                        onClick={() => {
                          chosen.current = true;
                          setRole("student");
                        }}
                      >
                        {body}
                      </button>
                    )}
                  </li>
                );
              })}
            </ul>
          </>
        )}

        <div className={styles.guest}>
          <Link href="/start" className={styles.link} data-testid="try-guest">
            {copy.auth.tryAsGuest}
          </Link>
          <span className={styles.hint}>{signin.guestHint}</span>
        </div>
        <div className={styles.footer}>
          <LegalLinks />
        </div>
      </main>
    </div>
  );
}

export default function LoginPage() {
  return (
    <LandingLanguageProvider>
      <LoginPageContent />
    </LandingLanguageProvider>
  );
}
