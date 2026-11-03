"use client";

import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { controlDefaults, type AiSeries, type RunnableWidget } from "@/lib/lessons/ai-lesson";
import { linspace, type Formula } from "@/lib/lessons/formula";
import { useCopy } from "@/lib/locale";
import { BlockTitle, Note } from "./blocks";
import { StepPicture } from "./StepPicture";

type SliderRun = Extract<RunnableWidget, { formula: Formula }>;
type GraphRun = Extract<RunnableWidget, { series: unknown[] }>;
type PlainRun = Exclude<RunnableWidget, SliderRun | GraphRun>;

/** A readable number: plain for everyday sizes, scientific for the very large and very small. */
export function fmt(n: number): string {
  if (!Number.isFinite(n)) return "–";
  if (n === 0) return "0";
  const abs = Math.abs(n);
  if (abs >= 1e5 || abs < 1e-3) return n.toExponential(2);
  return String(Number(n.toPrecision(4)));
}

const SERIES_COLOR: Record<AiSeries["color"], string> = {
  blue: "#3b82f6",
  red: "#ef4444",
  green: "#22c55e",
  orange: "#f59e0b",
  purple: "#a855f7",
};

const RANGE = "h-2 w-full cursor-pointer accent-[var(--c-accent)]";

/** The curve of a formula over a range, as SVG points in a 0..W by 0..H box, plus the y-range used. */
function curve(fn: (x: number) => number, lo: number, hi: number, w: number, h: number, pad: number, yRange?: [number, number]) {
  const xs = linspace(lo, hi, 80);
  const ys = xs.map(fn);
  const yMin = yRange ? yRange[0] : Math.min(...ys);
  let yMax = yRange ? yRange[1] : Math.max(...ys);
  if (yMax === yMin) yMax = yMin + 1;
  const px = (x: number) => pad + ((x - lo) / (hi - lo)) * (w - 2 * pad);
  const py = (y: number) => h - pad - ((y - yMin) / (yMax - yMin)) * (h - 2 * pad);
  return { points: xs.map((x, i) => `${px(x).toFixed(1)},${py(ys[i]!).toFixed(1)}`).join(" "), px, py, yMin, yMax };
}

function SliderSim({ run }: { run: SliderRun }) {
  const { widget, formula } = run;
  const { spec, controls } = widget;
  const [value, setValue] = useState(spec.min);
  const [extra, setExtra] = useState<Record<string, number>>(() => controlDefaults(controls));
  const out = formula({ ...extra, [spec.variable]: value });
  const shape = useMemo(() => curve((x) => formula({ ...extra, [spec.variable]: x }), spec.min, spec.max, 200, 80, 8), [formula, extra, spec]);

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-line bg-surface p-4" data-testid="widget-slider">
      <label className="flex flex-col gap-1.5 text-[0.875rem] text-ink">
        <span className="flex justify-between gap-3">
          <span>{spec.variable.replace(/_/g, " ")}</span>
          <span className="tabular-nums text-muted">
            {fmt(value)} {spec.unit}
          </span>
        </span>
        <input
          type="range"
          className={RANGE}
          min={spec.min}
          max={spec.max}
          step={spec.step}
          value={value}
          aria-valuetext={`${fmt(value)} ${spec.unit}`}
          onChange={(e) => setValue(Number(e.target.value))}
        />
      </label>
      {controls.map((c) => (
        <label key={c.var} className="flex flex-col gap-1.5 text-[0.875rem] text-ink">
          <span className="flex justify-between gap-3">
            <span>{c.label}</span>
            <span className="tabular-nums text-muted">{fmt(extra[c.var] ?? c.min)}</span>
          </span>
          <input
            type="range"
            className={RANGE}
            min={c.min}
            max={c.max}
            step={c.step}
            value={extra[c.var] ?? c.min}
            onChange={(e) => setExtra((prev) => ({ ...prev, [c.var]: Number(e.target.value) }))}
          />
        </label>
      ))}
      <div className="flex items-end justify-between gap-4">
        <div className="flex flex-col gap-0.5">
          <span className="text-[0.75rem] text-muted">{spec.output_label}</span>
          <span className="text-[1.5rem] font-light tabular-nums text-ink" data-testid="widget-output" aria-live="polite">
            {fmt(out)} <span className="text-[0.875rem] text-muted">{spec.output_unit}</span>
          </span>
        </div>
        <svg viewBox="0 0 200 80" className="h-20 w-48 shrink-0" role="img" aria-label={spec.output_label}>
          <polyline points={shape.points} fill="none" stroke="var(--c-accent)" strokeWidth="2" strokeLinejoin="round" />
          <circle cx={shape.px(value)} cy={shape.py(out)} r="4.5" fill="var(--c-accent)" />
        </svg>
      </div>
    </div>
  );
}

