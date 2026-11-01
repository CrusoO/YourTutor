"use client";

import { Icon } from "@/components/ui/icons";
import { useCopy } from "@/lib/locale";
import type { StudentHomeSnapshot } from "@/lib/chat/home-cache";
import styles from "./ChatHome.module.css";

type Props = {
  student: StudentHomeSnapshot;
  reviewEnabled: boolean;
  onContinue: () => void;
  onReview: () => void;
  onToday: () => void;
};

export function RightPanel({ student, reviewEnabled, onContinue, onReview, onToday }: Props) {
  const copy = useCopy();
  const progress = student.current?.chapter;
  const percent = progress && progress.skills_total > 0
    ? Math.round((progress.skills_can_do_it / progress.skills_total) * 100)
    : null;

  return (
    <aside className={`flex w-full min-w-0 flex-col ${styles.rightPanel} ${styles.panel}`} aria-label={copy.homePanelLabel} data-testid="right-panel">
      <section className={`border p-[18px] ${styles.panelCard} ${styles.continueCard}`}>
        <p className="m-0 text-[0.6875rem] text-muted">{copy.homeContinueLabel}</p>
        {percent !== null ? (
          <>
            <p className="home-stat m-0 mt-2 flex items-start font-extralight leading-none tracking-[-0.045em] text-accent-ink" style={{ fontSize: "2.9rem", fontWeight: 200 }}>
              {percent}
              <span className="ml-[0.08em] mt-[0.4em] text-[0.4em] font-light tracking-normal">%</span>
            </p>
            <div
              className="relative mt-3 h-[2px] w-full rounded-full bg-[color-mix(in_srgb,var(--c-text)_14%,transparent)]"
              role="progressbar"
              aria-label={progress?.title}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={percent}
            >
              <div className="absolute inset-y-0 left-0 rounded-full bg-accent" style={{ width: `${percent}%` }} />
            </div>
          </>
        ) : null}
        <p className="m-0 mt-2.5 text-[0.8125rem] font-medium text-ink">
          {progress?.title ?? copy.chatContinue}
        </p>
        {student.current?.skill ? (
          <p className="m-0 mt-1 text-[0.6875rem] text-muted">{student.current.skill}</p>
        ) : null}
        <button
          type="button"
          onClick={onContinue}
          className={`mt-4 inline-flex min-h-9 cursor-pointer items-center gap-1.5 border-0 bg-accent px-3.5 text-[0.75rem] font-medium text-accent-fg transition-opacity hover:opacity-90 ${styles.continueButton}`}
          data-testid="panel-continue"
        >
          {student.resume ? copy.homeResume : copy.chatContinue}
          <Icon name="arrowUp" size={12} className="rotate-90" />
        </button>
      </section>

      <section className={`border p-[18px] ${styles.panelCard}`} aria-label={copy.homeToday}>
        <h2 className="m-0 text-[0.8125rem] font-medium text-ink">{copy.homeToday}</h2>
        <button
          type="button"
          onClick={onReview}
          disabled={student.due === 0 || !reviewEnabled}
          className={`mt-3 flex min-h-11 w-full cursor-pointer items-center justify-between gap-2 border-0 border-b border-line bg-transparent px-0 py-2 text-left text-[0.75rem] text-ink disabled:cursor-default disabled:text-muted ${styles.panelReview}`}
          data-testid="panel-review"
        >
          <span>{copy.chatReviewDue}</span>
          <span>{student.due > 0 ? copy.chatReviewDueN.replace("{n}", String(student.due)) : copy.chatNothingDue}</span>
        </button>
        {student.minutesLeft !== null ? (
          <p className="m-0 border-b border-line py-2 text-[0.75rem] text-muted">
            {copy.chatMinutesLeft.replace("{n}", String(student.minutesLeft))}
          </p>
        ) : null}
        <button
          type="button"
          onClick={onToday}
          className={`mt-2 inline-flex min-h-9 cursor-pointer items-center gap-1.5 border border-input-line bg-transparent px-3.5 text-[0.75rem] font-medium text-ink hover:bg-surface-2 ${styles.panelToday}`}
          data-testid="panel-today"
        >
          {copy.chatTodayPlan}
          <Icon name="arrowUp" size={12} className="rotate-90" />
        </button>
      </section>
    </aside>
  );
}
