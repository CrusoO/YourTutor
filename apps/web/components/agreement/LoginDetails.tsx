"use client";

import Link from "next/link";
import { useState } from "react";
import { loginDetails, settings } from "@/lib/agreement-copy";
import { makeLoginDetails } from "@/lib/agreements-api";

/** Guardian: a short username and PIN for a child (the PIN is shown once), and the link to Settings. */
export default function LoginDetails({ studentId }: { studentId: string }) {
  const [made, setMade] = useState<{ username: string; pin: string } | null>(null);
  const [failed, setFailed] = useState(false);
  return (
    <section className="stack" data-testid="login-details">
      <button
        type="button"
        className="secondary"
        onClick={() =>
          makeLoginDetails(studentId)
            .then((d) => {
              setMade(d);
              setFailed(false);
            })
            .catch(() => setFailed(true))
        }
      >
        {loginDetails.button}
      </button>
      {made ? (
        <p className="card" role="status">
          {loginDetails.result}
          <br />
          {loginDetails.username}: <strong data-testid="made-username">{made.username}</strong> · {loginDetails.pin}:{" "}
          <strong data-testid="made-pin">{made.pin}</strong>
        </p>
      ) : null}
      {failed ? <p className="banner">!</p> : null}
      <Link href="/settings/agreements">{settings.title}</Link>
    </section>
  );
}
