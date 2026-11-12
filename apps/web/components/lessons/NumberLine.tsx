"use client";

import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import ReadAloud from "@/components/flow/ReadAloud";
import {
  checkPrediction,
  clampToLine,
  directionOf,
  expression,
  fmt,
  hopAnnouncement,
  isSafeFigure,
  narrationScript,
  pathPoints,
  predictScript,
  tokenText,
  valueFromX,
  valueText,
  viewWindow,
  type PredictionResult,
} from "@/lib/lessons/numberline";
import { t } from "@/lib/messages";
import { loadUi } from "@/lib/ui";
import { prefersReducedMotion } from "./ScenePlayer";
import { CSS, styles } from "./numberline-style";

export type NumberLineProps = {
  start: number;
  delta: number;
  /** Where the figure opens: PREDICT (place a guess first), REVEAL (hops) or EXPLORE (move it yourself). */
  mode?: "predict" | "reveal" | "explore";
  /** PREDICT only. "reveal": lock in, then hop. "check": lock in, then say right or wrong at once. "hold": no lock-in; every move is reported through onGuess and the answer is not shown. */
  after?: "reveal" | "check" | "hold";
  /** A guess made earlier (in the Guess step): REVEAL shows it against the true landing. */
  priorGuess?: number | null;
  /** Moves the dot from outside (a tapped choice button). Only used by `after="hold"`. */
  externalGuess?: number | null;
  /** The dot was moved (hold mode) or the guess was locked in. */
  onGuess?: (value: number) => void;
  onLocked?: (result: PredictionResult) => void;
  locale?: string;
  /** Overrides the browser setting; true shows the path as still arrows and steps by button. */
  reducedMotion?: boolean;
  hopMs?: number;
  autoPlay?: boolean;
  /** Show the Read aloud / Listen control with the generated narration. Default true. */
  narrate?: boolean;
};

const W = 340;
const PAD = 20;
const AXIS_Y = 88;
const ARC = 26;

type Phase = "predict" | "hops" | "checked" | "explore";

function arrowHead(x: number, y: number, fromX: number, fromY: number): string {
  const dx = x - fromX;
  const dy = y - fromY;
  const len = Math.hypot(dx, dy) || 1;
  const ux = dx / len;
  const uy = dy / len;
  const s = 5;
  const bx = x - ux * s * 1.6;
  const by = y - uy * s * 1.6;
  return `${x},${y} ${bx - uy * s},${by + ux * s} ${bx + uy * s},${by - ux * s}`;
}

export default function NumberLine(props: NumberLineProps) {
  const { start, delta, locale = "en" } = props;
  if (!isSafeFigure(start, delta)) {
    return (
      <p role="alert" className={styles.refused}>
        {t(locale).numberLineOutOfRange}
      </p>
    );
  }
  return <Line {...props} />;
}

