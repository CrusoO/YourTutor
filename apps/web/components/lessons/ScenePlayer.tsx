"use client";

import { useEffect, useId, useRef, useState } from "react";
import { pick, type L10n, type PauseAndAsk, type Scene, type SceneAction } from "@/lib/lessons/types";

export type SceneAskInfo = { sceneId: string; step: number; choice: number; correct: boolean };
export type Delay = (ms: number) => Promise<void>;
type DrawAction = Exclude<SceneAction, PauseAndAsk>;
type Drawn = { key: number; action: DrawAction };

const realDelay: Delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

/** How long a piece of text takes to be "written", and how long a caption stays before moving on. */
export const writeMs = (text: string) => Math.min(1100, 250 + text.length * 55);
export const dwellMs = (caption: string, reduced: boolean) =>
  reduced ? 900 : Math.max(1600, caption.length * 42);

type Props = {
  scene: Scene;
  locale: string;
  finalCaption?: L10n;
  /** Called for every answer a student picks in a pause_and_ask (right or wrong). */
  onAsk?: (info: SceneAskInfo) => void;
  onDone?: () => void;
  /** Tests inject an instant delay; reduced motion is read from the browser unless overridden. */
  delay?: Delay;
  reducedMotion?: boolean;
  speak?: (text: string) => Promise<void> | void;
};

