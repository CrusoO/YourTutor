"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { storyCaptions, type SettingId, type StoryBeatId } from "./landing-extras";
import styles from "./LandingExtras.module.css";

/** True once the element has scrolled into view; always true where there is no observer or motion is reduced. */
export function useSeen<T extends Element>(): [React.RefObject<T | null>, boolean, boolean] {
  const ref = useRef<T | null>(null);
  const [seen, setSeen] = useState(false);
  // Armed means the scroll watcher is running: only then may a picture start hidden. Without it (no script,
  // no observer, reduced motion) everything is simply shown, so nothing important depends on an animation.
  const [armed, setArmed] = useState(false);
  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches || !("IntersectionObserver" in window)) {
      setSeen(true);
      return;
    }
    setArmed(true);
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setSeen(true);
          observer.disconnect();
        }
      },
      { threshold: 0.35 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  return [ref, seen, armed];
}

type Pose = "stand" | "think" | "raise" | "point";

/** A stick figure standing with its feet at (x, y). `s` scales the 60-unit-tall figure. */
function Figure({ x, y, s = 1, pose = "stand", accent = false, label }: { x: number; y: number; s?: number; pose?: Pose; accent?: boolean; label?: string }) {
  const shoulder = y - 40 * s;
  const arms: Record<Pose, ReactNode> = {
    stand: (
      <>
        <line x1={x} y1={shoulder} x2={x - 10 * s} y2={y - 24 * s} />
        <line x1={x} y1={shoulder} x2={x + 10 * s} y2={y - 24 * s} />
      </>
    ),
    think: (
      <>
        <line x1={x} y1={shoulder} x2={x - 10 * s} y2={y - 24 * s} />
        <polyline points={`${x},${shoulder} ${x + 9 * s},${y - 32 * s} ${x + 3 * s},${y - 45 * s}`} />
      </>
    ),
    raise: (
      <>
        <line x1={x} y1={shoulder} x2={x - 10 * s} y2={y - 24 * s} />
        <line x1={x} y1={shoulder} x2={x + 11 * s} y2={y - 58 * s} />
      </>
    ),
    point: (
      <>
        <line x1={x} y1={shoulder} x2={x - 10 * s} y2={y - 24 * s} />
        <line x1={x} y1={shoulder} x2={x + 24 * s} y2={y - 38 * s} />
      </>
    ),
  };
  return (
    <g className={accent ? styles.accentStroke : styles.inkStroke} strokeWidth={2.2 * s} fill="none" strokeLinecap="round" strokeLinejoin="round">
      <circle cx={x} cy={y - 52 * s} r={7 * s} className={accent ? styles.accentFill : undefined} />
      <line x1={x} y1={y - 45 * s} x2={x} y2={y - 22 * s} />
      <line x1={x} y1={y - 22 * s} x2={x - 8 * s} y2={y} />
      <line x1={x} y1={y - 22 * s} x2={x + 8 * s} y2={y} />
      {arms[pose]}
      {label ? (
        <text x={x} y={y + 14 * s} textAnchor="middle" className={styles.artLabel} stroke="none">
          {label}
        </text>
      ) : null}
    </g>
  );
}

function Prop({ setting }: { setting: SettingId }) {
  if (setting === "class") {
    return (
      <g>
        <rect x="80" y="8" width="160" height="30" rx="2" className={styles.propBox} />
        <line x1="92" y1="18" x2="190" y2="18" className={styles.dimStroke} />
        <line x1="92" y1="28" x2="150" y2="28" className={styles.dimStroke} />
      </g>
    );
  }
  return (
    <g>
      <rect x="90" y="8" width="140" height="30" rx="3" className={styles.propBox} />
      <rect x="104" y="22" width="12" height="10" className={styles.dimFill} />
      <rect x="122" y="16" width="12" height="16" className={styles.dimFill} />
      <rect x="140" y="12" width="12" height="20" className={styles.dimFill} />
    </g>
  );
}

function Nod({ setting }: { setting: SettingId }) {
  if (setting === "alone") {
    return (
      <>
        <rect x="90" y="30" width="140" height="80" rx="4" className={styles.propBox} />
        <text x="160" y="76" textAnchor="middle" className={styles.artText}>
          Got it?
        </text>
        <g className={styles.nodder}>
          <Figure x={160} y={186} s={1.25} pose="stand" accent label="Robin" />
        </g>
      </>
    );
  }
  const robin = setting === "class" ? 11 : 17; // a seat at the right-hand edge, so the label has clear space
  return (
    <>
      <Prop setting={setting} />
      {Array.from({ length: 30 }, (_, i) => {
        const cx = 76 + (i % 6) * 34;
        const cy = 62 + Math.floor(i / 6) * 25;
        const isRobin = i === robin;
        return (
          <circle
            key={i}
            cx={cx}
            cy={cy}
            r={isRobin ? 7 : 6}
            className={isRobin ? styles.accentFill : styles.crowdDot}
            style={isRobin ? undefined : { animationDelay: `${(i % 7) * 90}ms` }}
            data-nod={isRobin ? undefined : "true"}
          />
        );
      })}
      <circle cx={76 + (robin % 6) * 34} cy={62 + Math.floor(robin / 6) * 25} r={11} className={styles.robinRing} />
      <text x={76 + (robin % 6) * 34 + 18} y={62 + Math.floor(robin / 6) * 25 + 4} className={styles.artLabelAccent}>
        Robin
      </text>
    </>
  );
}

