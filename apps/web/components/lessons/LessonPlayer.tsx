"use client";

import dynamic from "next/dynamic";
import { useRef, useState } from "react";
import { pick, type Beat, type Lesson, type NumberLineFigure } from "@/lib/lessons/types";
import { choiceValueToNumber, expression, guessToChoiceValue } from "@/lib/lessons/numberline";
import { balanceStart } from "@/lib/lessons/widgets";
import { t, type Messages } from "@/lib/messages";
import SourceChips, { type SourceChip } from "@/components/flow/SourceChips";
import BalanceScale, { BalanceFigure } from "./BalanceScale";
import FunctionGraph from "./FunctionGraph";
import ScenePlayer, { type Delay, type SceneAskInfo } from "./ScenePlayer";

// The number line is only needed on lessons that carry a figure, so it loads on demand and stays
// out of every other route's bundle.
const NumberLine = dynamic(() => import("./NumberLine"), {
  ssr: false,
  loading: () => <div aria-hidden="true" style={{ minHeight: 320 }} />,
});

/** The player's own words come from the locale files (English wherever a Hindi string is missing or unreviewed). */
function lessonCopy(m: Messages) {
  return {
    continue: m.lessonContinue,
    start: m.lessonStart,
    nextStep: m.lessonNextStep,
    checking: m.lessonChecking,
    verified: m.lessonVerified,
    notVerified: m.lessonNotVerified,
    checkTitle: m.lessonCheckTitle,
    previewNote: m.lessonPreviewNote,
    answerLabel: m.lessonAnswerLabel,
    source: m.lessonSource,
    check: m.lessonCheck,
    fadedPreviewNote: m.lessonFadedPreviewNote,
    another: m.numberLineAnother,
    steps: {
      predict: m.lessonStepGuess,
      explore: m.lessonStepTry,
      explain_scene: m.lessonStepWatch,
      worked_example: m.lessonStepExample,
      faded_example: m.lessonStepFinish,
      check: m.lessonStepPractise,
    },
  };
}

export type WidgetResult = { widget_id: string; final_state: unknown; actions_count: number };

type Props = {
  lesson: Lesson;
  locale: string;
  mode: "session" | "preview";
  /** Beat to open on: 1 when the session is already past the predict step (resumed). */
  startAt?: number;
  onPredict?: (choice: string | null) => Promise<void> | void;
  onSceneAsk?: (info: SceneAskInfo) => void;
  /** Resolves true when the server accepted the widget result. */
  onWidgetResult?: (result: WidgetResult) => Promise<boolean>;
  /** Resolves true when the server says the typed answer to faded example number `index` is right. */
  onFadedAnswer?: (index: number, response: string) => Promise<boolean>;
  onComplete?: (info: { latency_ms: number }) => Promise<void> | void;
  reducedMotion?: boolean;
  delay?: Delay;
  /** Approved sources of this lesson, shown as chips on the scene and worked-example beats. */
  sources?: SourceChip[];
};

function Beats({ beat, children }: { beat: Beat; children: React.ReactNode }) {
  return <section className={`lp-step lp-${beat.kind}`}>{children}</section>;
}

