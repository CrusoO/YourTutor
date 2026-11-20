"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { pick, type Beat, type Lesson, type NumberLineFigure } from "@/lib/lessons/types";
import { choiceValueToNumber, countOnHint, expression, firstSignKind, guessToChoiceValue, shouldCountOn, type SignKind } from "@/lib/lessons/numberline";
import { lessonFlowEn as flow, fill } from "@/lib/lessons/copy";
import { balanceStart } from "@/lib/lessons/widgets";
import { t, type Messages } from "@/lib/messages";
import SourceChips, { type SourceChip } from "@/components/flow/SourceChips";
import BalanceScale, { BalanceFigure } from "./BalanceScale";
import FunctionGraph from "./FunctionGraph";
import ScenePlayer, { type Delay, type SceneAskInfo } from "./ScenePlayer";
import SignHelp from "./SignHelp";

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
    placeFirst: m.lessonPlaceDotFirst,
    pickFirst: m.lessonPickAnswerFirst,
    lockIn: m.numberLineLockIn,
    checkBtn: m.numberLineCheck,
    countFirst: m.lessonCountFirst,
    workOut: m.lessonWorkOut,
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

/** Styles for the main button's reason line, kept with the lazy player so the homepage stays light. */
const BAR_CSS = `.lp-why { max-width: 328px; margin: 0 auto 8px; text-align: center; font-size: 0.9rem; line-height: 1.35; color: var(--c-muted); } .lp-why.nudge { color: var(--c-text); font-weight: 600; } .lp-count { margin: 0 0 4px; font-size: 0.9rem; color: var(--c-muted); } .lp-links { display: flex; flex-wrap: wrap; justify-content: center; gap: 4px 16px; } .lp-link { background: none; border: 0; width: auto; min-height: 44px; min-width: 44px; padding: 8px 6px; color: var(--c-accent-ink); font-size: 0.95rem; font-weight: 600; text-decoration: underline; text-underline-offset: 3px; cursor: pointer; } .lp-link:focus-visible { outline: 3px solid var(--c-focus); outline-offset: 2px; } @layer legacy { .lp .lp-bar .lp-primary.is-blocked { background: var(--c-line); color: var(--c-muted) !important; cursor: not-allowed; } }`;

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
  const [dotTouched, setDotTouched] = useState(false);
  const [lockSignal, setLockSignal] = useState(0);
  const [nudge, setNudge] = useState(0);
  const [fadedHint, setFadedHint] = useState(0);
  const [typing, setTyping] = useState(false);
  const [barH, setBarH] = useState(96);
  const barRef = useRef<HTMLDivElement>(null);
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
    setDotTouched(false);
    setNudge(0);
    setFadedHint(0);
    setTyping(false);
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
  // One example at a time: the first figure, then each of the others, in order.
  const exampleFigures: NumberLineFigure[] =
    beat.kind === "worked_example" && beat.number_line ? [beat.number_line, ...(beat.more_number_lines ?? [])] : [];
  const exIdx = extraIdx === null ? 0 : extraIdx + 1;
  const workedFigure: NumberLineFigure | null = exampleFigures[exIdx] ?? null;
  // The extra figures may carry their own authored problem text and one-line note.
  const extra = beat.kind === "worked_example" && exIdx > 0 ? (beat.more_number_lines ?? [])[exIdx - 1] : undefined;
  const moreExamples = exampleFigures.length > exIdx + 1;
  const showWrittenSteps = beat.kind === "worked_example" && (!beat.number_line || (exampleLocked && exIdx === 0));

  // The sign note: said once, the first time a figure in the lesson needs it, at that screen only.
  const seq: { beat: number; sub: number; f: NumberLineFigure }[] = [];
  beats.forEach((b, bi) => {
    if (b.kind === "predict" && b.number_line) seq.push({ beat: bi, sub: 0, f: b.number_line });
    if (b.kind === "worked_example" && b.number_line) [b.number_line, ...(b.more_number_lines ?? [])].forEach((f, k) => seq.push({ beat: bi, sub: k, f }));
    if (b.kind === "faded_example" && b.number_line) seq.push({ beat: bi, sub: 0, f: b.number_line });
  });
  const seqNow = seq.findIndex((x) => x.beat === cur && x.sub === (beat.kind === "worked_example" ? exIdx : 0));
  const noteKind: SignKind | null = seqNow < 0 ? null : firstSignKind(seq.map((x) => x.f), seqNow);
  const signNote = noteKind === "minus" ? flow.signNoteMinus : noteKind === "negative" ? flow.signNoteNegative : null;

  const primary = beat.kind === "check" ? (mode === "session" ? COPY.start : null) : COPY.continue;

  // Some steps need one action first. The main button is then either that action ("Check") or visibly
  // switched off with the reason beside it; it is never a live-looking button that does nothing.
  const predictCount =
    beat.kind === "predict" && !!beat.number_line && shouldCountOn(beat.number_line.delta);
  const exampleCount = workedFigure ? shouldCountOn(workedFigure.delta) : false;
  const counting = predictCount || exampleCount;
  const fadedFigure = beat.kind === "faded_example" ? (beat.number_line ?? null) : null;
  const fadedDone = faded === "ok";
  const inputShown = beat.kind === "faded_example" && !!onFadedAnswer && (!fadedFigure || typing);
  const typedReady = inputShown && fadedText.trim() !== "";
  const needsLock =
    (beat.kind === "worked_example" && !!beat.number_line && !exampleLocked) ||
    (beat.kind === "faded_example" && !fadedDone && (fadedFigure ? !(exampleLocked && faded !== "bad") : true)) ||
    (predictCount && !predictSent && guess === null);
  const needsGuess = beat.kind === "predict" && !predictCount && !predictSent && guess === null;
  const fadedReady = beat.kind === "faded_example" && (typedReady || (!!fadedFigure && dotTouched));
  const anotherNow = beat.kind === "worked_example" && exampleLocked && moreExamples;
  const lockNow = needsLock && (beat.kind === "faded_example" ? fadedReady : dotTouched);
  const blocked = (needsLock && !lockNow) || needsGuess;
  const why = blocked
    ? needsLock
      ? beat.kind === "faded_example"
        ? faded === "bad"
          ? fadedFigure
            ? flow.tryAgainDot
            : flow.notQuite
          : fadedFigure
            ? flow.placeDotCheck
            : flow.typeFirst
        : counting
          ? COPY.countFirst
          : COPY.placeFirst
      : COPY.pickFirst
    : null;
  const label = lockNow
    ? beat.kind === "faded_example"
      ? COPY.check
      : counting
        ? COPY.checkBtn
        : COPY.lockIn
    : beat.kind === "faded_example" && !fadedDone
      ? faded === "pending"
        ? COPY.checking
        : COPY.check
      : anotherNow
        ? flow.another
        : primary;

  function press() {
    if (blocked) {
      setNudge((n) => n + 1);
      return;
    }
    if (lockNow) {
      if (beat.kind === "faded_example" && typedReady) void checkFaded();
      else setLockSignal((n) => n + 1);
      return;
    }
    if (anotherNow) {
      setExtraIdx(exIdx);
      setExampleLocked(false);
      setDotTouched(false);
      setStepsShown(1);
      setNudge(0);
      return;
    }
    void next();
  }

  // Help for Finish it: one rung at a time, only when asked. The last rung is the lesson's own hint when it has one.
  const fadedRungs: string[] = [];
  if (beat.kind === "faded_example") {
    if (fadedFigure) {
      fadedRungs.push(countOnHint(fadedFigure.start, fadedFigure.delta, 1), countOnHint(fadedFigure.start, fadedFigure.delta, 2));
      fadedRungs.push(
        beat.hint
          ? pick(beat.hint, locale)
          : fill(flow.hintDragCount, { n: Math.abs(fadedFigure.delta), dir: fadedFigure.delta >= 0 ? "to the right" : "to the left" }),
      );
    } else if (beat.hint) {
      fadedRungs.push(pick(beat.hint, locale));
    }
  }

  // The scrolling content keeps clear of the fixed bar whatever its height (a reason line, large text).
  useEffect(() => {
    const el = barRef.current;
    if (!el) return;
    const measure = () => {
      const h = Math.ceil(el.getBoundingClientRect().height);
      if (h > 0) setBarH(h);
    };
    measure();
    if (typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [primary, why]);

  return (
    <div className="lp" style={{ ["--lp-bar-h" as string]: `${barH}px` }} data-testid="lesson-player">
      <style>{BAR_CSS}</style>
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
            {beat.number_line ? <SignHelp note={signNote} /> : null}
            {beat.number_line ? (
              <NumberLine
                key={`${beat.number_line.start}:${beat.number_line.delta}`}
                start={beat.number_line.start}
                delta={beat.number_line.delta}
                mode="predict"
                after={predictCount ? "check" : "hold"}
                countOn={predictCount}
                locale={locale}
                reducedMotion={reducedMotion}
                onGuess={predictCount ? undefined : (v) => setGuess(guessToChoiceValue(v, beat.choices))}
                onLocked={predictCount ? (r) => setGuess(guessToChoiceValue(r.guess, beat.choices)) : undefined}
                onTouchedChange={predictCount ? setDotTouched : undefined}
                lockSignal={predictCount ? lockSignal : undefined}
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
            {beat.number_line ? null : (
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
            )}
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
            {exampleFigures.length > 1 ? (
              <p className="lp-count" data-testid="example-count">
                {fill(flow.exampleOf, { n: exIdx + 1, total: exampleFigures.length })}
              </p>
            ) : null}
            <p className="lp-problem">
              {exIdx > 0 && workedFigure
                ? (extra?.problem ?? `${COPY.workOut} ${expression(workedFigure.start, workedFigure.delta)}.`)
                : pick(beat.problem, locale)}
            </p>
            {beat.number_line && workedFigure ? (
              <>
                <SignHelp note={extra?.note ?? signNote} />
                <NumberLine
                  key={`ex:${exIdx}:${workedFigure.start}:${workedFigure.delta}`}
                  start={workedFigure.start}
                  delta={workedFigure.delta}
                  mode="predict"
                  after="reveal"
                  countOn={exampleCount}
                  locale={locale}
                  reducedMotion={reducedMotion}
                  onLocked={() => setExampleLocked(true)}
                  onTouchedChange={setDotTouched}
                  lockSignal={lockSignal}
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
              <>
                <SignHelp note={signNote} />
                <NumberLine
                  key={`faded:${beat.number_line.start}:${beat.number_line.delta}`}
                  start={beat.number_line.start}
                  delta={beat.number_line.delta}
                  mode="predict"
                  after="check"
                  locale={locale}
                  reducedMotion={reducedMotion}
                  onTouchedChange={setDotTouched}
                  lockSignal={lockSignal}
                  onLocked={(r) => {
                    setExampleLocked(true);
                    setFadedText(String(r.guess));
                    void checkFaded(String(r.guess));
                  }}
                />
              </>
            ) : null}
            <p className="lp-problem">{pick(beat.blank_prompt, locale)}</p>
            {onFadedAnswer ? (
              <>
                {inputShown ? (
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
                  </form>
                ) : null}
                {fadedFigure && !fadedDone ? (
                  <div className="lp-links">
                    <button type="button" className="lp-link" onClick={() => setTyping((v) => !v)}>
                      {typing ? flow.useLine : flow.typeInstead}
                    </button>
                  </div>
                ) : null}
              </>
            ) : (
              <p className="lp-src">{COPY.fadedPreviewNote}</p>
            )}
            {faded === "pending" ? (
              <p className="lp-verify pending" role="status">
                {COPY.checking}
              </p>
            ) : null}
            {faded === "ok" ? <p className="lp-fb tip" role="status">{pick(beat.success, locale)}</p> : null}
            {faded === "bad" && !fadedFigure ? <p className="lp-fb tip" role="status">{flow.notQuite}</p> : null}
            {fadedHint > 0 ? (
              <p className="lp-fb tip" role="status" data-testid="faded-hint">
                {fadedRungs[Math.min(fadedHint, fadedRungs.length) - 1]}
              </p>
            ) : null}
            {!fadedDone && fadedHint < fadedRungs.length ? (
              <div className="lp-links">
                <button type="button" className="lp-link" onClick={() => setFadedHint((n) => Math.min(fadedRungs.length, n + 1))}>
                  {fadedHint === 0 ? flow.hint : flow.anotherHint}
                </button>
              </div>
            ) : null}
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
        <div className="lp-bar" ref={barRef}>
          {why ? (
            <p id="lp-why" className={`lp-why${nudge > 0 ? " nudge" : ""}`} role="status" data-testid="primary-why">
              {why}
            </p>
          ) : null}
          <button
            type="button"
            className={`lp-primary${blocked ? " is-blocked" : ""}`}
            disabled={busy || faded === "pending"}
            aria-disabled={blocked ? "true" : undefined}
            aria-describedby={why ? "lp-why" : undefined}
            onClick={press}
          >
            {label}
          </button>
        </div>
      ) : null}
    </div>
  );
}
