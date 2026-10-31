"use client";

import { useId } from "react";
import { cn } from "@/lib/cn";
import { useCopy } from "@/lib/locale";
import type { Messages } from "@/lib/messages";

// Placeholder mastery data: wire to a real progress API when one exists.
const TOPICS = [
  { key: "homeTopicLinear", pct: 88, hi: false },
  { key: "homeTopicQuadratic", pct: 72, hi: true },
  { key: "homeTopicZeroes", pct: 54, hi: false },
  { key: "homeTopicTrig", pct: 31, hi: false },
] as const satisfies readonly { key: keyof Messages; pct: number; hi: boolean }[];

/** Chart height in px: taller for higher mastery, so the stats stagger down the row. */
const chartHeight = (pct: number) => Math.round(18 + 1.09 * pct);

function Chart({ pct, hi }: { pct: number; hi: boolean }) {
  const gid = useId();
  const h = chartHeight(pct);
  const tone = hi ? "var(--c-accent)" : "var(--c-text)";
  return (
    <div className="relative" style={{ height: h + 30 }} aria-hidden="true">
      <span className="absolute left-0 top-0 size-[5px] -translate-x-1/2 rounded-full" style={{ background: tone }} />
      <svg className="absolute bottom-0 left-0 block w-full overflow-visible" style={{ height: h }} viewBox="0 0 100 100" preserveAspectRatio="none">
        <defs>
          <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={tone} stopOpacity={hi ? 0.5 : 0.34} />
            <stop offset="100%" stopColor={tone} stopOpacity={hi ? 0.04 : 0.02} />
          </linearGradient>
        </defs>
        <polygon points="0,0 66,0 100,21 100,100 0,100" fill={`url(#${gid})`} />
        <polyline points="0,0 66,0 100,21" fill="none" stroke={tone} strokeWidth="1.6" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
        <line x1="0" y1="0" x2="0" y2="100" stroke={tone} strokeOpacity="0.55" strokeWidth="1" strokeDasharray="2 3" vectorEffect="non-scaling-stroke" />
        <line x1="66" y1="0" x2="66" y2="100" stroke={tone} strokeOpacity="0.4" strokeWidth="1" strokeDasharray="2 3" vectorEffect="non-scaling-stroke" />
      </svg>
      <span className="absolute left-0 top-[5px] h-[25px] border-0 border-l border-dashed" style={{ borderColor: tone, opacity: 0.55 }} />
    </div>
  );
}

export function TopicMastery() {
  const copy = useCopy();
  return (
    <section className="w-full rounded-[18px] border border-line bg-surface px-[22px] pb-0 pt-[18px] shadow-[var(--shadow-card)]" aria-label={copy.homeMastery} data-testid="topic-mastery">
      <div className="mb-4 flex items-baseline justify-between">
        <h2 className="m-0 text-[0.8125rem] font-medium text-ink">{copy.homeMastery}</h2>
        <span className="text-[0.6875rem] text-muted">{copy.homeMasteryMeta}</span>
      </div>
      <div className="grid h-[15rem] grid-cols-4 gap-x-3 overflow-hidden sm:gap-x-4">
        {TOPICS.map((t) => (
          <div key={t.key} className="flex min-w-0 flex-col justify-end">
            <div
              className={cn("home-stat flex items-start font-extralight leading-none tracking-[-0.045em]", t.hi ? "text-accent-ink" : "text-ink")}
              style={{ fontFamily: "var(--ff-body)", fontSize: "clamp(1.75rem, 4.2vw, 2.7rem)", fontWeight: 200 }}
            >
              {t.pct}
              <span className="ml-[0.08em] mt-[0.42em] text-[0.4em] font-light tracking-normal">%</span>
            </div>
            <div className="mb-3 mt-1.5 text-[0.6875rem] leading-snug text-muted">{copy[t.key]}</div>
            <Chart pct={t.pct} hi={t.hi} />
          </div>
        ))}
      </div>
    </section>
  );
}
