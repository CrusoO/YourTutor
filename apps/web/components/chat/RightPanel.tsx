"use client";

import { useState } from "react";
import { Icon } from "@/components/ui/icons";
import { cn } from "@/lib/cn";
import { useCopy } from "@/lib/locale";

// Placeholder data: wire these to a real progress and schedule API when one exists.
const CONTINUE_PCT = 72;

const INITIAL_TASKS: { id: number; key: "homeTask1" | "homeTask2" | "homeTask3"; done: boolean }[] = [
  { id: 1, key: "homeTask1", done: true },
  { id: 2, key: "homeTask2", done: false },
  { id: 3, key: "homeTask3", done: false },
];

type Day = { state: "done" | "today" | "todo" };
const STREAK: Day[] = [
  { state: "done" },
  { state: "done" },
  { state: "done" },
  { state: "done" },
  { state: "done" },
  { state: "today" },
  { state: "todo" },
];

export function RightPanel() {
  const copy = useCopy();
  const days = copy.homeDays.split(",");
  const [tasks, setTasks] = useState(INITIAL_TASKS);
  const doneCount = tasks.filter((t) => t.done).length;
  const toggle = (id: number) => setTasks((prev) => prev.map((t) => (t.id === id ? { ...t, done: !t.done } : t)));

  return (
    <aside className="hidden w-60 shrink-0 flex-col gap-6 xl:flex" aria-label={copy.homePanelLabel} data-testid="right-panel">
      <section className="rounded-2xl border border-accent bg-surface p-[18px] shadow-[0_0_0_1px_color-mix(in_srgb,var(--c-accent)_12%,transparent),0_10px_30px_color-mix(in_srgb,var(--c-accent)_10%,transparent)]">
        <p className="m-0 text-[0.6875rem] text-muted">{copy.homeContinueLabel}</p>
        <p className="home-stat m-0 mt-2 flex items-start font-extralight leading-none tracking-[-0.045em] text-accent-ink" style={{ fontSize: "2.9rem", fontWeight: 200 }}>
          {CONTINUE_PCT}
          <span className="ml-[0.08em] mt-[0.4em] text-[0.4em] font-light tracking-normal">%</span>
        </p>
        <p className="m-0 mt-2.5 text-[0.8125rem] font-medium text-ink">{copy.homeContinueTopic}</p>
        <p className="m-0 mt-1 text-[0.6875rem] text-muted">{copy.homeContinueNext}</p>
        <div
          className="relative mt-3 h-[2px] w-full rounded-full bg-[color-mix(in_srgb,var(--c-text)_14%,transparent)]"
          role="progressbar"
          aria-label={copy.homeContinueTopic}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={CONTINUE_PCT}
        >
          <div className="absolute inset-y-0 left-0 rounded-full bg-accent shadow-[0_0_8px_var(--c-accent)]" style={{ width: `${CONTINUE_PCT}%` }} />
        </div>
        <button
          type="button"
          className="mt-4 inline-flex min-h-8 cursor-pointer items-center gap-1.5 rounded-full border-0 bg-accent px-3.5 text-[0.75rem] font-medium text-accent-fg transition-opacity hover:opacity-90"
        >
          {copy.homeResume}
          <Icon name="arrowUp" size={12} className="rotate-90" />
        </button>
      </section>

      <section aria-label={copy.homeToday}>
        <div className="mb-1.5 flex items-baseline justify-between">
          <h3 className="m-0 text-[0.8125rem] font-medium text-ink">{copy.homeToday}</h3>
          <span className="text-[0.6875rem] text-muted">
            {copy.homeDoneOf.replace("{done}", String(doneCount)).replace("{total}", String(tasks.length))}
          </span>
        </div>
        <ul className="m-0 flex list-none flex-col p-0">
          {tasks.map((task) => (
            <li key={task.id} className="border-0 border-b border-line last:border-b-0">
              <button
                type="button"
                onClick={() => toggle(task.id)}
                aria-pressed={task.done}
                className="flex w-full cursor-pointer items-center gap-2.5 border-0 bg-transparent px-0 py-[9px] text-left"
              >
                <span
                  className={cn(
                    "grid size-4 shrink-0 place-items-center rounded-full border",
                    task.done ? "border-accent bg-accent text-accent-fg" : "border-input-line text-transparent",
                  )}
                  aria-hidden="true"
                >
                  <Icon name="check" size={9} />
                </span>
                <span className={cn("text-[0.75rem] leading-snug", task.done ? "text-muted line-through" : "text-ink")}>{copy[task.key]}</span>
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section aria-label={copy.homeStreak}>
        <div className="mb-3 flex items-baseline justify-between">
          <h3 className="m-0 text-[0.8125rem] font-medium text-ink">{copy.homeStreak}</h3>
          <span className="text-[0.6875rem] text-accent-ink">{copy.homeKeepGoing}</span>
        </div>
        <ol className="m-0 flex list-none items-start justify-between p-0">
          {STREAK.map((d, i) => (
            <li key={i} className="flex flex-col items-center gap-1.5">
              <span
                aria-hidden="true"
                className={cn(
                  "size-6 rounded-full",
                  d.state === "done" && "bg-ink",
                  d.state === "today" && "border border-dashed border-accent",
                  d.state === "todo" && "bg-surface-2",
                )}
              />
              <span className="text-[0.5625rem] text-muted">{days[i]}</span>
            </li>
          ))}
        </ol>
      </section>
    </aside>
  );
}
