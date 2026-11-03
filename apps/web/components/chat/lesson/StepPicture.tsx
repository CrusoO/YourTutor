import type { ReactNode } from "react";
import type { AiPicture, BalancePart } from "@/lib/lessons/ai-lesson";

/**
 * The everyday picture for one step: a level balance, a cut whole, equal groups or a number line.
 * Drawn from numbers only, so nothing the model wrote can become markup. A picture that does not make
 * sense draws nothing, and the step reads as words as before.
 */

const W = 320;
const H = 140;
const ACCENT = "var(--c-accent)";
const SOFT = "var(--c-surface-2)";
const MUTED = "var(--c-muted)";

const whole = (n: unknown, low: number, high: number): n is number => typeof n === "number" && Number.isInteger(n) && n >= low && n <= high;

function names(parts: BalancePart[]): string {
  return parts.map((p) => (p.unknown ? p.what || "something unknown" : `${p.n - p.out} ${p.what}`.trim())).join(" and ");
}

/** The words for a screen reader, so the drawing is never the only way to get the step. */
export function describePicture(picture: AiPicture): string {
  switch (picture.kind) {
    case "balance":
      return `A balance that stays level. On the left: ${names(picture.left)}. On the right: ${names(picture.right)}.`;
    case "pieces":
      return `A ${picture.what || "whole"} cut into ${picture.parts} equal pieces, ${picture.shaded} shaded.`;
    case "groups":
      return `${picture.groups} groups of ${picture.each} ${picture.what || "things"}.`;
    case "line": {
      const jump = picture.jump ? ` A jump from ${picture.jump.from} to ${picture.jump.to}.` : "";
      return `A number line from ${picture.min} to ${picture.max}.${jump}`;
    }
  }
}

function Dots({ count, out, x, y, perRow }: { count: number; out: number; x: number; y: number; perRow: number }) {
  return (
    <>
      {Array.from({ length: count }, (_, i) => {
        const cx = x + (i % perRow) * 16;
        const cy = y - Math.floor(i / perRow) * 16;
        const gone = i >= count - out;
        return (
          <g key={i}>
            <circle cx={cx} cy={cy} r={6} fill={gone ? "none" : ACCENT} stroke={ACCENT} strokeWidth={1.5} opacity={gone ? 0.45 : 1} />
            {gone ? <path d={`M${cx - 5} ${cy - 5} L${cx + 5} ${cy + 5} M${cx + 5} ${cy - 5} L${cx - 5} ${cy + 5}`} stroke={MUTED} strokeWidth={1.5} /> : null}
          </g>
        );
      })}
    </>
  );
}

function Side({ parts, centre }: { parts: BalancePart[]; centre: number }) {
  // lay the parts left to right along the pan, each one starting after the last, five items to a row
  const items: ReactNode[] = [];
  let x = centre - 48;
  parts.forEach((p, k) => {
    if (p.unknown) {
      items.push(
        <g key={k}>
          <rect x={x} y={56} width={26} height={26} rx={5} fill={SOFT} stroke="currentColor" strokeWidth={1.5} />
          <text x={x + 13} y={74} textAnchor="middle" fontSize={15} fontWeight={600} fill="currentColor">
            {(p.what || "?").slice(0, 2)}
          </text>
        </g>,
      );
      x += 32;
    } else {
      const perRow = Math.min(5, Math.max(1, p.n));
      items.push(<Dots key={k} count={p.n} out={p.out} x={x + 6} y={76} perRow={perRow} />);
      x += perRow * 16 + 8;
    }
  });
  return <>{items}</>;
}

function Balance({ left, right }: { left: BalancePart[]; right: BalancePart[] }) {
  return (
    <>
      <path d="M160 112 L148 132 L172 132 Z" fill={MUTED} />
      <line x1={160} y1={24} x2={160} y2={112} stroke={MUTED} strokeWidth={3} />
      <line x1={28} y1={24} x2={292} y2={24} stroke={MUTED} strokeWidth={3} strokeLinecap="round" />
      {[80, 240].map((cx) => (
        <g key={cx}>
          <path d={`M${cx - 52} 24 V86 M${cx + 52} 24 V86`} stroke={MUTED} strokeWidth={1.2} />
          <path d={`M${cx - 54} 86 H${cx + 54} Q${cx + 48} 100 ${cx} 100 Q${cx - 48} 100 ${cx - 54} 86 Z`} fill={SOFT} stroke={MUTED} strokeWidth={1.5} />
        </g>
      ))}
      <Side parts={left} centre={80} />
      <Side parts={right} centre={240} />
    </>
  );
}

