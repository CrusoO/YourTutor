import Link from "next/link";
import { legalLinks, legalNavLabel } from "@/lib/legal-copy";

/** Small row of links to the privacy, terms and grievance drafts, for screens where a privacy link is natural. */
export default function LegalLinks() {
  return (
    <nav aria-label={legalNavLabel} className="muted" data-testid="legal-links">
      {legalLinks.map((link, index) => (
        <span key={link.id}>
          {index > 0 ? " · " : null}
          <Link href={link.href}>{link.label}</Link>
        </span>
      ))}
    </nav>
  );
}
