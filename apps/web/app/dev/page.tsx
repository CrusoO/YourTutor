"use client";

import Link from "next/link";
import { notFound, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  listDevScenarios,
  seedDevScenarios,
  setStudentId,
  studentLogin,
  today,
  type DevScenario,
} from "@/lib/api";
import { devToolsEnabled } from "@/lib/dev";

export default function DevPage() {
  if (!devToolsEnabled()) notFound();
  const router = useRouter();
  const [scenarios, setScenarios] = useState<DevScenario[] | null>(null);
  const [error, setError] = useState("");
  const [resetting, setResetting] = useState(false);

  useEffect(() => {
    listDevScenarios()
      .then((body) => setScenarios(body.scenarios))
      .catch(() =>
        setError("Could not load scenarios. Start the API with DEV_TOOLS=true and ALLOW_DRAFT_CONTENT=true."),
      );
  }, []);

  async function resetAll() {
    setError("");
    setResetting(true);
    try {
      await seedDevScenarios();
      const body = await listDevScenarios();
      setScenarios(body.scenarios);
    } catch {
      setError("Could not reset the scenarios. Check the API log.");
    } finally {
      setResetting(false);
    }
  }

  async function loginAs(scenario: DevScenario) {
    setError("");
    try {
      await studentLogin(scenario.family_code, scenario.pin);
      const me = await today();
      setStudentId(me.student_id);
      router.push("/today");
    } catch {
      setError(`Could not log in as ${scenario.title}. Seed the scenarios first.`);
    }
  }

  return (
    <main className="stack">
      <h1>Dev scenarios</h1>
      <p>Preview students in known states. Dev only.</p>
      <p>
        <Link href="/dev/lessons">Lessons</Link>
      </p>
      <button type="button" className="secondary" disabled={resetting} onClick={resetAll}>
        {resetting ? "Resetting… (about a minute)" : "Reset scenarios"}
      </button>
      {error ? <p className="banner">{error}</p> : null}
      {scenarios?.map((scenario) => (
        <section key={scenario.name} className="stack">
          <h2>{scenario.title}</h2>
          <p>{scenario.description}</p>
          <p>
            Family code {scenario.family_code} · PIN {scenario.pin}
          </p>
          {scenario.seeded ? null : (
            <p className="banner">
              Not seeded. Run <code>python -m app.dev seed_scenarios</code>.
            </p>
          )}
          <button type="button" onClick={() => loginAs(scenario)}>
            Log in as {scenario.title}
          </button>
        </section>
      ))}
    </main>
  );
}