function Pieces({ parts, shaded }: { parts: number; shaded: number }) {
  const cx = 160;
  const cy = 68;
  const r = 52;
  const point = (turn: number) => `${cx + r * Math.sin(turn * 2 * Math.PI)} ${cy - r * Math.cos(turn * 2 * Math.PI)}`;
  return (
    <>
      {Array.from({ length: parts }, (_, i) => (
        <path
          key={i}
          d={`M${cx} ${cy} L${point(i / parts)} A${r} ${r} 0 ${1 / parts > 0.5 ? 1 : 0} 1 ${point((i + 1) / parts)} Z`}
          fill={i < shaded ? ACCENT : SOFT}
          stroke="currentColor"
          strokeWidth={1.5}
          strokeLinejoin="round"
        />
      ))}
      <text x={cx} y={134} textAnchor="middle" fontSize={13} fill="currentColor">
        {shaded} of {parts}
      </text>
    </>
  );
}

function Groups({ groups, each }: { groups: number; each: number }) {
  const gap = (W - 20) / groups;
  const perRow = Math.min(4, each);
  return (
    <>
      {Array.from({ length: groups }, (_, g) => {
        const left = 10 + g * gap + gap / 2;
        return (
          <g key={g}>
            <rect x={left - Math.min(gap / 2 - 4, 40)} y={22} width={Math.min(gap - 8, 80)} height={86} rx={12} fill={SOFT} stroke={MUTED} strokeWidth={1.5} />
            {Array.from({ length: each }, (_, i) => (
              <circle key={i} cx={left - ((perRow - 1) * 14) / 2 + (i % perRow) * 14} cy={44 + Math.floor(i / perRow) * 16} r={5.5} fill={ACCENT} />
            ))}
          </g>
        );
      })}
      <text x={W / 2} y={130} textAnchor="middle" fontSize={13} fill="currentColor">
        {groups} × {each} = {groups * each}
      </text>
    </>
  );
}

function Line({ picture }: { picture: Extract<AiPicture, { kind: "line" }> }) {
  const { min, max } = picture;
  const x = (v: number) => 24 + ((v - min) / (max - min)) * (W - 48);
  const span = max - min;
  const step = span <= 12 ? 1 : Math.ceil(span / 10);
  const ticks: number[] = [];
  for (let v = Math.ceil(min); v <= max; v += step) ticks.push(v);
  return (
    <>
      <line x1={24} y1={86} x2={W - 24} y2={86} stroke={MUTED} strokeWidth={2} strokeLinecap="round" />
      {ticks.map((v) => (
        <g key={v}>
          <line x1={x(v)} y1={80} x2={x(v)} y2={92} stroke={MUTED} strokeWidth={1.5} />
          <text x={x(v)} y={108} textAnchor="middle" fontSize={11} fill={MUTED}>
            {v}
          </text>
        </g>
      ))}
      {picture.marks.map((m) => (
        <g key={m.at}>
          <circle cx={x(m.at)} cy={86} r={6} fill={ACCENT} />
          <text x={x(m.at)} y={126} textAnchor="middle" fontSize={11} fontWeight={600} fill="currentColor">
            {m.label}
          </text>
        </g>
      ))}
      {picture.jump ? (
        <path
          d={`M${x(picture.jump.from)} 78 Q${(x(picture.jump.from) + x(picture.jump.to)) / 2} 22 ${x(picture.jump.to)} 78`}
          fill="none"
          stroke={ACCENT}
          strokeWidth={2.5}
          strokeLinecap="round"
          markerEnd="url(#step-arrow)"
        />
      ) : null}
    </>
  );
}

/** True when the picture's numbers are ones this file can draw (the server already checked, the page does not trust it). */
export function drawable(picture: AiPicture | null | undefined): picture is AiPicture {
  if (!picture) return false;
  switch (picture.kind) {
    case "balance": {
      const ok = (side: BalancePart[]) => Array.isArray(side) && side.length >= 1 && side.length <= 3 && side.every((p) => whole(p.n, 0, 12) && whole(p.out, 0, p.n));
      return ok(picture.left) && ok(picture.right);
    }
    case "pieces":
      return whole(picture.parts, 2, 12) && whole(picture.shaded, 0, picture.parts);
    case "groups":
      return whole(picture.groups, 1, 6) && whole(picture.each, 1, 8);
    case "line":
      return Number.isFinite(picture.min) && Number.isFinite(picture.max) && picture.max > picture.min && Array.isArray(picture.marks);
    default:
      return false;
  }
}

export function StepPicture({ picture }: { picture: AiPicture | null | undefined }) {
  if (!drawable(picture)) return null;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={describePicture(picture)} className="h-auto w-full max-w-[22rem] self-center text-ink" data-testid="step-picture" data-kind={picture.kind}>
      <defs>
        <marker id="step-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0 0 L10 5 L0 10 Z" fill={ACCENT} />
        </marker>
      </defs>
      {picture.kind === "balance" ? <Balance left={picture.left} right={picture.right} /> : null}
      {picture.kind === "pieces" ? <Pieces parts={picture.parts} shaded={picture.shaded} /> : null}
      {picture.kind === "groups" ? <Groups groups={picture.groups} each={picture.each} /> : null}
      {picture.kind === "line" ? <Line picture={picture} /> : null}
    </svg>
  );
}
