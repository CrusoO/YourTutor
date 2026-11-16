"use client";

import { notFound } from "next/navigation";
import { useState, type ReactNode } from "react";
import {
  AnswerGroup,
  AnswerOption,
  BottomTabBar,
  ConfidenceRow,
  ContinueCard,
  EmptyState,
  FeedbackCard,
  HintLadder,
  IDontKnowButton,
  LEARN_COPY_EN as C,
  ProgressBar,
  QuestionCard,
  SkeletonCard,
  TopicChip,
  TrustChip,
} from "@/components/learn";
import { devToolsEnabled } from "@/lib/dev";

const CONF = [
  { value: "guess", label: C.confidence.guessing },
  { value: "think", label: C.confidence.thinkSo },
  { value: "sure", label: C.confidence.sure },
] as const;

const TABS = [
  { id: "home", label: C.tabs.home, href: "/", icon: "home" },
  { id: "practice", label: C.tabs.practice, href: "/practice", icon: "pencil" },
  { id: "progress", label: C.tabs.progress, href: "/progress", icon: "chart" },
  { id: "lessons", label: C.tabs.lessons, href: "/lessons", icon: "book" },
] as const;

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex min-w-0 flex-col gap-3">
      <h2 className="m-0 text-sm font-semibold uppercase tracking-wide text-muted">{title}</h2>
      {children}
    </section>
  );
}

function Showcase({ theme }: { theme: "light" | "dark" }) {
  const [pick, setPick] = useState("b");
  const [conf, setConf] = useState<string | null>("think");
  const hintLabels = { ...C.hint, hintTitle: (n: number, t: number) => `Hint ${n} of ${t}` };
  return (
    <div
      data-theme={theme}
      data-testid={`learn-${theme}`}
      className="ui-root flex min-w-0 flex-1 flex-col gap-6 rounded-[var(--radius-card)] border border-line p-4"
      style={{ background: "var(--c-bg)" }}
    >
      <h1 className="m-0 text-xl font-semibold">{theme === "light" ? "Light" : "Dark"}</h1>

      <Section title="QuestionCard">
        <QuestionCard label="Question" eyebrow="Question 2" stem="Solve the equation." equation="x^2 + 5x + 6 = 0" equationLabel="x squared plus 5 x plus 6 equals 0" />
        <QuestionCard
          label="Question with figure"
          stem="What number is shown on the line?"
          figure={
            <svg width="220" height="40" viewBox="0 0 220 40" role="img" aria-label="A number line from 0 to 5">
              <line x1="10" y1="20" x2="210" y2="20" stroke="currentColor" strokeWidth="2" />
              <circle cx="130" cy="20" r="6" fill="var(--c-accent)" />
            </svg>
          }
        />
        <QuestionCard label={C.loading} stem="" loading />
      </Section>

      <Section title="AnswerOption: default, selected, correct, look-again, disabled, loading">
        <AnswerGroup label="Choose an answer">
          <AnswerOption name={`${theme}-a`} value="a" marker="A">x = 2 or x = 3</AnswerOption>
          <AnswerOption name={`${theme}-a`} value="b" marker="B" selected={pick === "b"} onSelect={setPick}>
            x = -2 or x = -3
          </AnswerOption>
          <AnswerOption name={`${theme}-a`} value="c" marker="C" state="correct" stateLabel={C.correct}>x = -2 or x = -3</AnswerOption>
          <AnswerOption name={`${theme}-a`} value="d" marker="D" state="look-again" stateLabel={C.lookAgain}>x = 6 or x = 1</AnswerOption>
          <AnswerOption name={`${theme}-a`} value="e" marker="E" disabled>Not available</AnswerOption>
          <AnswerOption name={`${theme}-a`} value="f" marker="F" loading>Loading</AnswerOption>
        </AnswerGroup>
      </Section>

      <Section title="ConfidenceRow: selected, none, disabled">
        <ConfidenceRow legend={C.confidenceLegend} options={CONF} value={conf} onChange={setConf} />
        <ConfidenceRow legend={C.confidenceLegend} options={CONF} value={null} />
        <ConfidenceRow legend={C.confidenceLegend} options={CONF} value="sure" disabled />
      </Section>

      <Section title="IDontKnowButton: default, disabled, loading">
        <IDontKnowButton label={C.idk} />
        <IDontKnowButton label={C.idk} disabled />
        <IDontKnowButton label={C.idk} loading />
      </Section>

      <Section title="TrustChip">
        <div className="flex flex-wrap gap-2">
          <TrustChip variant="checked-by-code" verified />
          <TrustChip variant="hints-from-verified-steps" verified />
          <TrustChip variant="not-verified" verified={false} />
        </div>
      </Section>

      <Section title="HintLadder">
        <HintLadder hints={["Look at the numbers that multiply to 6.", "Which pair also adds to 5?"]} labels={hintLabels} steps={<span>(x + 2)(x + 3) = 0, so x = -2 or x = -3.</span>} />
        <HintLadder hints={["One"]} labels={hintLabels} disabled />
        <HintLadder hints={["One"]} labels={hintLabels} loading />
      </Section>

      <Section title="FeedbackCard">
        <FeedbackCard variant="look-again" title={C.lookAgainTitle}>Check the sign of the middle term, then try again.</FeedbackCard>
        <FeedbackCard variant="correct" title={C.correctTitle}>Both factors multiply to 6 and add to 5.</FeedbackCard>
      </Section>

      <Section title="TopicChip and ProgressBar">
        <div className="flex flex-wrap gap-2">
          <TopicChip>Quadratics</TopicChip>
          <TopicChip onClick={() => {}} selected>Factorising</TopicChip>
          <TopicChip onClick={() => {}}>Roots</TopicChip>
          <TopicChip onClick={() => {}} disabled>Locked</TopicChip>
        </div>
        <ProgressBar current={2} total={5} label="Question 2 of 5" />
      </Section>

      <Section title="SkeletonCard and EmptyState">
        <SkeletonCard label={C.loading} />
        <EmptyState title="Nothing to practise yet">Pick a topic and your questions will appear here.</EmptyState>
      </Section>

      <Section title="ContinueCard: default, disabled, loading">
        <ContinueCard eyebrow="Pick up where you left off" title="Quadratic equations" progress={{ current: 3, total: 8, label: "Step 3 of 8" }} actionLabel={C.resume} href="/lessons/quad" />
        <ContinueCard title="Quadratic equations" actionLabel={C.resume} disabled />
        <ContinueCard title="" actionLabel={C.resume} loading loadingLabel={C.loading} />
      </Section>

      <Section title="BottomTabBar (in flow here; fixed in the app)">
        <BottomTabBar items={TABS} currentPath="/practice/3" label={C.navLabel} position="static" className="rounded-xl border" />
      </Section>
    </div>
  );
}

/** Dev only (NEXT_PUBLIC_DEV_TOOLS): every learn component and state, light and dark side by side. */
export default function LearnComponentsPreview() {
  if (!devToolsEnabled()) notFound();
  return (
    <main className="mx-auto flex max-w-[1400px] flex-col gap-4 p-3 lg:flex-row" data-testid="learn-preview">
      <Showcase theme="light" />
      <Showcase theme="dark" />
    </main>
  );
}
