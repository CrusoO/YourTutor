"use client";

import { FormEvent, useState } from "react";
import { enrolPilot } from "@/lib/api";

export default function PilotPage() {
  const [first, setFirst] = useState("Pema");
  const [curriculumId, setCurriculumId] = useState("");
  const [paper, setPaper] = useState("paper-consent-1");
  const [card, setCard] = useState<Record<string, string> | null>(null);
  const [error, setError] = useState("");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const body = await enrolPilot({
        first_name: first,
        paper_ref: paper,
        grade: 9,
        board: curriculumId,
        scopes: ["tutoring", "research_pseudonymised"],
      });
      setCard(body);
    } catch (err) {
      setError(err instanceof Error ? err.message : "enrol failed");
    }
  }

  return (
    <main className="stack">
      <h1>Pilot enrol</h1>
      <form className="stack" onSubmit={onSubmit}>
        <label>
          First name
          <input value={first} onChange={(e) => setFirst(e.target.value)} />
        </label>
        <label>
          Curriculum id
          <input
            value={curriculumId}
            onChange={(e) => setCurriculumId(e.target.value)}
            required
          />
        </label>
        <label>
          Paper consent reference
          <input value={paper} onChange={(e) => setPaper(e.target.value)} />
        </label>
        <button type="submit">Create login card</button>
      </form>
      {error ? <p className="banner">{error}</p> : null}
      {card ? (
        <section className="banner">
          <p>{card.first_name}</p>
          <p>Family code: {card.family_code}</p>
          <p>PIN: {card.pin}</p>
          <p className="muted">No surname or other PII on this card.</p>
        </section>
      ) : null}
    </main>
  );
}
