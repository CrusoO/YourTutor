"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  closeGroup,
  explainLesson,
  groupSummary,
  myGroups,
  publishGroup,
  type GroupListing,
  type GroupSummary,
} from "@/lib/api";
import type { AiBlock } from "@/lib/lessons/ai-lesson";

/** Staff-facing, English only for now. */
const WORDS = {
  title: "Share a lesson with a group",
  intro: "Build a lesson on one question, read it through, then share the link. Everyone gets the same lesson, so you can see where the group is stuck.",
  signIn: "Sign in as a teacher to use this.",
  topic: "What should the lesson be about?",
  build: "Build the lesson",
  building: "Building… this takes about half a minute.",
  failed: "Couldn't build that lesson. Try again, or change the question.",
  review: "Read it through before you share it",
  reviewNote: "An AI wrote this. You are the one checking it: the right answers are marked.",
  publish: "Share this lesson",
  discard: "Start again",
  link: "Your link",
  copy: "Copy link",
  copied: "Copied.",
  yours: "Your lessons",
  none: "Nothing shared yet.",
  answered: "answered",
  results: "See results",
  close: "Stop collecting",
  closed: "Closed",
  waiting: (n: number, min: number) => `${n} of ${min} people have sent results. Results show when ${min} have, so nobody can be picked out.`,
  hidden: (cell: number) => `fewer than ${cell}`,
  wrong: "got it wrong",
  sureWrong: "were sure and wrong",
  ideas: "Ideas behind the wrong answers",
};

