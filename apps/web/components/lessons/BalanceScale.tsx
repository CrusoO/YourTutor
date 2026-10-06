"use client";

import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { pick, type BalanceScaleWidget } from "@/lib/lessons/types";
import {
  balanceStart,
  balanceTilt,
  goalMet,
  isBalanced,
  sideString,
  type BalanceState,
} from "@/lib/lessons/widgets";
import { prefersReducedMotion } from "./ScenePlayer";

type Props = {
  widget: BalanceScaleWidget;
  locale: string;
  /** Called once each time the goal state is reached. The server re-checks it. */
  onSolved?: (state: BalanceState, actionsCount: number) => void;
  reducedMotion?: boolean;
};

function useTween(target: number, reduced: boolean): number {
  const [value, setValue] = useState(target);
  const from = useRef(target);
  useEffect(() => {
    if (reduced || from.current === target || typeof requestAnimationFrame !== "function") {
      from.current = target;
      setValue(target);
      return;
    }
    const start = performance.now();
    const a = from.current;
    let raf = 0;
    const frame = (now: number) => {
      let k = Math.min(1, (now - start) / 450);
      k = 1 - Math.pow(1 - k, 3);
      const next = a + (target - a) * k;
      from.current = next;
      setValue(next);
      if (k < 1) raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, [target, reduced]);
  return value;
}

function Pan({
  ex,
  ey,
  boxes,
  weights,
  side,
  tap,
  onTake,
}: {
  ex: number;
  ey: number;
  boxes: number;
  weights: number;
  side: "L" | "R";
  tap: boolean;
  onTake: (side: "L" | "R") => void;
}) {
  const py = ey + 82;
  const items = [...Array(boxes).fill("b"), ...Array(weights).fill("w")] as ("b" | "w")[];
  const per = 4;
  return (
    <g>
      <line x1={ex} y1={ey} x2={ex - 52} y2={py} className="lp-str" />
      <line x1={ex} y1={ey} x2={ex + 52} y2={py} className="lp-str" />
      <path d={`M${ex - 58} ${py} L${ex + 58} ${py} Q${ex} ${py + 26} ${ex - 58} ${py}Z`} className="lp-panb" />
      {items.map((item, i) => {
        const row = Math.floor(i / per);
        const col = i % per;
        const n = Math.min(per, items.length - row * per);
        const x = ex - n * 11 + 11 + col * 22;
        const y = py - 12 - row * 22;
        if (item === "b") {
          return (
            <g key={i}>
              <rect x={x - 10} y={y - 10} width={20} height={20} rx={4} className="lp-box" />
              <text x={x} y={y + 5} className="lp-boxt">
                x
              </text>
            </g>
          );
        }
        const label = `Take one weight off the ${side === "L" ? "left" : "right"}`;
        return (
          <g
            key={i}
            className={`lp-wt${tap ? " tap" : ""}`}
            role={tap ? "button" : undefined}
            tabIndex={tap ? 0 : undefined}
            aria-label={tap ? label : undefined}
            onClick={tap ? () => onTake(side) : undefined}
            onKeyDown={
              tap
                ? (e: KeyboardEvent) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onTake(side);
                    }
                  }
                : undefined
            }
          >
            <circle cx={x} cy={y} r={13} fill="transparent" />
            <circle cx={x} cy={y} r={10} className="lp-wc" />
            <text x={x} y={y + 4} className="lp-wtt">
              1
            </text>
          </g>
        );
      })}
    </g>
  );
}

/** Static balance picture, also used by the predict beat. */
export function BalanceFigure({
  state,
  boxWeight,
  tap = false,
  onTake = () => {},
  reducedMotion,
}: {
  state: BalanceState;
  boxWeight: number;
  tap?: boolean;
  onTake?: (side: "L" | "R") => void;
  reducedMotion?: boolean;
}) {
  const reduced = reducedMotion ?? prefersReducedMotion();
  const deg = useTween(balanceTilt(state, boxWeight), reduced);
  const t = (deg * Math.PI) / 180;
  const L = 110;
  const cx = 170;
  const cy = 58;
  const lx = cx - L * Math.cos(t);
  const ly = cy + L * Math.sin(t);
  const rx = cx + L * Math.cos(t);
  const ry = cy - L * Math.sin(t);
  const level = isBalanced(state, boxWeight);
  const label = `Left pan: ${state.lb} boxes and ${state.lw} weights. Right pan: ${state.rb} boxes and ${state.rw} weights. ${
    level ? "Level." : deg > 0 ? "Left side down." : "Right side down."
  }`;
  return (
    <svg viewBox="0 0 340 246" role="img" aria-label={label} className="lp-svg">
      <path d={`M${cx} ${cy} L${cx} 228`} className="lp-stand" />
      <rect x={cx - 46} y={226} width={92} height={12} rx={6} className="lp-standb" />
      <Pan ex={lx} ey={ly} boxes={state.lb} weights={state.lw} side="L" tap={tap} onTake={onTake} />
      <Pan ex={rx} ey={ry} boxes={state.rb} weights={state.rw} side="R" tap={tap} onTake={onTake} />
      <line x1={lx} y1={ly} x2={rx} y2={ry} className="lp-beam" />
      <circle cx={cx} cy={cy} r={7} className="lp-pivot" />
    </svg>
  );
}

