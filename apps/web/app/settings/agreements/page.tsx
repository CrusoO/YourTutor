"use client";

import Link from "next/link";
import AgreementSettings from "@/components/agreement/AgreementSettings";
import AgreementShell from "@/components/agreement/AgreementShell";
import { settings, ui } from "@/lib/agreement-copy";
import { staffToken } from "@/lib/api";

/** Settings: withdraw or re-tick any item of the agreements a guardian, adult or teacher gave. */
export default function AgreementSettingsPage() {
  return (
    <AgreementShell title={settings.title}>
      {staffToken() ? (
        <AgreementSettings />
      ) : (
        <p>
          {ui.signInFirst} <Link href="/staff/login">{ui.signInLink}</Link>
        </p>
      )}
    </AgreementShell>
  );
}
