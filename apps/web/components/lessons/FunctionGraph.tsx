"use client";

import { useEffect, useRef, useState, type PointerEvent } from "react";
import { pick, type FunctionGraphWidget } from "@/lib/lessons/types";
import { goalMet, graphValue, snapGraphX } from "@/lib/lessons/widgets";

type Props = {
  widget: FunctionGraphWidget;
  locale: string;
  onSolved?: (state: { x: number }, actionsCount: number) => void;
};

const W = 320;
const H = 240;
const GL = 38;
const GR = 308;
const GT = 12;
const GB = 212;

/** 1, 2 or 5 times a power of ten, at least `raw`. */
export function niceStep(raw: number): number {
  const exp = Math.pow(10, Math.floor(Math.log10(raw)));
  const f = raw / exp;
  return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * exp;
}
const fmt = (n: number) => String(Math.round(n * 10) / 10);

export default function FunctionGraph({ widget, locale, onSolved }: Props) {
  const g = widget.params;
  const step = g.step ?? 0.1;
  const startX = snapGraphX(g, g.x_min + (g.x_max - g.x_min) / 8, false);
  const [x, setX] = useState(startX);
  const [actions, setActions] = useState(0);
  const dragging = useRef(false);
  const svg = useRef<SVGSVGElement | null>(null);
  const solved = goalMet(widget, { x });
  const wasSolved = useRef(false);
  const cb = useRef(onSolved);
  cb.current = onSolved;

  useEffect(() => {
    if (solved && !wasSolved.current) cb.current?.({ x }, actions);
    wasSolved.current = solved;
  }, [solved, x, actions]);

  const yAtMin = graphValue(g, g.x_min);
  const yAtMax = graphValue(g, g.x_max);
  const yLow = Math.min(0, yAtMin, yAtMax, g.target_y);
  const yHigh = Math.max(yAtMin, yAtMax, g.target_y);
  const yStep = niceStep((yHigh - yLow) / 5);
  const yTop = Math.ceil(yHigh / yStep) * yStep;
  const yBottom = Math.floor(yLow / yStep) * yStep;
  const xStep = niceStep((g.x_max - g.x_min) / 8);
  const sx = (v: number) => GL + ((v - g.x_min) * (GR - GL)) / (g.x_max - g.x_min);
  const sy = (v: number) => GB - ((v - yBottom) * (GB - GT)) / (yTop - yBottom);
  const y = graphValue(g, x);
  const xName = g.x_label ? pick(g.x_label, locale) : "x";
  const targetName = g.target_label ? pick(g.target_label, locale) : `target = ${g.target_y}`;

  function setFromRaw(raw: number) {
    const next = snapGraphX(g, raw);
    setX((prev) => {
      if (prev !== next) setActions((n) => n + 1);
      return next;
    });
  }
  function fromPointer(e: PointerEvent<SVGSVGElement>) {
    const el = svg.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / (rect.width || W)) * W;
    setFromRaw(g.x_min + ((px - GL) / (GR - GL)) * (g.x_max - g.x_min));
  }

  const gridX: number[] = [];
  for (let v = Math.ceil(g.x_min / xStep) * xStep; v <= g.x_max + 1e-9; v += xStep) gridX.push(Math.round(v * 1e6) / 1e6);
  const gridY: number[] = [];
  for (let v = yBottom; v <= yTop + 1e-9; v += yStep) gridY.push(Math.round(v * 1e6) / 1e6);

  const slopeUp = g.slope > 0;
  const hint =
    y < g.target_y
      ? slopeUp
        ? "The line is lower than the target. Slide to the right."
        : "The line is lower than the target. Slide to the left."
      : slopeUp
        ? "The line is higher than the target. Slide to the left."
        : "The line is higher than the target. Slide to the right.";

  return (
    <div className="lp-widget">
      <p className="lp-lead">{pick(widget.prompt, locale)}</p>
      <div className="lp-panel">
        <svg
          ref={svg}
          viewBox={`0 0 ${W} ${H}`}
          className="lp-svg lp-graph"
          role="img"
          aria-label={`Graph of ${g.label ?? "the line"} with a target line at ${g.target_y}`}
          onPointerDown={(e) => {
            dragging.current = true;
            svg.current?.setPointerCapture?.(e.pointerId);
            fromPointer(e);
          }}
          onPointerMove={(e) => dragging.current && fromPointer(e)}
          onPointerUp={() => (dragging.current = false)}
          onPointerCancel={() => (dragging.current = false)}
        >
          {gridX.map((v) => (
            <g key={`x${v}`}>
              <line x1={sx(v)} y1={GT} x2={sx(v)} y2={GB} className="lp-g" />
              <text x={sx(v)} y={GB + 16} className="lp-gl">
                {fmt(v)}
              </text>
            </g>
          ))}
          {gridY.map((v) => (
            <g key={`y${v}`}>
              <line x1={GL} y1={sy(v)} x2={GR} y2={sy(v)} className="lp-g" />
              <text x={GL - 8} y={sy(v) + 4} className="lp-gl end">
                {fmt(v)}
              </text>
            </g>
          ))}
          <text x={GR} y={GB + 30} className="lp-gl end">
            {xName}
          </text>
          <line x1={GL} y1={sy(g.target_y)} x2={GR} y2={sy(g.target_y)} className="lp-target" />
          <text x={GR} y={sy(g.target_y) - 5} className="lp-tl">
            {targetName}
          </text>
          <line x1={sx(g.x_min)} y1={sy(yAtMin)} x2={sx(g.x_max)} y2={sy(yAtMax)} className="lp-ln" />
          {g.label ? (
            <text x={sx(g.x_min + (g.x_max - g.x_min) * 0.42)} y={sy(graphValue(g, g.x_min + (g.x_max - g.x_min) * 0.42)) - 12} className="lp-ll">
              {g.label}
            </text>
          ) : null}
          <line x1={sx(x)} y1={sy(y)} x2={sx(x)} y2={GB} className="lp-drop" />
          <circle cx={sx(x)} cy={sy(y)} r={11} className={`lp-pt${solved ? " hit" : ""}`} />
        </svg>
      </div>
      <label className="lp-sublabel" htmlFor="lp-graph-x">
        {xName}
      </label>
      <input
        id="lp-graph-x"
        className="lp-range"
        type="range"
        min={g.x_min}
        max={g.x_max}
        step={step}
        value={x}
        aria-valuetext={`${xName} ${fmt(x)}, the line is at ${fmt(y)}`}
        onChange={(e) => setFromRaw(Number(e.target.value))}
      />
      <p className="lp-read">
        {xName} = {fmt(x)}, the line is at {fmt(y)}
      </p>
      <p className={`lp-fb ${solved ? "good" : "tip"}`} aria-live="polite">
        {solved ? pick(widget.success, locale) : hint}
      </p>
    </div>
  );
}