export default function GroupsPage() {
  const [access, setAccess] = useState<"checking" | "needed" | "ok">("checking");
  const [groups, setGroups] = useState<GroupListing[]>([]);
  const [topic, setTopic] = useState("");
  const [state, setState] = useState<"idle" | "building" | "failed">("idle");
  const [draft, setDraft] = useState<{ prompt: string; blocks: AiBlock[] } | null>(null);
  const [published, setPublished] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [summary, setSummary] = useState<GroupSummary | null>(null);

  async function refresh() {
    try {
      setGroups((await myGroups()).groups);
      setAccess("ok");
    } catch {
      setAccess("needed");
    }
  }
  useEffect(() => {
    void refresh();
  }, []);

  async function build() {
    const prompt = topic.trim();
    if (prompt.length < 2) return;
    setState("building");
    setDraft(null);
    setPublished(null);
    try {
      const result = await explainLesson(prompt, "en");
      if (result.kind !== "lesson") throw new Error("no lesson");
      setDraft({ prompt, blocks: result.blocks });
      setState("idle");
    } catch {
      setState("failed");
    }
  }

  async function publish() {
    if (!draft) return;
    try {
      const made = await publishGroup(draft.prompt, "en", draft.blocks);
      setPublished(`${window.location.origin}${made.path}`);
      setDraft(null);
      setTopic("");
      await refresh();
    } catch {
      setState("failed");
    }
  }

  async function copyLink() {
    if (!published) return;
    try {
      await navigator.clipboard.writeText(published);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  if (access === "checking") return <main className="p-6 text-muted">…</main>;
  if (access === "needed") {
    return (
      <main className="mx-auto flex max-w-xl flex-col gap-4 p-6" data-testid="groups-signin">
        <h1 className="m-0 text-[1.5rem] font-light text-ink">{WORDS.title}</h1>
        <p className="m-0 text-ink">{WORDS.signIn}</p>
        <a href="/login">Sign in</a>
      </main>
    );
  }

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-col gap-8 p-6" data-testid="groups">
      <header className="flex flex-col gap-2">
        <h1 className="m-0 text-[1.75rem] font-light text-ink">{WORDS.title}</h1>
        <p className="m-0 text-[0.9375rem] text-muted">{WORDS.intro}</p>
      </header>

      <section className="flex flex-col gap-3" aria-label={WORDS.topic}>
        <label htmlFor="group-topic" className="text-[0.875rem] text-ink">
          {WORDS.topic}
        </label>
        <input
          id="group-topic"
          value={topic}
          maxLength={300}
          onChange={(e) => setTopic(e.target.value)}
          className="min-h-12 rounded-xl border border-line bg-surface px-4 text-[0.9375rem] text-ink outline-none focus:border-accent"
          data-testid="group-topic"
        />
        <div className="flex items-center gap-3">
          <Button onClick={build} disabled={state === "building" || topic.trim().length < 2} data-testid="group-build">
            {WORDS.build}
          </Button>
          {state === "building" ? <span className="text-[0.875rem] text-muted" role="status">{WORDS.building}</span> : null}
          {state === "failed" ? <span className="text-[0.875rem] text-warning" role="alert">{WORDS.failed}</span> : null}
        </div>
      </section>

      {draft ? <Review draft={draft} onPublish={publish} onDiscard={() => setDraft(null)} /> : null}

      {published ? (
        <section className="flex flex-col gap-2 rounded-2xl border border-line bg-surface p-4" data-testid="group-published">
          <p className="m-0 text-[0.875rem] text-muted">{WORDS.link}</p>
          <code className="break-all text-[0.875rem] text-ink" data-testid="group-link">{published}</code>
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" onClick={copyLink}>
              {WORDS.copy}
            </Button>
            {copied ? <span className="text-[0.8125rem] text-muted" role="status">{WORDS.copied}</span> : null}
          </div>
        </section>
      ) : null}

      <section className="flex flex-col gap-3" aria-labelledby="yours">
        <h2 id="yours" className="m-0 text-[1.0625rem] font-medium text-ink">
          {WORDS.yours}
        </h2>
        {groups.length === 0 ? <p className="m-0 text-muted">{WORDS.none}</p> : null}
        <ul className="m-0 flex list-none flex-col gap-3 p-0">
          {groups.map((g) => (
            <li key={g.code} className="flex flex-col gap-2 rounded-2xl border border-line p-4" data-testid="group-row">
              <p className="m-0 text-[0.9375rem] text-ink">{g.prompt}</p>
              <p className="m-0 text-[0.8125rem] text-muted">
                {g.participants} {WORDS.answered}
                {g.closed ? ` · ${WORDS.closed}` : ""}
              </p>
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" size="sm" onClick={async () => setSummary(await groupSummary(g.code))} data-testid="group-results">
                  {WORDS.results}
                </Button>
                {g.closed ? null : (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={async () => {
                      await closeGroup(g.code);
                      await refresh();
                    }}
                  >
                    {WORDS.close}
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      </section>

      {summary ? <Summary summary={summary} /> : null}
    </main>
  );
}

function Review({ draft, onPublish, onDiscard }: { draft: { prompt: string; blocks: AiBlock[] }; onPublish: () => void; onDiscard: () => void }) {
  return (
    <section className="flex flex-col gap-4 rounded-2xl border border-line p-4" aria-labelledby="review" data-testid="group-review">
      <h2 id="review" className="m-0 text-[1.0625rem] font-medium text-ink">
        {WORDS.review}
      </h2>
      <p className="m-0 text-[0.8125rem] text-muted">{WORDS.reviewNote}</p>
      <ol className="m-0 flex list-none flex-col gap-4 p-0">
        {draft.blocks.map((block, i) => (
          <li key={i} className="flex flex-col gap-1 text-[0.875rem] text-ink">
            <span className="text-[0.6875rem] uppercase tracking-wide text-muted">{block.kind === "widget" ? block.widget_kind : block.kind}</span>
            {block.kind === "hook" ? <span>{block.text} <strong>{block.question}</strong></span> : null}
            {block.kind === "explain" ? <span>{block.text}</span> : null}
            {block.kind === "transfer" ? <span>{block.scenario} <strong>{block.question}</strong></span> : null}
            {block.kind === "recap" ? <span>{block.three_bullets.join(" · ")}</span> : null}
            {block.kind === "predict" || block.kind === "check" ? (
              <>
                <strong>{block.kind === "predict" ? block.prompt : block.question}</strong>
                {block.options ? (
                  <ul className="m-0 list-none p-0">
                    {block.options.map((option, k) => (
                      <li key={k}>
                        {k === block.correct ? "✓ " : "· "}
                        {option}
                        {block.misconceptions?.[k] ? <em className="text-muted"> ({block.misconceptions[k]})</em> : null}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </>
            ) : null}
          </li>
        ))}
      </ol>
      <div className="flex gap-3">
        <Button onClick={onPublish} data-testid="group-publish">
          {WORDS.publish}
        </Button>
        <Button variant="ghost" onClick={onDiscard}>
          {WORDS.discard}
        </Button>
      </div>
    </section>
  );
}

function Summary({ summary }: { summary: GroupSummary }) {
  return (
    <section className="flex flex-col gap-4 rounded-2xl border border-line p-4" aria-label={summary.prompt} data-testid="group-summary">
      <h2 className="m-0 text-[1.0625rem] font-medium text-ink">{summary.prompt}</h2>
      {!summary.ready ? (
        <p className="m-0 text-muted" data-testid="group-waiting">
          {WORDS.waiting(summary.participants, summary.minimum)}
        </p>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-4 p-0">
          {summary.questions.map((q) => (
            <li key={q.question} className="flex flex-col gap-1 text-[0.875rem] text-ink" data-testid="group-question">
              <strong>{q.question}</strong>
              <span>
                {q.answered} {WORDS.answered}: {q.wrong ?? WORDS.hidden(summary.cell)} {WORDS.wrong}
                {q.sure_wrong !== null ? `, ${q.sure_wrong} ${WORDS.sureWrong}` : ""}
              </span>
              {q.ideas.length > 0 ? (
                <span className="text-muted">
                  {WORDS.ideas}: {q.ideas.map((i) => `${i.idea} (${i.count})`).join("; ")}
                </span>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
