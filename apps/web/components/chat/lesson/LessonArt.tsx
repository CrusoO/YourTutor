/**
 * The small pictures beside a prepared lesson's steps. Each one shows the same thing the step says (two trains and a finish flag, a
 * speedometer that cannot go below zero), drawn with the same few objects the whole way through so the student can follow one
 * story from the first step to the last. Plain SVG, no network, each with a spoken label for a screen reader.
 */
import type { ReactNode } from "react";

export type LessonArtKey = "runwalk" | "twotrains" | "timebars" | "distance" | "equation" | "speedometer" | "clock" | "bus" | "recap";

const INK = "#3b4651";
const BLUE = "#bfe6f1";
const BLUE_D = "#8fd0e4";
const ORANGE = "#f2b27a";
const YELLOW = "#f6e58d";
const GREEN = "#bfe3c6";
const RED = "#e5565f";
const GROUND = "#c9ccd6";

function Rails({ x, y, w }: { x: number; y: number; w: number }) {
  const ties = Math.floor(w / 4);
  return (
    <g>
      <path d={`M ${x},${y + 4} L ${x + 2},${y + 1.6} L ${x + w - 2},${y + 1.6} L ${x + w},${y + 4} Z`} fill={GROUND} stroke={INK} strokeWidth={0.25} />
      {Array.from({ length: ties }, (_, i) => (
        <rect key={i} x={x + 1 + i * 4} y={y + 1} width={1.6} height={1.4} fill={ORANGE} stroke={INK} strokeWidth={0.15} />
      ))}
      <rect x={x} y={y} width={w} height={0.8} fill={INK} opacity={0.85} />
    </g>
  );
}

/** A small train, wheels sitting on y: an engine with a pantograph and two coaches with windows. Its width is 62 at scale 1. */
function Train({ x, y, scale = 1, tint = BLUE }: { x: number; y: number; scale?: number; tint?: string }) {
  const coach = (cx: number) => (
    <g key={cx}>
      <rect x={cx} y={-11} width={19} height={9} rx={1.2} fill={tint} stroke={INK} strokeWidth={0.4} />
      <rect x={cx} y={-6.4} width={19} height={0.9} fill={ORANGE} />
      {[0, 1, 2, 3].map((i) => (
        <rect key={i} x={cx + 1.6 + i * 4.1} y={-9.6} width={2.8} height={2.6} rx={0.4} fill={YELLOW} stroke={INK} strokeWidth={0.2} />
      ))}
      {[3, 14].map((wx) => (
        <g key={wx}>
          <circle cx={cx + wx} cy={-0.9} r={1.3} fill={INK} />
          <circle cx={cx + wx + 3} cy={-0.9} r={1.3} fill={INK} />
        </g>
      ))}
    </g>
  );
  return (
    <g transform={`translate(${x} ${y}) scale(${scale})`}>
      {coach(0)}
      {coach(21)}
      <path d="M 42,-2 L 42,-9.4 C 42,-10.4 42.6,-10.8 43.4,-10.8 L 55,-10.8 C 59,-10.8 61.4,-6.4 62,-2 Z" fill={tint} stroke={INK} strokeWidth={0.4} />
      <rect x={42.2} y={-6.4} width={19} height={0.9} fill={ORANGE} />
      <path d="M 54,-10 L 56,-10 C 57.4,-9 58.4,-7.6 58.8,-6.6 L 54,-6.6 Z" fill="#ffffff" stroke={INK} strokeWidth={0.2} />
      <rect x={47} y={-9.6} width={5} height={2.6} rx={0.4} fill={YELLOW} stroke={INK} strokeWidth={0.2} />
      <path d="M 46,-10.8 L 49,-14 L 52,-10.8 M 47.4,-14 L 50.6,-14" fill="none" stroke={INK} strokeWidth={0.35} />
      <circle cx={61.2} cy={-4} r={0.7} fill={YELLOW} stroke={INK} strokeWidth={0.15} />
      {[44, 54].map((wx) => (
        <g key={wx}>
          <circle cx={wx} cy={-0.9} r={1.3} fill={INK} />
          <circle cx={wx + 3} cy={-0.9} r={1.3} fill={INK} />
        </g>
      ))}
    </g>
  );
}

const T = ({ x, y, children, size = 5.5, anchor = "middle", weight = 400 }: { x: number; y: number; children: ReactNode; size?: number; anchor?: "start" | "middle" | "end"; weight?: number }) => (
  <text x={x} y={y} fontSize={size} textAnchor={anchor} fill={INK} fontWeight={weight} fontFamily="Inter, system-ui, sans-serif">
    {children}
  </text>
);