export default function ScenePlayer({
  scene,
  locale,
  finalCaption,
  onAsk,
  onDone,
  delay = realDelay,
  reducedMotion,
  speak,
}: Props) {
  const uid = useId().replace(/:/g, "");
  const reduced = reducedMotion ?? prefersReducedMotion();
  const [drawn, setDrawn] = useState<Drawn[]>([]);
  const [caption, setCaption] = useState("");
  const [stepIdx, setStepIdx] = useState(0);
  const [ask, setAsk] = useState<{ step: number; ask: PauseAndAsk } | null>(null);
  const [wrong, setWrong] = useState<number[]>([]);
  const [feedback, setFeedback] = useState("");
  const [paused, setPaused] = useState(false);
  const [done, setDone] = useState(false);
  const run = useRef(0);
  const pausedRef = useRef(false);
  const answer = useRef<((index: number) => void) | null>(null);
  const keyRef = useRef(0);
  const cb = useRef({ onAsk, onDone, speak });
  cb.current = { onAsk, onDone, speak };
  const width = scene.canvas?.width ?? 340;
  const height = scene.canvas?.height ?? 290;

  async function play() {
    const mine = ++run.current;
    const alive = () => run.current === mine;
    setDrawn([]);
    setDone(false);
    setAsk(null);
    setPaused(false);
    pausedRef.current = false;
    for (let s = 0; s < scene.steps.length; s++) {
      setStepIdx(s);
      const step = scene.steps[s];
      const text = pick(step.caption, locale);
      let shown = false;
      const showCaption = () => {
        if (shown) return;
        shown = true;
        setCaption(text);
        void cb.current.speak?.(text);
      };
      for (const action of step.actions) {
        if (!alive()) return;
        if (action.kind === "pause_and_ask") {
          setCaption("");
          await new Promise<void>((resolve) => {
            setWrong([]);
            setFeedback("");
            setAsk({ step: s, ask: action });
            answer.current = (index: number) => {
              const option = action.options[index];
              cb.current.onAsk?.({ sceneId: scene.id, step: s, choice: index, correct: option.correct });
              if (option.correct) {
                setAsk(null);
                resolve();
              } else {
                setWrong((prev) => [...prev, index]);
                setFeedback(`${pick(option.feedback, locale)} ${locale === "en" ? "Try again." : ""}`.trim());
              }
            };
          });
          answer.current = null;
          continue;
        }
        showCaption();
        const ms =
          action.kind === "write_text" ? (reduced ? 0 : writeMs(action.text)) : reduced ? 0 : 350;
        const key = keyRef.current++;
        setDrawn((prev) => [...prev, { key, action }]);
        if (ms) await delay(ms);
      }
      showCaption();
      await delay(dwellMs(text, reduced));
      while (pausedRef.current && alive()) await delay(120);
    }
    if (!alive()) return;
    if (finalCaption) setCaption(pick(finalCaption, locale));
    setDone(true);
    setPaused(true);
    pausedRef.current = true;
    cb.current.onDone?.();
  }

  useEffect(() => {
    void play();
    return () => {
      run.current += 1; // cancel
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scene.id]);

  function togglePause() {
    if (done) {
      void play();
      return;
    }
    pausedRef.current = !pausedRef.current;
    setPaused(pausedRef.current);
  }

  return (
    <div className="lp-board">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={pick(scene.alt, locale)}>
        <defs>
          <marker id={`${uid}-arrow`} viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0 0 L10 5 L0 10 z" className="lp-arrowhead" />
          </marker>
        </defs>
        <g>
          {drawn.map(({ key, action }) => (
            <DrawnAction key={key} uid={uid} id={key} action={action} animate={!reduced} />
          ))}
        </g>
      </svg>
      <div className="lp-dots" aria-hidden="true">
        {scene.steps.map((_, i) => (
          <span key={i} className={i <= stepIdx ? "on" : ""} />
        ))}
      </div>
      <p className="lp-caption" aria-live="polite" data-testid="scene-caption">
        {caption}
      </p>
      {ask ? (
        <div className="lp-ask" role="group" aria-label={pick(ask.ask.question, locale)}>
          <p>{pick(ask.ask.question, locale)}</p>
          <div className="lp-choices">
            {ask.ask.options.map((option, i) => (
              <button
                key={i}
                type="button"
                className={`lp-choice${wrong.includes(i) ? " wrong" : ""}`}
                onClick={() => answer.current?.(i)}
              >
                {pick(option.text, locale)}
              </button>
            ))}
          </div>
          {feedback ? (
            <p className="lp-fb bad" aria-live="polite">
              {feedback}
            </p>
          ) : null}
        </div>
      ) : null}
      <div className="lp-ctrl">
        <button type="button" className="lp-btn main" onClick={togglePause}>
          {done ? "Play again" : paused ? "Play" : "Pause"}
        </button>
        <button type="button" className="lp-btn" onClick={() => void play()}>
          Replay
        </button>
      </div>
      <p className="lp-src">Source: {scene.source_ref}</p>
    </div>
  );
}

function DrawnAction({
  uid,
  id,
  action,
  animate,
}: {
  uid: string;
  id: number;
  action: DrawAction;
  animate: boolean;
}) {
  const fade = animate ? (
    <animate attributeName="opacity" from="0" to="1" dur="350ms" fill="freeze" />
  ) : null;
  const tone = (c?: string | null) => (c ? ` ${c}` : "");
  switch (action.kind) {
    case "write_text": {
      const clip = `${uid}-clip-${id}`;
      const w = action.size * 0.62 * action.text.length + 8;
      return (
        <g>
          {animate ? (
            <clipPath id={clip}>
              <rect x={action.x - w / 2} y={action.y - action.size} height={action.size * 1.6} width={0}>
                <animate attributeName="width" from="0" to={w} dur={`${writeMs(action.text)}ms`} fill="freeze" />
              </rect>
            </clipPath>
          ) : null}
          <text
            x={action.x}
            y={action.y}
            textAnchor="middle"
            className={`lp-wbt${tone(action.color)}`}
            style={{ fontSize: action.size }}
            clipPath={animate ? `url(#${clip})` : undefined}
          >
            {action.text}
          </text>
        </g>
      );
    }
    case "draw_shape":
      if (action.shape === "rect")
        return (
          <rect x={action.x ?? 0} y={action.y ?? 0} width={action.w ?? 0} height={action.h ?? 0} rx={6} className={`lp-shape${tone(action.color)}`}>
            {fade}
          </rect>
        );
      if (action.shape === "circle")
        return (
          <circle cx={action.cx ?? 0} cy={action.cy ?? 0} r={action.r ?? 0} className={`lp-shape${tone(action.color)}`}>
            {fade}
          </circle>
        );
      return (
        <line x1={action.x1 ?? 0} y1={action.y1 ?? 0} x2={action.x2 ?? 0} y2={action.y2 ?? 0} className={`lp-shape${tone(action.color)}`}>
          {fade}
        </line>
      );
    case "draw_arrow":
      return (
        <line
          x1={action.x1}
          y1={action.y1}
          x2={action.x2}
          y2={action.y2}
          className={`lp-shape${tone(action.color)}`}
          markerEnd={`url(#${uid}-arrow)`}
        >
          {fade}
        </line>
      );
    case "highlight":
      return (
        <rect x={action.x} y={action.y} width={action.w} height={action.h} rx={10} className="lp-hl">
          {fade}
        </rect>
      );
  }
}
