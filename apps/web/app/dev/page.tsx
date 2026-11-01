"use client";

import Link from "next/link";
import { notFound, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  devStaffToken,
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
        setError(
          "Could not load scenarios. Start the API with DEV_TOOLS=true and ALLOW_DRAFT_CONTENT=true.",
        ),
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
      router.push("/brownie-chat");
    } catch {
      setError(
        `Could not log in as ${scenario.title}. Seed the scenarios first.`,
      );
    }
  }

  async function staffAs(role: "teacher" | "parent", scenario?: DevScenario) {
    setError("");
    try {
      await devStaffToken(role, scenario?.name);
      router.push("/brownie-chat");
    } catch {
      setError(
        "Could not sign in the preview adult. Seed the scenarios first.",
      );
    }
  }

  return (
    <main className="stack">
      <h1>Dev scenarios</h1>
      <p>Preview students in known states. Dev only.</p>
      <p>
        <Link href="/dev/lessons">Lessons</Link>
      </p>
      <button
        type="button"
        className="secondary"
        disabled={resetting}
        onClick={resetAll}
      >
        {resetting ? "Resetting… (about a minute)" : "Reset scenarios"}
      </button>
      <button
        type="button"
        className="secondary"
        onClick={() => staffAs("teacher")}
        data-testid="login-teacher"
      >
        Log in as the preview teacher
      </button>
      {error ? <p className="banner">{error}</p> : null}
      <div className="grid-cards">
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
            <button
              type="button"
              onClick={() => loginAs(scenario)}
              data-testid={`login-${scenario.name}`}
            >
              Log in as {scenario.title}
            </button>
            <button
              type="button"
              className="secondary"
              onClick={() => staffAs("parent", scenario)}
              data-testid={`parent-${scenario.name}`}
            >
              Parent of {scenario.title}
            </button>
          </section>
        ))}
      </div>
    </main>
  );
}
