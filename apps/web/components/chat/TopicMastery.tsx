"use client";

import { useId } from "react";
import { useCopy } from "@/lib/locale";
import styles from "./ChatHome.module.css";

/** Chart height in px: taller for higher mastery, so the stats stagger down the row. */
const chartHeight = (pct: number) => Math.round(18 + 1.09 * pct);

function Chart({ pct }: { pct: number }) {
  const gid = useId();
  const h = chartHeight(pct);
  const tone = "var(--c-accent)";
  return (
    <div className="relative" style={{ height: h + 30 }} aria-hidden="true">
      <span className="absolute left-0 top-0 size-[5px] -translate-x-1/2 rounded-full" style={{ background: tone }} />
      <svg className="absolute bottom-0 left-0 block w-full overflow-visible" style={{ height: h }} viewBox="0 0 100 100" preserveAspectRatio="none">
        <defs>
          <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={tone} stopOpacity={0.42} />
            <stop offset="100%" stopColor={tone} stopOpacity={0.03} />
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

type TopicProgress = { id: string; title: string; percent: number };

export function TopicMastery({ topics }: { topics: TopicProgress[] }) {
  const copy = useCopy();
  return (
    <section className={`w-full border px-[22px] pb-0 pt-[18px] ${styles.masteryCard}`} aria-label={copy.homeMastery} data-testid="topic-mastery">
      <div className="mb-4 flex items-baseline justify-between">
        <h2 className="m-0 text-[0.8125rem] font-medium text-ink">{copy.homeMastery}</h2>
        <span className="text-[0.6875rem] text-muted">{copy.chatTopics}</span>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-5 overflow-hidden sm:grid-cols-4">
        {topics.slice(0, 4).map((topic) => (
          <div key={topic.id} className="flex min-w-0 flex-col justify-end">
            <div
              className="home-stat flex items-start font-extralight leading-none tracking-[-0.045em] text-accent-ink"
              style={{ fontFamily: "var(--ff-body)", fontSize: "clamp(1.75rem, 4.2vw, 2.7rem)", fontWeight: 200 }}
            >
              {topic.percent}
              <span className="ml-[0.08em] mt-[0.42em] text-[0.4em] font-light tracking-normal">%</span>
            </div>
            <div className={`mb-3 mt-1.5 truncate leading-snug text-muted ${styles.topicLabel}`} title={topic.title}>{topic.title}</div>
            <Chart pct={topic.percent} />
          </div>
        ))}
      </div>
    </section>
  );
}
