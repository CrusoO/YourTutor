import LegalShell, { Section } from "@/components/legal/LegalShell";
import { terms } from "@/lib/legal-copy";

export const metadata = { title: terms.pageTitle };

/** DRAFT, under legal review. Limitation text is deliberately minimal and marked for counsel. */
export default function TermsPage() {
  return (
    <LegalShell title={terms.title} intro={terms.intro}>
      {terms.sections.map((section) => (
        <Section key={section.id} id={section.id} heading={section.heading} body={section.body} list={"list" in section ? section.list : undefined} />
      ))}
    </LegalShell>
  );
}