const LABELS: Record<LessonArtKey, string> = {
  runwalk: "A short bar for running and a long bar for walking: going faster takes less time.",
  twotrains: "Two trains on the same road. The faster one reaches the finish flag first.",
  timebars: "Two bars: 9 hours at 40 kilometres an hour, 8 hours at 45. The difference is 1 hour.",
  distance: "A road of 360 kilometres with a train. Time is the distance divided by the speed.",
  equation: "Two trains on the same road: one at speed x, one at x plus 5. Their times differ by one hour.",
  speedometer: "A speedometer showing 40. It has nothing below zero, so a speed cannot be minus 45.",
  clock: "A train at 45 kilometres an hour and a clock showing 8 hours.",
  bus: "A bus on a road of 240 kilometres, going 20 kilometres an hour faster.",
  recap: "Three things to remember: time is distance over speed, the equation, and keep only the speed that makes sense.",
};

function Scene({ kind }: { kind: LessonArtKey }) {
  switch (kind) {
    case "runwalk":
      return (
        <>
          <T x={4} y={10} anchor="start">walk</T>
          <rect x={4} y={13} width={90} height={7} rx={3.5} fill={BLUE} stroke={INK} strokeWidth={0.4} />
          <T x={4} y={34} anchor="start">run</T>
          <rect x={4} y={37} width={45} height={7} rx={3.5} fill={GREEN} stroke={INK} strokeWidth={0.4} />
          <circle cx={52} cy={40.5} r={3.2} fill={ORANGE} stroke={INK} strokeWidth={0.35} />
          <path d="M 49.8,40 L 50.2,40 M 53.6,40 L 54,40" stroke={INK} strokeWidth={0.5} />
          <path d="M 50.4,42 Q 52,43.4 53.6,42" fill="none" stroke={INK} strokeWidth={0.4} />
          <T x={50} y={62} weight={600}>faster = sooner</T>
        </>
      );
    case "twotrains":
      return (
        <>
          <T x={4} y={10} anchor="start" size={5}>A · 40 km/h</T>
          <Train x={4} y={26} scale={0.8} />
          <Rails x={2} y={26} w={90} />
          <T x={4} y={40} anchor="start" size={5}>B · 45 km/h</T>
          <Train x={24} y={56} scale={0.8} tint={BLUE_D} />
          <Rails x={2} y={56} w={90} />
          <path d="M 94,6 L 94,62" stroke={INK} strokeWidth={0.6} />
          <path d="M 94,6 L 100,8.4 L 94,11 Z" fill={RED} />
        </>
      );
    case "timebars":
      return (
        <>
          <T x={4} y={10} anchor="start">40 km/h</T>
          <rect x={4} y={13} width={86} height={8} rx={2.5} fill={BLUE} stroke={INK} strokeWidth={0.4} />
          <T x={47} y={19} size={5}>9 hours</T>
          <T x={4} y={34} anchor="start">45 km/h</T>
          <rect x={4} y={37} width={76} height={8} rx={2.5} fill={GREEN} stroke={INK} strokeWidth={0.4} />
          <rect x={80} y={37} width={10} height={8} rx={2} fill={ORANGE} stroke={INK} strokeWidth={0.4} />
          <T x={42} y={43} size={5}>8 hours</T>
          <T x={85} y={58} weight={600}>1 hour saved</T>
        </>
      );
    case "distance":
      return (
        <>
          <T x={50} y={9} weight={600}>360 km</T>
          <path d="M 6,13 L 94,13 M 6,10.6 L 6,15.4 M 94,10.6 L 94,15.4" stroke={INK} strokeWidth={0.5} fill="none" />
          <Train x={20} y={40} scale={0.9} />
          <Rails x={4} y={40} w={92} />
          <T x={50} y={60} size={5.5}>time = distance ÷ speed</T>
        </>
      );
    case "equation":
      return (
        <>
          <T x={4} y={10} anchor="start" size={5}>speed x</T>
          <Train x={4} y={24} scale={0.8} />
          <Rails x={2} y={24} w={90} />
          <T x={96} y={21} anchor="end" size={5}>360 ÷ x</T>
          <T x={4} y={38} anchor="start" size={5}>speed x + 5</T>
          <Train x={4} y={52} scale={0.8} tint={BLUE_D} />
          <Rails x={2} y={52} w={90} />
          <T x={96} y={49} anchor="end" size={5}>360 ÷ (x+5)</T>
          <T x={50} y={66} weight={600} size={5.5}>difference = 1 hour</T>
        </>
      );
    case "speedometer":
      return (
        <>
          <path d="M 14,52 A 36,36 0 0 1 86,52" fill="#ffffff" stroke={INK} strokeWidth={0.8} />
          {Array.from({ length: 9 }, (_, i) => {
            const a = Math.PI - (i * Math.PI) / 8;
            return <line key={i} x1={50 + 31 * Math.cos(a)} y1={52 - 31 * Math.sin(a)} x2={50 + 35 * Math.cos(a)} y2={52 - 35 * Math.sin(a)} stroke={INK} strokeWidth={0.6} />;
          })}
          <T x={13} y={60} size={4.5}>0</T>
          <T x={87} y={60} size={4.5}>100</T>
          <line x1={50} y1={52} x2={50 + 28 * Math.cos(Math.PI - 0.4 * Math.PI)} y2={52 - 28 * Math.sin(Math.PI - 0.4 * Math.PI)} stroke={RED} strokeWidth={1.1} strokeLinecap="round" />
          <circle cx={50} cy={52} r={2.2} fill={INK} />
          <T x={50} y={44} size={6} weight={600}>40</T>
          <T x={50} y={12} size={5}>km/h</T>
          <text x={88} y={14} fontSize={6} fontWeight={700} fill={RED} textAnchor="middle" fontFamily="Inter, system-ui, sans-serif">−45 ✕</text>
        </>
      );
    case "clock":
      return (
        <>
          <circle cx={26} cy={26} r={18} fill="#ffffff" stroke={INK} strokeWidth={0.8} />
          {Array.from({ length: 12 }, (_, i) => {
            const a = (i * Math.PI) / 6;
            return <line key={i} x1={26 + 15 * Math.sin(a)} y1={26 - 15 * Math.cos(a)} x2={26 + 17 * Math.sin(a)} y2={26 - 17 * Math.cos(a)} stroke={INK} strokeWidth={0.5} />;
          })}
          <line x1={26} y1={26} x2={26 + 11 * Math.sin((8 * Math.PI) / 6)} y2={26 - 11 * Math.cos((8 * Math.PI) / 6)} stroke={INK} strokeWidth={1.1} strokeLinecap="round" />
          <line x1={26} y1={26} x2={26} y2={13} stroke={INK} strokeWidth={0.7} strokeLinecap="round" />
          <T x={74} y={20} size={9} weight={600}>8 h</T>
          <T x={74} y={30} size={5}>at 45 km/h</T>
          <Train x={20} y={58} scale={0.8} tint={BLUE_D} />
          <Rails x={4} y={58} w={92} />
        </>
      );
    case "bus":
      return (
        <>
          <T x={50} y={9} weight={600}>240 km</T>
          <path d="M 6,13 L 94,13 M 6,10.6 L 6,15.4 M 94,10.6 L 94,15.4" stroke={INK} strokeWidth={0.5} fill="none" />
          <rect x={20} y={28} width={46} height={18} rx={3} fill={ORANGE} stroke={INK} strokeWidth={0.5} opacity={0.9} />
          {[0, 1, 2, 3, 4].map((i) => (
            <rect key={i} x={23 + i * 8} y={31} width={6} height={6} rx={1} fill={YELLOW} stroke={INK} strokeWidth={0.3} />
          ))}
          <rect x={22} y={41} width={42} height={1.4} fill={RED} opacity={0.8} />
          <circle cx={32} cy={47} r={3.6} fill={INK} />
          <circle cx={54} cy={47} r={3.6} fill={INK} />
          <circle cx={32} cy={47} r={1.2} fill="#ffffff" />
          <circle cx={54} cy={47} r={1.2} fill="#ffffff" />
          <rect x={4} y={50.4} width={92} height={1.6} fill={GROUND} stroke={INK} strokeWidth={0.25} />
          <T x={50} y={64} size={5.5}>+ 20 km/h → 1 hour less</T>
        </>
      );
    case "recap":
      return (
        <>
          {[
            { x: 18, label: "÷", note: "time" },
            { x: 50, label: "x²", note: "equation" },
            { x: 82, label: "✓", note: "40" },
          ].map((c) => (
            <g key={c.label}>
              <circle cx={c.x} cy={26} r={12} fill={c.label === "✓" ? GREEN : BLUE} stroke={INK} strokeWidth={0.5} />
              <T x={c.x} y={30} size={11} weight={600}>{c.label}</T>
              <T x={c.x} y={48} size={5}>{c.note}</T>
            </g>
          ))}
          <path d="M 31,26 L 36,26 M 63,26 L 68,26" stroke={INK} strokeWidth={0.6} />
        </>
      );
  }
}

export function LessonArt({ kind }: { kind: LessonArtKey }) {
  return (
    <svg viewBox="0 0 100 70" role="img" aria-label={LABELS[kind]} data-testid={`art-${kind}`} className="block h-auto w-full rounded-xl border border-line bg-surface">
      <Scene kind={kind} />
    </svg>
  );
}

export const LESSON_ART_KEYS = Object.keys(LABELS) as LessonArtKey[];
