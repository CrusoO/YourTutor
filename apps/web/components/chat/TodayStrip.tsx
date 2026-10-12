"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/icons";
import { locale } from "@/lib/api";
import { activeDays, weekDays, type Plan, type Share } from "@/lib/chat/today";
import { useChatApi } from "./ChatProvider";

const fill = (text: string, values: Record<string, string | number>) =>
  Object.entries(values).reduce((out, [key, value]) => out.replaceAll(`{${key}}`, String(value)), text);

/** A progress ring with its meaning in words beside it; the ring itself carries no information alone. */
function Ring({ percent, label }: { percent: number; label: string }) {
  const r = 26;
  const c = 2 * Math.PI * r;
  return (
    <svg width="68" height="68" viewBox="0 0 68 68" role="img" aria-label={label} className="shrink-0" data-testid="today-ring">
      <circle cx="34" cy="34" r={r} fill="none" stroke="var(--c-line)" strokeWidth="7" />
      <circle
        cx="34"
        cy="34"
        r={r}
        fill="none"
        stroke="var(--c-accent)"
        strokeWidth="7"
        strokeLinecap="round"
        strokeDasharray={`${(c * percent) / 100} ${c}`}
        transform="rotate(-90 34 34)"
        style={{ transition: "stroke-dasharray var(--dur) var(--ease)" }}
      />
      <text x="34" y="39" textAnchor="middle" fontSize="15" fontWeight="700" fill="var(--c-text)">
        {percent}%
      </text>
    </svg>
  );
}

/** Days active this week, from dates kept on this device. No streak count, no loss message, no rank. */
function Week() {
  const { copy } = useChatApi();
  const [days, setDays] = useState<boolean[] | null>(null);
  useEffect(() => setDays(activeDays()), []);
  if (!days) return <div className="h-14" aria-hidden="true" />;
  const names = weekDays(new Date()).map((d) => new Intl.DateTimeFormat(locale(), { weekday: "short" }).format(d));
  const count = days.filter(Boolean).length;
  return (
    <section aria-label={copy.chatWeekTitle} data-testid="week-row">
      <p className="m-0 mb-2 text-sm font-semibold text-muted">
        {copy.chatWeekTitle}: {fill(copy.chatWeekCount, { n: count })}
      </p>
      <ul className="m-0 flex list-none gap-2 p-0">
        {days.map((on, i) => (
          <li key={i} className="flex flex-1 flex-col items-center gap-1 text-xs text-muted">
            <span
              className={`grid size-8 place-items-center rounded-full border text-sm font-bold ${on ? "border-success bg-success-soft text-success" : "border-line bg-surface text-muted"}`}
            >
              {on ? <Icon name="check" size={16} /> : <span aria-hidden="true">·</span>}
            </span>
            <span>{names[i]}</span>
            <span className="sr-only">{on ? copy.chatWeekActive : copy.chatWeekQuiet}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** "Today": the ring, a plan of about 25 minutes, one Start button, and the weekly row. */
export function TodayStrip({ share, plan, onStart }: { share: Share; plan: Plan | null; onStart: () => void }) {
  const { copy } = useChatApi();
  const ringText = fill(copy.chatRingLabel, { percent: share.percent, done: share.done, total: share.total });
  return (
    <section
      aria-label={copy.chatTodayTitle}
      className="grid w-full max-w-4xl gap-5 rounded-[var(--radius-card)] border border-line bg-surface p-5 shadow-[var(--shadow-card)] @2xl:grid-cols-[1fr_auto]"
      data-testid="today-strip"
    >
      <div className="flex items-center gap-4">
        <Ring percent={share.percent} label={ringText} />
        <div className="min-w-0">
          <h2 className="m-0 text-lg font-semibold">{copy.chatTodayTitle}</h2>
          <p className="m-0 text-sm text-muted" data-testid="ring-text">
            {ringText}
          </p>
        </div>
      </div>
      <div className="flex flex-col gap-3 @2xl:items-end">
        {plan ? (
          <>
            <p className="m-0 text-sm font-semibold text-muted">{fill(copy.chatPlanTitle, { n: plan.minutes })}</p>
            <ul className="m-0 list-none p-0 text-base" data-testid="plan-items">
              {plan.items.map((item) => (
                <li key={item.kind}>
                  {item.kind === "review" ? fill(copy.chatPlanReview, { n: item.count }) : fill(copy.chatPlanLearn, { title: item.title })}
                </li>
              ))}
            </ul>
            <Button onClick={onStart} className="min-h-12" data-testid="today-start">
              <Icon name="play" />
              {copy.chatPlanStart}
            </Button>
          </>
        ) : (
          <p className="m-0 text-base" data-testid="plan-empty">
            {copy.chatPlanNothing}
          </p>
        )}
      </div>
      <div className="@2xl:col-span-2">
        <Week />
      </div>
    </section>
  );
}