function Line({
  start,
  delta,
  mode = "predict",
  after = "reveal",
  priorGuess = null,
  externalGuess = null,
  onGuess,
  onLocked,
  locale = "en",
  reducedMotion,
  hopMs = 650,
  autoPlay = true,
  narrate = true,
}: NumberLineProps) {
  const copy = t(locale);
  const reduced = reducedMotion ?? prefersReducedMotion();
  const land = start + delta;
  const total = Math.abs(delta);
  const path = useMemo(() => pathPoints(start, delta), [start, delta]);
  const dir = directionOf(delta);

  const win = useMemo(() => {
    // The mirror point (the same move the other way) is always on the line: it is the likeliest
    // wrong guess, and it keeps the line balanced around the start so it gives nothing away.
    const small = Math.abs(delta) <= 8;
    const base = viewWindow([start, land, ...(small ? [start - delta] : []), ...(priorGuess === null ? [] : [priorGuess])]);
    return small ? base : { min: Math.max(-20, base.min - 2), max: Math.min(20, base.max + 2) };
  }, [start, land, delta, priorGuess]);

  const [phase, setPhase] = useState<Phase>(mode === "reveal" ? "hops" : mode === "explore" ? "explore" : "predict");
  const [guess, setGuess] = useState<number>(priorGuess ?? start);
  const [touched, setTouched] = useState(false);
  const [hop, setHop] = useState(0);
  const [playing, setPlaying] = useState(mode === "reveal" && autoPlay && !reduced);
  const [result, setResult] = useState<PredictionResult | null>(
    mode === "reveal" && priorGuess !== null ? checkPrediction(start, delta, priorGuess) : null,
  );
  const [free, setFree] = useState(start);
  const [announce, setAnnounce] = useState("");
  const svgRef = useRef<SVGSVGElement>(null);
  const dragging = useRef(false);

  // A tapped choice button elsewhere on the screen moves the dot.
  useEffect(() => {
    if (externalGuess !== null && externalGuess !== undefined && after === "hold") {
      setGuess(clampToLine(externalGuess, win.min, win.max));
      setTouched(true);
    }
  }, [externalGuess, after, win.min, win.max]);

  // The hops: one unit at a time, each announced politely.
  useEffect(() => {
    if (phase !== "hops" || !playing || reduced) return;
    if (hop >= total) {
      setPlaying(false);
      return;
    }
    const id = setTimeout(() => setHop((h) => h + 1), hopMs);
    return () => clearTimeout(id);
  }, [phase, playing, hop, total, reduced, hopMs]);

  useEffect(() => {
    if (phase === "hops" && hop > 0) setAnnounce(hopAnnouncement(hop, total, path[hop]));
  }, [phase, hop, total, path]);

  const x = (n: number) => PAD + ((n - win.min) / (win.max - win.min)) * (W - 2 * PAD);
  const unit = x(win.min + 1) - x(win.min);
  const done = phase === "hops" && hop === total;
  const position = phase === "hops" ? path[hop] : phase === "explore" ? free : guess;
  const canDrag = phase === "predict" || phase === "explore";
  const tokenColor = dir === "right" ? styles.right : styles.left;
  const showAnswer = phase === "hops" || phase === "checked" || phase === "explore";

  function move(n: number) {
    const v = clampToLine(n, win.min, win.max);
    if (phase === "predict") {
      setGuess(v);
      setTouched(true);
      if (after === "hold") onGuess?.(v);
    } else if (phase === "explore") {
      setFree(v);
    }
  }

  function pointerValue(e: PointerEvent<SVGSVGElement>): number {
    const r = svgRef.current?.getBoundingClientRect();
    if (!r) return position;
    return valueFromX(e.clientX, r.left, r.width, win, PAD / W);
  }

  function onKey(e: KeyboardEvent) {
    if (!canDrag) return;
    const keys: Record<string, number> = { ArrowRight: 1, ArrowUp: 1, ArrowLeft: -1, ArrowDown: -1, PageUp: 5, PageDown: -5 };
    if (e.key in keys) {
      e.preventDefault();
      move(position + keys[e.key]);
    } else if (e.key === "Home") {
      e.preventDefault();
      move(win.min);
    } else if (e.key === "End") {
      e.preventDefault();
      move(win.max);
    }
  }

  function lock() {
    const r = checkPrediction(start, delta, guess);
    setResult(r);
    onGuess?.(guess);
    onLocked?.(r);
    if (after === "check") {
      setPhase("checked");
    } else {
      setHop(0);
      setPlaying(!reduced && autoPlay);
      setPhase("hops");
    }
  }

  function replay() {
    setHop(0);
    setPlaying(!reduced);
    setPhase("hops");
  }

  function tryAgain() {
    setResult(null);
    setGuess(start);
    setTouched(false);
    setPhase("predict");
  }

  function stepHop(by: number) {
    setPlaying(false);
    setHop((h) => Math.max(0, Math.min(total, h + by)));
  }

  const everyLabel = unit >= 22 ? 1 : unit >= 11 ? 2 : 5;
  const ticks: number[] = [];
  for (let n = win.min; n <= win.max; n++) ticks.push(n);
  const drawnHops = phase === "hops" ? (reduced ? total : hop) : 0;
  const trueResult = result ?? (priorGuess !== null && phase === "hops" ? checkPrediction(start, delta, priorGuess) : null);
  const guessMark = trueResult && !trueResult.correct && showAnswer ? trueResult.guess : null;
  const speech =
    phase === "predict" || (phase === "checked" && !result?.correct)
      ? predictScript(start, delta)
      : narrationScript(start, delta);

  const midX = (x(start) + x(land)) / 2;
  const tokenW = 46;

  const nowLabel = (phase === "hops" && !done) || phase === "explore" ? copy.numberLineNow : copy.numberLineResult;
  const nowValue =
    phase === "predict"
      ? "?"
      : phase === "hops"
        ? fmt(path[hop])
        : phase === "checked"
          ? fmt(land)
          : fmt(free);
  const moveValue = phase === "explore" ? (free === start ? "0" : tokenText(free - start)) : tokenText(delta);

  return (
    <div className={styles.wrap} data-phase={phase} data-testid="number-line">
      <style>{CSS}</style>
      <div className={styles.legend} aria-label={copy.numberLineLabel}>
        <span className={`${styles.chip} ${styles.right}`}>
          <span aria-hidden="true">{"→ "}</span>
          {copy.numberLineLegendRight}
        </span>
        <span className={`${styles.chip} ${styles.left}`}>
          <span aria-hidden="true">{"← "}</span>
          {copy.numberLineLegendLeft}
        </span>
      </div>

      <div className={styles.panel}>
        <svg
          ref={svgRef}
          viewBox={`0 0 ${W} 150`}
          className={`${styles.svg} ${canDrag ? styles.drag : ""}`}
          role="group"
          aria-label={`${copy.numberLineLabel}: ${expression(start, delta)}`}
          onPointerDown={(e) => {
            if (!canDrag) return;
            dragging.current = true;
            svgRef.current?.setPointerCapture?.(e.pointerId);
            move(pointerValue(e));
          }}
          onPointerMove={(e) => {
            if (dragging.current) move(pointerValue(e));
          }}
          onPointerUp={() => {
            dragging.current = false;
          }}
          onPointerCancel={() => {
            dragging.current = false;
          }}
        >
          {/* the sign shown as direction: the token sits over the path it describes */}
          <g className={tokenColor} aria-hidden="true">
            <rect x={midX - tokenW / 2} y={4} width={tokenW} height={22} rx={11} className={styles.tokenBox} />
            <text x={midX} y={19.5} textAnchor="middle" className={styles.tokenText}>
              {dir === "right" ? `${tokenText(delta)} →` : `← ${tokenText(delta)}`}
            </text>
          </g>

          <line x1={PAD - 8} y1={AXIS_Y} x2={W - PAD + 8} y2={AXIS_Y} className={styles.axis} />
          {ticks.map((n) => (
            <g key={n} aria-hidden="true">
              <line
                x1={x(n)}
                x2={x(n)}
                y1={AXIS_Y - (n === 0 ? 8 : 5)}
                y2={AXIS_Y + (n === 0 ? 8 : 5)}
                className={n === 0 ? styles.zeroTick : styles.tick}
              />
              {n === position || (Math.abs(n - position) * unit >= 20 && (n % everyLabel === 0 || n === 0)) ? (
                <text
                  x={x(n)}
                  y={AXIS_Y + 22}
                  textAnchor="middle"
                  className={n === position ? styles.tickNow : n === 0 ? styles.tickZero : styles.tickText}
                >
                  {fmt(n)}
                </text>
              ) : null}
            </g>
          ))}

          {path.slice(0, drawnHops + 1).map((p, i) => {
            if (i === 0) return null;
            const a = x(path[i - 1]);
            const b = x(p);
            const cx = (a + b) / 2;
            const arcH = Math.max(7, Math.min(ARC, Math.abs(b - a) * 1.1));
            const cy = AXIS_Y - 6 - arcH;
            const current = !reduced && i === hop;
            return (
              <g key={i} className={`${tokenColor} ${current ? styles.hopNow : ""}`} data-hop={i} aria-hidden="true">
                <path d={`M ${a} ${AXIS_Y - 8} Q ${cx} ${cy} ${b} ${AXIS_Y - 8}`} className={styles.arc} />
                <polygon points={arrowHead(b, AXIS_Y - 8, cx, cy)} className={styles.head} />
                {unit >= 15 || i % 5 === 0 || i === total ? (
                  <text x={cx} y={AXIS_Y - 6 - arcH / 2 - 4} textAnchor="middle" className={styles.hopNum}>
                    {i}
                  </text>
                ) : null}
              </g>
            );
          })}

          {/* start ring, answer ring, a wrong guess */}
          <g aria-hidden="true">
            <circle cx={x(start)} cy={AXIS_Y} r={8} className={styles.startRing} />
            <text x={Math.max(22, Math.min(W - 22, x(start)))} y={AXIS_Y + 38} textAnchor="middle" className={styles.markText}>
              {copy.numberLineStart}
            </text>
            {showAnswer && (done || phase === "checked" || phase === "explore") ? (
              <>
                <circle cx={x(land)} cy={AXIS_Y} r={9} className={styles.answerRing} />
                <text x={Math.max(22, Math.min(W - 22, x(land)))} y={AXIS_Y + 50} textAnchor="middle" className={styles.answerText}>
                  {copy.numberLineAnswerMark}
                </text>
              </>
            ) : null}
            {guessMark !== null && (done || phase === "checked") ? (
              <>
                <circle cx={x(guessMark)} cy={AXIS_Y} r={9} className={styles.guessRing} />
                <text x={Math.max(22, Math.min(W - 22, x(guessMark)))} y={AXIS_Y + 62} textAnchor="middle" className={styles.guessText}>
                  {copy.numberLineGuessMark}
                </text>
              </>
            ) : null}
          </g>

          {/* the dot: a slider wherever the learner may move it */}
          <g
            className={`${styles.marker} ${canDrag ? styles.markerLive : ""} ${reduced ? styles.still : ""}`}
            style={{ transform: `translateX(${x(position)}px)` }}
            role={canDrag ? "slider" : "img"}
            tabIndex={canDrag ? 0 : undefined}
            aria-label={canDrag ? (phase === "predict" ? copy.numberLineGuessLabel : copy.numberLineSlider) : `${copy.numberLineNow} ${valueText(position)}`}
            aria-valuemin={canDrag ? win.min : undefined}
            aria-valuemax={canDrag ? win.max : undefined}
            aria-valuenow={canDrag ? position : undefined}
            aria-valuetext={canDrag ? valueText(position) : undefined}
            onKeyDown={onKey}
          >
            <circle cx={0} cy={AXIS_Y} r={22} className={styles.hit} />
            <circle cx={0} cy={AXIS_Y} r={14} className={`${styles.ring} `} />
            <circle cx={0} cy={AXIS_Y} r={10} className={`${styles.dot} ${tokenColor}`} />
          </g>
        </svg>
      </div>

      <dl className={styles.numbers} aria-label={copy.numberLineLabel}>
        <div>
          <dt>{copy.numberLineStart}</dt>
          <dd data-testid="nl-start">{fmt(start)}</dd>
        </div>
        <div className={tokenColor}>
          <dt>{copy.numberLineMove}</dt>
          <dd data-testid="nl-move">{moveValue}</dd>
        </div>
        <div className={done || phase === "checked" ? styles.final : undefined}>
          <dt>{nowLabel}</dt>
          <dd data-testid="nl-result">{nowValue}</dd>
        </div>
      </dl>

      {phase === "predict" ? (
        <>
          <p className={styles.hint}>{copy.numberLinePredictHint}</p>
          <div className={styles.controls}>
            <button type="button" className={styles.btn} onClick={() => move(position - 1)} disabled={position <= win.min}>
              {copy.numberLineStepLeft}
            </button>
            <button type="button" className={styles.btn} onClick={() => move(position + 1)} disabled={position >= win.max}>
              {copy.numberLineStepRight}
            </button>
            {after !== "hold" ? (
              <button type="button" className={`${styles.btn} ${styles.main}`} onClick={lock} disabled={!touched}>
                {copy.numberLineLockIn}
              </button>
            ) : null}
          </div>
          {after === "hold" && touched ? (
            <p className={styles.note} role="status">
              {copy.numberLineGuessSaved}
            </p>
          ) : null}
        </>
      ) : null}

      {phase === "hops" ? (
        <>
          <div className={styles.controls}>
            {reduced || !playing ? (
              <>
                <button type="button" className={styles.btn} onClick={() => stepHop(-1)} disabled={hop === 0}>
                  {copy.numberLinePrevHop}
                </button>
                <button type="button" className={`${styles.btn} ${styles.main}`} onClick={() => stepHop(1)} disabled={hop === total}>
                  {copy.numberLineNextHop}
                </button>
              </>
            ) : null}
            {!done ? (
              <button
                type="button"
                className={styles.btn}
                onClick={() => {
                  setPlaying(false);
                  setHop(total);
                }}
              >
                {copy.numberLineSkip}
              </button>
            ) : null}
          </div>
          {done ? (
            <div className={styles.result} role="status">
              <p className={styles.landed}>
                {expression(start, delta)} = {fmt(land)}
              </p>
              {trueResult ? (
                <p className={trueResult.correct ? styles.good : styles.tip} data-testid="nl-reason">
                  {trueResult.reason}
                </p>
              ) : null}
              <div className={styles.controls}>
                <button type="button" className={styles.btn} onClick={replay}>
                  {copy.numberLineReplay}
                </button>
                <button type="button" className={`${styles.btn} ${styles.main}`} onClick={() => setPhase("explore")}>
                  {copy.numberLineExplore}
                </button>
              </div>
            </div>
          ) : null}
        </>
      ) : null}

      {phase === "checked" && result ? (
        <div className={styles.result} role="status">
          <p className={result.correct ? styles.good : styles.tip} data-testid="nl-reason">
            {result.reason}
          </p>
          <div className={styles.controls}>
            {!result.correct ? (
              <button type="button" className={styles.btn} onClick={tryAgain}>
                {copy.numberLineTrySame}
              </button>
            ) : null}
            <button type="button" className={`${styles.btn} ${styles.main}`} onClick={replay}>
              {copy.numberLineShowHops}
            </button>
          </div>
        </div>
      ) : null}

      {phase === "explore" ? (
        <>
          <p className={styles.hint}>{copy.numberLineExploreHint}</p>
          <div className={styles.controls}>
            <button type="button" className={styles.btn} onClick={() => move(free - 1)} disabled={free <= win.min}>
              {copy.numberLineStepLeft}
            </button>
            <button type="button" className={styles.btn} onClick={() => move(free + 1)} disabled={free >= win.max}>
              {copy.numberLineStepRight}
            </button>
          </div>
          <input
            type="range"
            className={styles.slider}
            min={win.min}
            max={win.max}
            step={1}
            value={free}
            aria-label={copy.numberLineSlider}
            aria-valuetext={valueText(free)}
            onChange={(e) => move(Number(e.target.value))}
          />
          <div className={styles.controls}>
            <button type="button" className={styles.btn} onClick={replay}>
              {copy.numberLineReplay}
            </button>
          </div>
        </>
      ) : null}

      {narrate ? <ReadAloud text={speech} lang="en" ui={loadUi()} /> : null}
      <div className={styles.sr} aria-live="polite" data-testid="nl-live">
        {announce}
      </div>
    </div>
  );
}
