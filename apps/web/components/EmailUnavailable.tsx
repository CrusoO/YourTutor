"use client";

import Link from "next/link";
import { useCopy } from "@/lib/locale";

/** Shown when the sign-in code could not be sent: say so plainly and offer the guest path. */
export default function EmailUnavailable() {
  const copy = useCopy();
  return (
    <div className="stack" data-testid="email-unavailable">
      <p className="banner">{copy.emailUnavailable}</p>
      <Link href="/start" className="button" data-testid="continue-as-guest">
        {copy.continueAsGuest}
      </Link>
    </div>
  );
}