function GraphExplore({ run }: { run: GraphRun }) {
  const copy = useCopy();
  const { spec } = run.widget as Extract<typeof run.widget, { widget_kind: "graph_explore" }>;
  const [x, setX] = useState(spec.x_min);
  const W = 320;
  const H = 170;
  const PAD = 26;
  const all = useMemo(() => run.series.flatMap((s) => linspace(spec.x_min, spec.x_max, 80).map((v) => s.formula({ x: v }))), [run, spec]);
  const range: [number, number] = [Math.min(...all), Math.max(...all) === Math.min(...all) ? Math.min(...all) + 1 : Math.max(...all)];
  const px = (v: number) => PAD + ((v - spec.x_min) / (spec.x_max - spec.x_min)) * (W - 2 * PAD);
  const py = (v: number) => H - PAD - ((v - range[0]) / (range[1] - range[0])) * (H - 2 * PAD);

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-line bg-surface p-4" data-testid="widget-graph">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={`${spec.y_label} against ${spec.x_label}`}>
        <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="var(--c-line)" strokeWidth="1.5" />
        <line x1={PAD} y1={PAD} x2={PAD} y2={H - PAD} stroke="var(--c-line)" strokeWidth="1.5" />
        <text x={PAD} y={H - 8} fontSize="9" fill="var(--c-muted)">
          {fmt(spec.x_min)}
        </text>
        <text x={W - PAD} y={H - 8} fontSize="9" fill="var(--c-muted)" textAnchor="end">
          {fmt(spec.x_max)} {spec.x_unit}
        </text>
        <text x={W / 2} y={H - 8} fontSize="9" fill="var(--c-muted)" textAnchor="middle">
          {spec.x_label}
        </text>
        <text x={PAD - 4} y={PAD + 3} fontSize="9" fill="var(--c-muted)" textAnchor="end">
          {fmt(range[1])}
        </text>
        <text x={PAD - 4} y={H - PAD} fontSize="9" fill="var(--c-muted)" textAnchor="end">
          {fmt(range[0])}
        </text>
        {run.series.map((entry, i) => {
          const { series, formula } = entry;
          const points = linspace(spec.x_min, spec.x_max, 80)
            .map((v) => `${px(v).toFixed(1)},${py(formula({ x: v })).toFixed(1)}`)
            .join(" ");
          return (
            <g key={i}>
              <polyline points={points} fill="none" stroke={SERIES_COLOR[series.color]} strokeWidth="2.2" strokeLinejoin="round" />
              <circle cx={px(x)} cy={py(formula({ x }))} r="4" fill={SERIES_COLOR[series.color]} />
            </g>
          );
        })}
        <line x1={px(x)} y1={PAD} x2={px(x)} y2={H - PAD} stroke="var(--c-line)" strokeDasharray="3 3" />
      </svg>
      <input
        type="range"
        className={RANGE}
        min={spec.x_min}
        max={spec.x_max}
        step={spec.x_step}
        value={x}
        aria-label={copy.lessonScrub}
        onChange={(e) => setX(Number(e.target.value))}
      />
      <ul className="m-0 flex list-none flex-wrap gap-x-5 gap-y-1 p-0 text-[0.8125rem] text-ink" aria-live="polite">
        <li className="tabular-nums text-muted">
          {spec.x_label} = {fmt(x)} {spec.x_unit}
        </li>
        {run.series.map((entry, i) => {
          const { series, formula } = entry;
          return (
            <li key={i} className="tabular-nums">
              <span aria-hidden="true" style={{ color: SERIES_COLOR[series.color] }}>
                ●{" "}
              </span>
              {series.name || spec.y_label} = {fmt(formula({ x }))} {spec.y_unit}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function StepThrough({ run }: { run: PlainRun }) {
  const copy = useCopy();
  const spec = (run.widget as Extract<typeof run.widget, { widget_kind: "step_through" }>).spec;
  const [i, setI] = useState(0);
  const step = spec.steps[i]!;
  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-line bg-surface p-4" data-testid="widget-steps">
      <div className="flex items-center gap-1.5" aria-hidden="true">
        {spec.steps.map((_, k) => (
          <span key={k} className={`h-1.5 flex-1 rounded-full ${k <= i ? "bg-accent" : "bg-surface-2"}`} />
        ))}
      </div>
      <div aria-live="polite" className="flex flex-col gap-1">
        <BlockTitle>
          {i + 1}. {step.label}
        </BlockTitle>
        <p className="m-0 text-[0.9375rem] leading-[1.6] text-ink">{step.description}</p>
      </div>
      <StepPicture picture={step.picture} />
      <div className="flex gap-2">
        <Button variant="outline" size="sm" disabled={i === 0} onClick={() => setI(i - 1)}>
          {copy.lessonPrev}
        </Button>
        <Button variant="outline" size="sm" disabled={i === spec.steps.length - 1} onClick={() => setI(i + 1)}>
          {copy.lessonNext}
        </Button>
      </div>
    </div>
  );
}

/** Start order: the items shifted along by one or two places, so it is never already the answer. */
function startOrder(correct: number[]): number[] {
  const n = correct.length;
  const base = Array.from({ length: n }, (_, k) => k);
  for (const shift of [1, 2]) {
    const order = base.map((_, k) => base[(k + shift) % n]!);
    if (order.some((v, p) => v !== correct[p])) return order;
  }
  return base.reverse();
}

function DragSort({ run }: { run: PlainRun }) {
  const copy = useCopy();
  const spec = (run.widget as Extract<typeof run.widget, { widget_kind: "drag_sort" }>).spec;
  const [order, setOrder] = useState(() => startOrder(spec.correct_order));
  const [verdict, setVerdict] = useState<"right" | "wrong" | null>(null);
  const move = (from: number, to: number) => {
    if (to < 0 || to >= order.length) return;
    const next = [...order];
    [next[from], next[to]] = [next[to]!, next[from]!];
    setOrder(next);
    setVerdict(null);
  };
  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-line bg-surface p-4" data-testid="widget-sort">
      <ol className="m-0 flex list-none flex-col gap-2 p-0">
        {order.map((item, p) => (
          <li key={item} className="flex items-center gap-2 rounded-xl border border-line bg-surface-2 px-3 py-2 text-[0.9375rem] text-ink">
            <span className="w-5 text-[0.75rem] tabular-nums text-muted" aria-hidden="true">
              {p + 1}
            </span>
            <span className="min-w-0 flex-1">{spec.items[item]}</span>
            <Button variant="ghost" size="icon" className="size-10 min-h-10 min-w-10" aria-label={`${copy.lessonMoveUp}: ${spec.items[item]}`} disabled={p === 0} onClick={() => move(p, p - 1)}>
              ↑
            </Button>
            <Button variant="ghost" size="icon" className="size-10 min-h-10 min-w-10" aria-label={`${copy.lessonMoveDown}: ${spec.items[item]}`} disabled={p === order.length - 1} onClick={() => move(p, p + 1)}>
              ↓
            </Button>
          </li>
        ))}
      </ol>
      <div>
        <Button variant="outline" size="sm" onClick={() => setVerdict(order.every((v, p) => v === spec.correct_order[p]) ? "right" : "wrong")}>
          {copy.lessonCheckOrder}
        </Button>
      </div>
      {verdict ? <Note tone={verdict === "right" ? "good" : "miss"}>{verdict === "right" ? copy.lessonOrderRight : copy.lessonOrderWrong}</Note> : null}
    </div>
  );
}

function ToggleCompare({ run }: { run: PlainRun }) {
  const spec = (run.widget as Extract<typeof run.widget, { widget_kind: "toggle_compare" }>).spec;
  const [side, setSide] = useState<"a" | "b">("a");
  const text = side === "a" ? spec.description_a : spec.description_b;
  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-line bg-surface p-4" data-testid="widget-toggle">
      <div className="grid grid-cols-2 gap-2" role="group">
        {(["a", "b"] as const).map((s) => (
          <button
            key={s}
            type="button"
            aria-pressed={side === s}
            onClick={() => setSide(s)}
            className={`min-h-12 cursor-pointer rounded-xl border px-3 py-2 text-[0.9375rem] ${side === s ? "border-accent bg-accent-soft text-ink" : "border-line bg-surface text-muted hover:text-ink"}`}
          >
            {s === "a" ? spec.label_a : spec.label_b}
          </button>
        ))}
      </div>
      <p className="m-0 text-[0.9375rem] leading-[1.6] text-ink" aria-live="polite">
        {text}
      </p>
    </div>
  );
}

/** One widget plus the sentence that says what to look for in it. */
export function WidgetBlock({ run }: { run: RunnableWidget }) {
  const copy = useCopy();
  const kind = run.widget.widget_kind;
  return (
    <section className="flex flex-col gap-3" data-testid="block-widget">
      {"formula" in run ? <SliderSim run={run} /> : "series" in run ? <GraphExplore run={run} /> : kind === "step_through" ? <StepThrough run={run} /> : kind === "drag_sort" ? <DragSort run={run} /> : <ToggleCompare run={run} />}
      {run.widget.what_to_notice ? (
        <p className="m-0 text-[0.875rem] leading-[1.6] text-muted">
          <span className="font-medium text-ink">{copy.lessonNotice}: </span>
          {run.widget.what_to_notice}
        </p>
      ) : null}
    </section>
  );
}
