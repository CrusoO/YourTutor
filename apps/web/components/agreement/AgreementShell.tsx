import type { ReactNode } from "react";
import LegalLinks from "@/components/legal/LegalLinks";
import { DRAFT_BANNER } from "@/lib/legal-copy";

/** The frame for every agreement-related screen: the draft banner first, English only, privacy links last. */
export default function AgreementShell({ title, children }: { title: string; children: ReactNode }) {
  return (
    <main className="stack" lang="en">
      <aside className="banner" role="note" aria-label="Draft status" data-testid="draft-banner">
        <strong>{DRAFT_BANNER}</strong>
      </aside>
      <h1>{title}</h1>
      {children}
      <LegalLinks />
    </main>
  );
}
