import type { SessionCopy } from "@/lib/session/copy";
import { fmt } from "@/lib/session/integer-stem";

/** The tick range: 0 is always inside, the start is inside, one tick of padding each side. */
export function lineWindow(start: number, delta: number): { min: number; max: number } {
  // Symmetric around the start, so the window itself never tells which way the dot goes or where it stops.
  const reach = Math.abs(delta);
  return {
    min: Math.min(0, start, start - reach) - 1,
    max: Math.max(0, start, start + reach) + 1,
  };
}

const W = 360;
const PAD = 22;
const LABEL_GAP = 30; // least distance in px between two tick labels

/** Which tick values get a label: 0 and the start always, others on a round step so labels never touch. */
export function labelledTicks(min: number, max: number, required: number[], onlyRequired = false): number[] {
  const spacing = (W - 2 * PAD) / (max - min);
  const need = Math.ceil(LABEL_GAP / spacing);
  const every = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000].find((n) => n >= need) ?? need;
  const px = (v: number) => PAD + (v - min) * spacing;
  const out = new Set<number>(required);
  if (onlyRequired) return [...out].sort((a, b) => a - b);
  for (let v = min; v <= max; v++) {
    if (v % every !== 0) continue;
    if (required.some((r) => Math.abs(px(r) - px(v)) < LABEL_GAP)) continue;
    out.add(v);
  }
  return [...out].sort((a, b) => a - b);
}

function fill(template: string, values: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (_, k: string) => String(values[k] ?? ""));
}

/** What a screen reader hears, and what the caption shows. Leaves the landing out when it is not shown. */
export function lineDescription(
  copy: Pick<SessionCopy, "signLineName" | "signLineStart" | "signLineMove" | "signLineLand" | "signDirLeft" | "signDirRight" | "signUnitOne" | "signUnitMany">,
  start: number,
  delta: number,
  showLanding: boolean,
): string {
  const { min, max } = lineWindow(start, delta);
  const n = Math.abs(delta);
  const parts = [
    fill(copy.signLineName, { min: fmt(min), max: fmt(max) }),
    fill(copy.signLineStart, { start: fmt(start) }),
  ];
  if (delta !== 0) {
    parts.push(
      fill(copy.signLineMove, {
        n,
        unit: n === 1 ? copy.signUnitOne : copy.signUnitMany,
        dir: delta > 0 ? copy.signDirRight : copy.signDirLeft,
      }),
    );
  }
  if (showLanding) parts.push(fill(copy.signLineLand, { result: fmt(start + delta) }));
  return parts.join(" ");
}

type Props = {
  copy: SessionCopy;
  start: number;
  /** Signed move: positive is right. */
  delta: number;
  /** False for the hint: the start and the arrow are drawn, the landing number and dot are not. */
  showLanding: boolean;
};

/**
 * A small static number line: ticks only as wide as needed, 0 always visible, the start dot, an arrow for the move and,
 * when allowed, the landing dot. No animation. It has an accessible name and the same words as visible text.
 */
export default function MiniNumberLine({ copy, start, delta, showLanding }: Props) {
  const { min, max } = lineWindow(start, delta);
  const end = start + delta;
  const spacing = (W - 2 * PAD) / (max - min);
  const x = (v: number) => PAD + (v - min) * spacing;
  const required = showLanding ? [0, start, end] : [0, start];
  // In the hint only 0 and the start are named, so the student counts the ticks and no label sits where the arrow stops.
  const labels = new Set(labelledTicks(min, max, required, !showLanding));
  const ticks: number[] = [];
  for (let v = min; v <= max; v++) ticks.push(v);
  const lineY = 70;
  const arrowY = 38;
  const description = lineDescription(copy, start, delta, showLanding);
  const head = delta === 0 ? null : delta > 0 ? 1 : -1;
  return (
    <figure className="mnl" data-testid="mini-number-line" data-landing={showLanding ? "shown" : "hidden"}>
      <svg
        viewBox={`0 0 ${W} 138`}
        role="img"
        aria-label={description}
        focusable="false"
        className="mnl-svg"
      >
        <line className="mnl-axis" x1={PAD - 8} x2={W - PAD + 8} y1={lineY} y2={lineY} />
        {ticks.map((v) => (
          <g key={v}>
            <line
              className={v === 0 ? "mnl-tick mnl-zero" : "mnl-tick"}
              x1={x(v)}
              x2={x(v)}
              y1={lineY - (v === 0 ? 9 : 6)}
              y2={lineY + (v === 0 ? 9 : 6)}
            />
            {labels.has(v) ? (
              <text className={v === 0 ? "mnl-label mnl-label-zero" : "mnl-label"} x={x(v)} y={lineY + 28} textAnchor="middle">
                {fmt(v)}
              </text>
            ) : null}
          </g>
        ))}
        {head !== null ? (
          <g className="mnl-move">
            <line x1={x(start)} x2={x(end) - head * 7} y1={arrowY} y2={arrowY} />
            <polygon
              points={`${x(end)},${arrowY} ${x(end) - head * 10},${arrowY - 6} ${x(end) - head * 10},${arrowY + 6}`}
            />
            {showLanding ? <line className="mnl-drop" x1={x(end)} x2={x(end)} y1={arrowY + 6} y2={lineY - 10} /> : null}
          </g>
        ) : null}
        <line className="mnl-drop" x1={x(start)} x2={x(start)} y1={arrowY - 4} y2={lineY - 10} />
        <circle className="mnl-start" cx={x(start)} cy={lineY} r={8} />
        {showLanding ? <circle className="mnl-land" cx={x(end)} cy={lineY} r={8} /> : null}
        <text className="mnl-tag" x={x(start)} y={lineY + 46} textAnchor="middle">
          {copy.signStart}
        </text>
        {showLanding && end !== start ? (
          <text className="mnl-tag mnl-tag-land" x={x(end)} y={lineY + (Math.abs(x(end) - x(start)) < 84 ? 60 : 46)} textAnchor="middle">
            {copy.signLandLabel}
          </text>
        ) : null}
      </svg>
      <figcaption className="mnl-caption" aria-hidden="true">{description}</figcaption>
    </figure>
  );
}
