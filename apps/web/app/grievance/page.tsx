import LegalShell, { Section } from "@/components/legal/LegalShell";
import { grievance } from "@/lib/legal-copy";

export const metadata = { title: grievance.pageTitle };

/** DRAFT. Every contact detail is a marked placeholder until the owner supplies it. */
export default function GrievancePage() {
  const g = grievance;
  return (
    <LegalShell title={g.title} intro={g.intro}>
      <Section id="contact" heading={g.contact.heading}>
        <dl className="stack" data-testid="grievance-contact">
          {g.contact.fields.map((field) => (
            <div key={field.id}>
              <dt>
                <strong>{field.label}</strong>
              </dt>
              <dd data-testid={`contact-${field.id}`}>{field.value}</dd>
            </div>
          ))}
        </dl>
        <p className="muted">{g.contact.note}</p>
      </Section>
      <Section id="send" heading={g.send.heading} list={g.send.list} />
      <section className="stack" aria-labelledby="process-h">
        <h2 id="process-h">{g.process.heading}</h2>
        <ol>
          {g.process.steps.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
        <p>
          <strong>{g.process.time.label}:</strong> <span data-testid="reply-time">{g.process.time.value}</span>
        </p>
      </section>
      <Section id="today" heading={g.today.heading} body={g.today.body} />
    </LegalShell>
  );
}
