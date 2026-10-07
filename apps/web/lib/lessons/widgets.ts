/** Widget goal predicates and drawing helpers. Mirrors apps/api/app/lessons/widgets.py. */
import type {
  BalanceScaleParams,
  BalanceScaleWidget,
  FunctionGraphParams,
  FunctionGraphWidget,
  WidgetSpec,
} from "./types";

export const GRAPH_TOLERANCE = 1e-6;

export type BalanceState = { lb: number; lw: number; rb: number; rw: number };
export type GraphState = { x: number };

const isInt = (v: unknown): v is number => typeof v === "number" && Number.isInteger(v);
const isNum = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);

export function balanceStart(p: BalanceScaleParams): BalanceState {
  return { lb: p.left_boxes, lw: p.left_weights, rb: p.right_boxes, rw: p.right_weights };
}

function parseBalance(state: unknown): BalanceState | null {
  if (typeof state !== "object" || state === null) return null;
  const s = state as Record<string, unknown>;
  const { lb, lw, rb, rw } = s;
  if (![lb, lw, rb, rw].every((v) => isInt(v) && v >= 0)) return null;
  return { lb: lb as number, lw: lw as number, rb: rb as number, rw: rw as number };
}

export function balanceMass(boxes: number, weights: number, boxWeight: number): number {
  return boxes * boxWeight + weights;
}

export function isBalanced(state: BalanceState, boxWeight: number): boolean {
  return balanceMass(state.lb, state.lw, boxWeight) === balanceMass(state.rb, state.rw, boxWeight);
}

function balanceGoal(w: BalanceScaleWidget, state: unknown): boolean {
  const s = parseBalance(state);
  if (!s) return false;
  const p = w.params;
  if (s.lb > p.left_boxes || s.lw > p.left_weights || s.rb > p.right_boxes || s.rw > p.right_weights) {
    return false;
  }
  return isBalanced(s, p.box_weight) && s.lb === 1 && s.lw === 0 && s.rb === 0 && s.rw === p.box_weight;
}

function graphGoal(w: FunctionGraphWidget, state: unknown): boolean {
  if (typeof state !== "object" || state === null) return false;
  const x = (state as Record<string, unknown>).x;
  if (!isNum(x)) return false;
  const g = w.params;
  const step = g.step ?? 0.1;
  if (x < g.x_min - GRAPH_TOLERANCE || x > g.x_max + GRAPH_TOLERANCE) return false;
  const k = Math.round((x - g.x_min) / step);
  if (Math.abs(g.x_min + k * step - x) > GRAPH_TOLERANCE) return false;
  return Math.abs(g.slope * x + g.intercept - g.target_y) <= GRAPH_TOLERANCE;
}

/** Same result as the server's check; used for instant UI feedback only. */
export function goalMet(widget: WidgetSpec, state: unknown): boolean {
  return widget.type === "balance_scale" ? balanceGoal(widget, state) : graphGoal(widget, state);
}

// ---- drawing helpers (UI only; no effect on the goal) -----------------------------------

export function sideString(boxes: number, weights: number): string {
  const parts: string[] = [];
  if (boxes) parts.push(boxes === 1 ? "x" : `${boxes}x`);
  if (weights) parts.push(String(weights));
  return parts.join(" + ") || "0";
}

export function balanceTilt(state: BalanceState, boxWeight: number): number {
  const diff = balanceMass(state.lb, state.lw, boxWeight) - balanceMass(state.rb, state.rw, boxWeight);
  return Math.max(-16, Math.min(16, diff * 2.2));
}

export function graphValue(g: FunctionGraphParams, x: number): number {
  return g.slope * x + g.intercept;
}

/** Snap a dragged x onto the step grid, and onto the solution when it is very close. */
export function snapGraphX(g: FunctionGraphParams, raw: number, toSolution = true): number {
  const step = g.step ?? 0.1;
  const clamped = Math.max(g.x_min, Math.min(g.x_max, raw));
  let x = g.x_min + Math.round((clamped - g.x_min) / step) * step;
  x = Math.round(x * 1e6) / 1e6;
  const star = (g.target_y - g.intercept) / g.slope;
  if (toSolution && Math.abs(x - star) <= 2 * step) x = Math.round(star * 1e6) / 1e6;
  return x;
}
