import type { ReactNode } from "react";
import Link from "next/link";
import { DRAFT_BANNER, DRAFT_NOTE, legalLinks, legalNavLabel } from "@/lib/legal-copy";

/** The frame shared by /privacy, /terms and /grievance: a draft banner, the title, and links to the three pages. */
export default function LegalShell({ title, intro, children }: { title: string; intro: string; children: ReactNode }) {
  return (
    <main className="stack" lang="en">
      <Link href="/" className="muted">
        ← Home
      </Link>
      <aside className="banner" role="note" aria-label="Draft status" data-testid="draft-banner">
        <strong>{DRAFT_BANNER}</strong>
        <p>{DRAFT_NOTE}</p>
      </aside>
      <h1>{title}</h1>
      <p>{intro}</p>
      <nav aria-label={legalNavLabel} data-testid="legal-nav">
        <ul className="stack" style={{ listStyle: "none", padding: 0, flexDirection: "row", flexWrap: "wrap", gap: 16 }}>
          {legalLinks.map((link) => (
            <li key={link.id}>
              <Link href={link.href}>{link.label}</Link>
            </li>
          ))}
        </ul>
      </nav>
      {children}
    </main>
  );
}

/** A heading with paragraphs under it. */
export function Section({ id, heading, body, list, children }: { id: string; heading: string; body?: readonly string[]; list?: readonly string[]; children?: ReactNode }) {
  return (
    <section className="stack" aria-labelledby={`${id}-h`}>
      <h2 id={`${id}-h`}>{heading}</h2>
      {body?.map((line) => <p key={line}>{line}</p>)}
      {list ? (
        <ul>
          {list.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      ) : null}
      {children}
    </section>
  );
}
