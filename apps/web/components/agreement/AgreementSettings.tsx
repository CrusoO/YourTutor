"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Tick } from "@/components/agreement/AgreementForm";
import { roleTitle, settings, ui, type Role } from "@/lib/agreement-copy";
import {
  acceptAgreement,
  getCatalog,
  myAgreements,
  withdrawItem,
  type Catalog,
  type MyAgreements,
} from "@/lib/agreements-api";

/**
 * Everything the person agreed to, each item its own box. Unticking withdraws it at once (the same one
 * step as ticking it was); an optional item can be ticked again. A required item asks first, because
 * withdrawing it stops the service for that person's learners.
 */
export default function AgreementSettings() {
  const [mine, setMine] = useState<MyAgreements | null>(null);
  const [catalogs, setCatalogs] = useState<Record<string, Catalog>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    myAgreements()
      .then(async (data) => {
        setMine(data);
        const found: Record<string, Catalog> = {};
        for (const row of data.agreements) found[row.role] = await getCatalog(row.role);
        setCatalogs(found);
      })
      .catch(() => setError(ui.failed));
  }, []);

  async function change(role: string, itemId: string, required: boolean, on: boolean) {
    if (!mine) return;
    const row = mine.agreements.find((a) => a.role === role);
    const catalog = catalogs[role];
    if (!row || !catalog) return;
    if (!on && required && !window.confirm(settings.withdrawRequired)) return;
    setBusy(true);
    setError("");
    try {
      setMine(
        on
          ? await acceptAgreement(role, catalog.version, [...row.items, itemId])
          : await withdrawItem(role, itemId),
      );
    } catch {
      setError(ui.failed);
    }
    setBusy(false);
  }

  if (!mine) return error ? <p className="banner">{error}</p> : <p>…</p>;
  return (
    <div className="stack" data-testid="agreement-settings">
      <p>{settings.intro}</p>
      {mine.agreements.length === 0 ? <p>{settings.none}</p> : null}
      {mine.agreements.map((row) => {
        const catalog = catalogs[row.role];
        if (!catalog) return null;
        return (
          <section key={row.role} className="stack" data-testid={`settings-${row.role}`}>
            <h2>{roleTitle[row.role as Role]}</h2>
            <p className="muted">
              {settings.version}: {row.version}
            </p>
            {catalog.items.map((item) => (
              <Tick
                key={item.id}
                role={row.role as Role}
                item={item}
                checked={row.items.includes(item.id)}
                disabled={busy}
                onChange={(on) => void change(row.role, item.id, item.required, on)}
              />
            ))}
            {!row.complete ? (
              <Link href="/agreement" data-testid="agree-again">
                {settings.agreeAgain}
              </Link>
            ) : null}
          </section>
        );
      })}
      {error ? <p className="banner">{error}</p> : null}
    </div>
  );
}