function Silence() {
  return (
    <>
      {Array.from({ length: 12 }, (_, i) => (
        <circle key={i} cx={176 + (i % 6) * 22} cy={150 + Math.floor(i / 6) * 22} r={4.5} className={styles.crowdDot} />
      ))}
      <Figure x={90} y={178} s={1.5} pose="stand" accent label="Robin" />
      <g className={styles.questionMarks}>
        {[0, 1, 2].map((i) => (
          <text key={i} x={140 + i * 30} y={72 - (i % 2) * 8} className={styles.questionMark} style={{ animationDelay: `${i * 220}ms` }}>
            ?
          </text>
        ))}
      </g>
      <line x1="76" y1="127" x2="104" y2="127" className={styles.accentStroke} strokeWidth="2.5" strokeLinecap="round" />
      <text x="190" y="118" className={styles.artNote}>
        questions kept inside
      </text>
    </>
  );
}

const STEP_W = 44;

/** Five steps rising to the right; step `missing` (0-based) is the one Robin missed. */
function Steps({ filled = false }: { filled?: boolean }) {
  return (
    <>
      {[0, 1, 2, 3, 4].map((i) => {
        const x = 40 + i * STEP_W;
        const h = 28 + i * 22;
        const missing = i === 2;
        return (
          <rect
            key={i}
            x={x}
            y={184 - h}
            width={STEP_W - 4}
            height={h}
            className={missing ? (filled ? styles.stepFound : styles.stepMissing) : i > 2 ? styles.stepLater : styles.step}
            style={{ animationDelay: `${i * 140}ms` }}
          />
        );
      })}
    </>
  );
}

function Missed() {
  return (
    <>
      <Steps />
      <Figure x={26} y={184} s={0.9} pose="stand" accent />
      <text x={40 + 2 * STEP_W + 18} y={184 - 28 - 2 * 22 - 8} textAnchor="middle" className={styles.artLabelAccent}>
        missed
      </text>
      <line x1={40 + 3 * STEP_W + 18} y1={60} x2={40 + 4 * STEP_W + 18} y2={60} className={styles.dimStroke} strokeDasharray="3 3" />
      <text x={40 + 3.5 * STEP_W + 18} y={52} textAnchor="middle" className={styles.artNote}>
        rests on it
      </text>
    </>
  );
}

function Belief() {
  return (
    <>
      <Figure x={80} y={172} s={1.5} pose="think" accent label="Robin" />
      <g>
        <ellipse cx="200" cy="64" rx="104" ry="40" className={styles.propBox} />
        <circle cx="130" cy="116" r="6" className={styles.propBox} />
        <circle cx="118" cy="134" r="3.5" className={styles.propBox} />
        <text x="200" y="60" textAnchor="middle" className={styles.artText}>
          Maybe I’m just not
        </text>
        <text x="200" y="78" textAnchor="middle" className={styles.artText}>
          good at this.
        </text>
      </g>
      <text x="200" y="160" textAnchor="middle" className={styles.artNote}>
        What happened: one step missed.
      </text>
    </>
  );
}

function Asked({ setting }: { setting: SettingId }) {
  return (
    <>
      <Steps filled />
      <Figure x={26} y={184} s={0.9} pose="raise" accent />
      {setting === "alone" ? (
        <g>
          <rect x="236" y="18" width="70" height="46" rx="4" className={styles.propBox} />
          <text x="271" y="46" textAnchor="middle" className={styles.artNote}>
            ?
          </text>
        </g>
      ) : (
        <Figure x={286} y={110} s={0.9} pose="point" />
      )}
      <g>
        <rect x="150" y="14" width="146" height="30" rx="8" className={styles.propBox} />
        <text x="223" y="33" textAnchor="middle" className={styles.artText}>
          Which part is confusing?
        </text>
      </g>
    </>
  );
}

/** The picture for one beat of Robin's story, drawn for the chosen setting, with its caption underneath. */
export function StoryArt({ beat, setting }: { beat: StoryBeatId; setting: SettingId }) {
  const [ref, seen, armed] = useSeen<HTMLElement>();
  const caption = storyCaptions[setting][beat];
  return (
    <figure ref={ref} className={styles.storyFigure} data-seen={seen} data-armed={armed} data-testid={`story-art-${beat}`}>
      <svg viewBox="0 0 320 200" className={styles.storySvg} role="img" aria-label={caption}>
        {beat === "nod" ? <Nod setting={setting} /> : null}
        {beat === "silence" ? <Silence /> : null}
        {beat === "missed" ? <Missed /> : null}
        {beat === "belief" ? <Belief /> : null}
        {beat === "asked" ? <Asked setting={setting} /> : null}
      </svg>
      <figcaption className={styles.storyCaption}>{caption}</figcaption>
    </figure>
  );
}