export default function BalanceScale({ widget, locale, onSolved, reducedMotion }: Props) {
  const p = widget.params;
  const start = useMemo(() => balanceStart(p), [p]);
  const [state, setState] = useState<BalanceState>(start);
  const [history, setHistory] = useState<BalanceState[]>([]);
  const [actions, setActions] = useState(0);
  const solved = goalMet(widget, state);
  const level = isBalanced(state, p.box_weight);
  const wasSolved = useRef(false);
  const cb = useRef(onSolved);
  cb.current = onSolved;

  useEffect(() => {
    if (solved && !wasSolved.current) cb.current?.(state, actions);
    wasSolved.current = solved;
  }, [solved, state, actions]);

  function push(next: BalanceState) {
    setHistory((h) => [...h, state]);
    setState(next);
    setActions((n) => n + 1);
  }
  const take = (side: "L" | "R") => {
    if (side === "L" ? state.lw > 0 : state.rw > 0) {
      push(side === "L" ? { ...state, lw: state.lw - 1 } : { ...state, rw: state.rw - 1 });
    }
  };
  const canSplit =
    level && state.lb > 1 && state.rb === 0 && state.lw % state.lb === 0 && state.rw % state.lb === 0;
  const split = () =>
    push({ lb: 1, lw: state.lw / state.lb, rb: 0, rw: state.rw / state.lb });

  let message: { tone: "good" | "bad" | "tip"; text: string };
  if (solved) message = { tone: "good", text: pick(widget.success, locale) };
  else if (!level)
    message = {
      tone: "bad",
      text: "Tilted. You took more off one side. Take the same off the other side, or tap Undo.",
    };
  else if (state.lw === 0 && state.lb > 1)
    message = {
      tone: "tip",
      text: `Only boxes on the left now. Split both sides into ${state.lb} equal parts to find what one box weighs.`,
    };
  else if (state.lw < start.lw)
    message = {
      tone: "tip",
      text: "Still level. Keep going: clear the loose weights off the left, and take the same number off the right.",
    };
  else message = { tone: "tip", text: "Tap a weight to take it off. Keep the balance level." };

  return (
    <div className="lp-widget">
      <p className="lp-lead">{pick(widget.prompt, locale)}</p>
      <div className="lp-eq" aria-live="polite">
        <span>{sideString(state.lb, state.lw)}</span>
        <span className={level ? "eqs" : "neq"}>{level ? "=" : "≠"}</span>
        <span>{sideString(state.rb, state.rw)}</span>
      </div>
      <div className="lp-panel">
        <BalanceFigure state={state} boxWeight={p.box_weight} tap onTake={take} reducedMotion={reducedMotion} />
      </div>
      <div className="lp-ctrl">
        <button type="button" className="lp-btn main" onClick={split} disabled={!canSplit}>
          {state.lb === 2 ? "Split both sides in half" : `Split both sides into ${state.lb} parts`}
        </button>
        <button
          type="button"
          className="lp-btn"
          disabled={history.length === 0}
          onClick={() => {
            const prev = history[history.length - 1];
            setHistory((h) => h.slice(0, -1));
            setState(prev);
          }}
        >
          Undo
        </button>
        <button
          type="button"
          className="lp-btn"
          onClick={() => {
            setState(start);
            setHistory([]);
            setActions(0);
          }}
        >
          Start over
        </button>
      </div>
      <p className={`lp-fb ${message.tone}`} aria-live="polite">
        {message.text}
      </p>
    </div>
  );
}