export default function LessonPlayer({
  lesson,
  locale,
  mode,
  startAt = 0,
  onPredict,
  onSceneAsk,
  onWidgetResult,
  onFadedAnswer,
  onComplete,
  reducedMotion,
  delay,
  sources,
}: Props) {
  const COPY = lessonCopy(t(locale));
  const [cur, setCur] = useState(startAt);
  const [maxSeen, setMaxSeen] = useState(startAt);
  const [guess, setGuess] = useState<string | null>(null);
  const [predictSent, setPredictSent] = useState(startAt > 0);
  const [stepsShown, setStepsShown] = useState(1);
  const [verify, setVerify] = useState<Record<string, "pending" | "ok" | "bad">>({});
  const [busy, setBusy] = useState(false);
  const [fadedText, setFadedText] = useState("");
  const [faded, setFaded] = useState<"idle" | "pending" | "ok" | "bad">("idle");
  const [exampleLocked, setExampleLocked] = useState(false);
  const [extraIdx, setExtraIdx] = useState<number | null>(null);
  const started = useRef(Date.now());
  const beats = lesson.beats;
  const beat = beats[cur];
  const last = beats.length - 1;

  function go(i: number) {
    const next = Math.max(0, Math.min(last, i));
    setCur(next);
    setMaxSeen((m) => Math.max(m, next));
    setStepsShown(1);
    setFadedText("");
    setFaded("idle");
    setExampleLocked(false);
    setExtraIdx(null);
    window.scrollTo?.(0, 0);
  }

  async function next() {
    if (busy) return;
    if (beat.kind === "predict" && !predictSent) {
      setBusy(true);
      try {
        await onPredict?.(guess);
        setPredictSent(true);
      } finally {
        setBusy(false);
      }
    }
    if (beat.kind === "check") {
      setBusy(true);
      try {
        await onComplete?.({ latency_ms: Date.now() - started.current });
      } finally {
        setBusy(false);
      }
      return;
    }
    go(cur + 1);
  }

  async function widgetSolved(widgetId: string, finalState: unknown, actions: number) {
    setVerify((v) => ({ ...v, [widgetId]: "pending" }));
    try {
      const ok = onWidgetResult
        ? await onWidgetResult({ widget_id: widgetId, final_state: finalState, actions_count: actions })
        : true;
      setVerify((v) => ({ ...v, [widgetId]: ok ? "ok" : "bad" }));
    } catch {
      setVerify((v) => ({ ...v, [widgetId]: "bad" }));
    }
  }

  async function checkFaded(typed?: string) {
    const text = (typed ?? fadedText).trim();
    if (!onFadedAnswer || text === "" || faded === "pending") return;
    const index = beats.slice(0, cur).filter((b) => b.kind === "faded_example").length;
    setFaded("pending");
    try {
      setFaded((await onFadedAnswer(index, text)) ? "ok" : "bad");
    } catch {
      setFaded("bad");
    }
  }

  // The Guess step's figure is shown again, hopping, on the Watch step so the guess can be checked.
  const guessFigure: NumberLineFigure | null =
    (beats.find((b) => b.kind === "predict") as Extract<Beat, { kind: "predict" }> | undefined)?.number_line ?? null;
  const workedFigure: NumberLineFigure | null =
    beat.kind === "worked_example" && beat.number_line
      ? extraIdx === null
        ? beat.number_line
        : (beat.more_number_lines?.[extraIdx] ?? beat.number_line)
      : null;
  const showWrittenSteps = beat.kind === "worked_example" && (!beat.number_line || (exampleLocked && extraIdx === null));

  const primary = beat.kind === "check" ? (mode === "session" ? COPY.start : null) : COPY.continue;

  return (
    <div className="lp">
      <header className="lp-top">
        <div>
          <h1>{pick(lesson.title, locale)}</h1>
        </div>
      </header>

      <nav className="lp-path" aria-label="Lesson steps" style={{ gridTemplateColumns: `repeat(${beats.length}, 1fr)` }}>
        {beats.map((b, i) => (
          <button
            key={i}
            type="button"
            className={`${i === cur ? "on" : ""}${i <= maxSeen ? " seen" : ""}`}
            disabled={i > maxSeen}
            aria-current={i === cur ? "step" : undefined}
            onClick={() => go(i)}
          >
            <span className="n">{i + 1}</span>
            {COPY.steps[b.kind]}
          </button>
        ))}
      </nav>

      <main>
        {beat.kind === "predict" ? (
          <Beats beat={beat}>
            <h2 tabIndex={-1}>{pick(beat.prompt, locale)}</h2>
            {beat.number_line ? (
              <NumberLine
                key={`${beat.number_line.start}:${beat.number_line.delta}`}
                start={beat.number_line.start}
                delta={beat.number_line.delta}
                mode="predict"
                after="hold"
                locale={locale}
                reducedMotion={reducedMotion}
                externalGuess={guess === null ? null : choiceValueToNumber(guess)}
                onGuess={(v) => setGuess(guessToChoiceValue(v, beat.choices))}
              />
            ) : null}
            {beat.figure ? (
              <div className="lp-panel">
                <BalanceFigure
                  state={balanceStart(beat.figure)}
                  boxWeight={beat.figure.box_weight}
                  reducedMotion={reducedMotion}
                />
              </div>
            ) : null}
            <div className="lp-choices" role="group" aria-label={pick(beat.prompt, locale)}>
              {beat.choices.map((c) => (
                <button
                  key={c.value}
                  type="button"
                  className="lp-choice"
                  aria-pressed={guess === c.value}
                  onClick={() => setGuess(c.value)}
                >
                  {pick(c.text, locale)}
                </button>
              ))}
            </div>
            {guess !== null && beat.reveal ? <p className="lp-fb tip">{pick(beat.reveal, locale)}</p> : null}
          </Beats>
        ) : null}

        {beat.kind === "explore" ? (
          <Beats beat={beat}>
            <h2 tabIndex={-1}>{pick(beat.title, locale)}</h2>
            {beat.intro ? <p className="lp-intro">{pick(beat.intro, locale)}</p> : null}
            {beat.widget.type === "balance_scale" ? (
              <BalanceScale
                key={beat.widget.widget_id}
                widget={beat.widget}
                locale={locale}
                reducedMotion={reducedMotion}
                onSolved={(s, n) => widgetSolved(beat.widget.widget_id, s, n)}
              />
            ) : (
              <FunctionGraph
                key={beat.widget.widget_id}
                widget={beat.widget}
                locale={locale}
                onSolved={(s, n) => widgetSolved(beat.widget.widget_id, s, n)}
              />
            )}
            {verify[beat.widget.widget_id] ? (
              <p className={`lp-verify ${verify[beat.widget.widget_id]}`} role="status">
                {verify[beat.widget.widget_id] === "pending"
                  ? COPY.checking
                  : verify[beat.widget.widget_id] === "ok"
                    ? COPY.verified
                    : COPY.notVerified}
              </p>
            ) : null}
          </Beats>
        ) : null}

        {beat.kind === "explain_scene" ? (
          <Beats beat={beat}>
            <h2 tabIndex={-1}>{pick(beat.title, locale)}</h2>
            {guessFigure ? (
              <NumberLine
                key={`reveal:${guessFigure.start}:${guessFigure.delta}`}
                start={guessFigure.start}
                delta={guessFigure.delta}
                mode="reveal"
                autoPlay={false}
                priorGuess={guess === null ? null : choiceValueToNumber(guess)}
                locale={locale}
                reducedMotion={reducedMotion}
              />
            ) : null}
            <ScenePlayer
              key={beat.scene.id}
              scene={beat.scene}
              locale={locale}
              finalCaption={beat.final_caption}
              onAsk={onSceneAsk}
              reducedMotion={reducedMotion}
              delay={delay}
            />
          </Beats>
        ) : null}

        {beat.kind === "worked_example" ? (
          <Beats beat={beat}>
            <h2 tabIndex={-1}>{pick(beat.title, locale)}</h2>
            <p className="lp-problem">{pick(beat.problem, locale)}</p>
            {beat.number_line && workedFigure ? (
              <>
                {beat.more_number_lines && beat.more_number_lines.length > 0 ? (
                  <div className="lp-ctrl chips" role="group" aria-label={COPY.another}>
                    {[beat.number_line, ...beat.more_number_lines].map((f, i) => (
                      <button
                        key={`${f.start}:${f.delta}`}
                        type="button"
                        className="lp-btn"
                        aria-pressed={(extraIdx === null ? 0 : extraIdx + 1) === i}
                        onClick={() => setExtraIdx(i === 0 ? null : i - 1)}
                      >
                        {expression(f.start, f.delta)}
                      </button>
                    ))}
                  </div>
                ) : null}
                <NumberLine
                  key={`ex:${workedFigure.start}:${workedFigure.delta}`}
                  start={workedFigure.start}
                  delta={workedFigure.delta}
                  mode="predict"
                  after="reveal"
                  locale={locale}
                  reducedMotion={reducedMotion}
                  onLocked={() => setExampleLocked(true)}
                />
              </>
            ) : null}
            {showWrittenSteps ? (
              <ol className="lp-steps">
                {beat.steps.slice(0, stepsShown).map((s, i) => (
                  <li key={i}>{pick(s, locale)}</li>
                ))}
              </ol>
            ) : null}
            {showWrittenSteps && stepsShown < beat.steps.length ? (
              <button type="button" className="lp-btn" onClick={() => setStepsShown((n) => n + 1)}>
                {COPY.nextStep}
              </button>
            ) : null}
          </Beats>
        ) : null}

        {beat.kind === "faded_example" ? (
          <Beats beat={beat}>
            <h2 tabIndex={-1}>{pick(beat.title, locale)}</h2>
            <p className="lp-problem">{pick(beat.problem, locale)}</p>
            <ol className="lp-steps">
              {beat.steps.map((st, i) => (
                <li key={i}>{pick(st, locale)}</li>
              ))}
            </ol>
            {beat.number_line ? (
              <NumberLine
                key={`faded:${beat.number_line.start}:${beat.number_line.delta}`}
                start={beat.number_line.start}
                delta={beat.number_line.delta}
                mode="predict"
                after="check"
                locale={locale}
                reducedMotion={reducedMotion}
                onLocked={(r) => {
                  setFadedText(String(r.guess));
                  void checkFaded(String(r.guess));
                }}
              />
            ) : null}
            <p className="lp-problem">{pick(beat.blank_prompt, locale)}</p>
            {onFadedAnswer ? (
              <form
                className="lp-faded"
                onSubmit={(e) => {
                  e.preventDefault();
                  void checkFaded();
                }}
              >
                <input
                  type="text"
                  aria-label={COPY.answerLabel}
                  placeholder={COPY.answerLabel}
                  value={fadedText}
                  autoComplete="off"
                  readOnly={faded === "ok"}
                  onChange={(e) => setFadedText(e.target.value)}
                />
                <button type="submit" className="lp-btn" disabled={fadedText.trim() === "" || faded === "pending" || faded === "ok"}>
                  {COPY.check}
                </button>
              </form>
            ) : (
              <p className="lp-src">{COPY.fadedPreviewNote}</p>
            )}
            {faded === "pending" ? (
              <p className="lp-verify pending" role="status">
                {COPY.checking}
              </p>
            ) : null}
            {faded === "ok" ? <p className="lp-fb tip" role="status">{pick(beat.success, locale)}</p> : null}
            {faded === "bad" && beat.hint ? <p className="lp-fb tip" role="status">{pick(beat.hint, locale)}</p> : null}
          </Beats>
        ) : null}

        {beat.kind === "check" ? (
          <Beats beat={beat}>
            <h2 tabIndex={-1}>{COPY.checkTitle}</h2>
            <p className="lp-problem">{pick(beat.prompt, locale)}</p>
            {mode === "preview" ? <p className="lp-src">{COPY.previewNote}</p> : null}
          </Beats>
        ) : null}
        {beat.kind === "explain_scene" || beat.kind === "worked_example" || beat.kind === "faded_example" ? (
          <SourceChips sources={sources} label={COPY.source} />
        ) : null}
      </main>

      {primary ? (
        <div className="lp-bar">
          <button type="button" className="lp-primary" disabled={busy} onClick={next}>
            {primary}
          </button>
        </div>
      ) : null}
    </div>
  );
}
