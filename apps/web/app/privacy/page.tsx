import LegalShell, { Section } from "@/components/legal/LegalShell";
import { inventory, privacy } from "@/lib/legal-copy";

export const metadata = { title: privacy.pageTitle };

/** DRAFT, under legal review. Written from the code's data inventory (lib/legal-copy.ts). */
export default function PrivacyPage() {
  const s = privacy.sections;
  const labels = privacy.fieldLabels;
  return (
    <LegalShell title={privacy.title} intro={privacy.intro}>
      <Section id="short" heading={s.short.heading} list={s.short.points} />
      <Section id="who" heading={s.who.heading} body={s.who.body} />
      <section className="stack" aria-labelledby="inventory-h" data-testid="inventory">
        <h2 id="inventory-h">{s.inventoryHeading}</h2>
        <p>{s.inventoryIntro}</p>
        {inventory.map((item) => (
          <article key={item.id} className="stack" aria-labelledby={`inv-${item.id}`} data-testid={`inventory-${item.id}`}>
            <h3 id={`inv-${item.id}`}>{item.title}</h3>
            <dl className="stack">
              {(["what", "why", "where", "who", "kept", "thirdParty"] as const).map((key) => (
                <div key={key}>
                  <dt>
                    <strong>{labels[key]}</strong>
                  </dt>
                  <dd>{item[key]}</dd>
                </div>
              ))}
            </dl>
          </article>
        ))}
      </section>
      <Section id="children" heading={s.children.heading} body={s.children.body}>
        <ul>
          {s.children.today.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
        <p>{s.children.note}</p>
      </Section>
      <Section id="rights" heading={s.rights.heading} body={s.rights.body} />
      <Section id="changes" heading={s.changes.heading} body={s.changes.body} />
      <Section id="contact" heading={s.contact.heading} body={s.contact.body} />
    </LegalShell>
  );
}
