"use client";

import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ensureDevStudent, skipLogin } from "@/lib/dev-auth";
import { getSession, locale, postEvent, type ActionPayload } from "@/lib/api";
import { t } from "@/lib/messages";
import { elapsedMs, hintDelayMs, idleNudgeMs } from "@/lib/session-timers";
import { applyBodyClasses, loadUi } from "@/lib/ui";
import ReadAloud from "@/components/flow/ReadAloud";
import SourceChips from "@/components/flow/SourceChips";
import LessonPlayer from "@/components/lessons/LessonPlayer";
import DoneScreen from "@/components/flow/DoneScreen";
import { StuckPoint, StuckStep, checkText } from "@/components/session/StuckPoint";
import { ConfidenceAsk, ExplainGrade, WhyWrong, type Confidence } from "@/components/session/Signals";
import { offeredWays, readReason, type Way } from "@/lib/session/ways";
import BlockedState, { hasNoQuestion } from "@/components/session/BlockedState";
import BreakOrSwitch from "@/components/session/BreakOrSwitch";
import ItemLabels from "@/components/session/ItemLabels";
import ProgressHeader, { FeedbackBlock, HintHeading } from "@/components/session/Progress";
import {
  parseIntegerStem,
  plainSourceLabel,
  showSignHintButton,
  verifiedParse,
  visibleSteps,
} from "@/lib/session/integer-stem";
import { reasonCopy, type DoneSummary } from "@/lib/flow";
import { useCopy, useLocale } from "@/lib/locale";
import { withSession } from "@/lib/session/copy";
import SessionStyles from "@/components/session/sessionStyles";

// The number-line panels load only inside the session route, never in the homepage bundle.
const SignExplanation = lazy(() => import("@/components/session/SignExplain").then((m) => ({ default: m.SignExplanation })));
const AnotherWay = lazy(() => import("@/components/session/AnotherWay").then((m) => ({ default: m.AnotherWay })));
const SignHint = lazy(() => import("@/components/session/SignExplain").then((m) => ({ default: m.SignHint })));

/** Help is always allowed when the server says so; `can_request_hint` is the deprecated name. */
function canHelp(a: ActionPayload): boolean {
  return Boolean(a.can_request_help ?? a.can_request_hint ?? a.allow_hint);
}

export default function SessionPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const baseCopy = useCopy();
  const copy = withSession(baseCopy);
  const activeLocale = useLocale();
  const [action, setAction] = useState<ActionPayload | null>(null);
  const ui = typeof window === "undefined" ? undefined : loadUi();
  useEffect(() => applyBodyClasses(loadUi()), []);
  const [answer, setAnswer] = useState("");
  const [step, setStep] = useState(1);
  const [pictureOpen, setPictureOpen] = useState(false);
  const [hintReady, setHintReady] = useState(false);
  const [nudge, setNudge] = useState(false);
  const [wrongOnce, setWrongOnce] = useState(false);
  // Practice items finished so far (the server sends no total, so the header shows a count, not a percentage).
  const [itemsDone, setItemsDone] = useState(0);
  // Help was pressed on this question; for sign sums it opens the number-line hint button.
  const [helpAsked, setHelpAsked] = useState(false);
  // The hint on screen came from a wrong answer (not from pressing Help).
  const [hintAfterWrong, setHintAfterWrong] = useState(false);
  const idle = useRef<number | null>(null);
  const hintTimer = useRef<number | null>(null);
  // When the current question appeared, so an answer carries the time it really took.
  const shownAt = useRef(Date.now());
  // The answer the learner has given but not yet sent: practice asks "how sure were you?" before sending it.
  const [pending, setPending] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const inFlight = useRef(false);
  // Timed when the answer was given, not when the confidence was tapped.
  const answeredMs = useRef(1);

  /** The payload of an answer: what was said, how long it took, and how sure the learner said they were. */
  function answerPayload(response: string, confidence?: Confidence | null): Record<string, unknown> {
    const latency_ms = pending === response ? answeredMs.current : elapsedMs(shownAt.current);
    return { response, latency_ms, ...(confidence ? { confidence } : {}) };
  }

  /** Check was pressed, or an option picked. Practice asks for confidence next; anything else sends now. */
  function giveAnswer(response: string, ask: boolean) {
    if (inFlight.current) return;
    if (!ask) {
      send("answer", answerPayload(response));
      return;
    }
    answeredMs.current = elapsedMs(shownAt.current);
    setPending(response);
  }

  /** One request at a time. On a failure the answer stays on screen so it can be sent again. */
  async function sendPending(confidence: Confidence | null) {
    if (inFlight.current || pending === null) return;
    setSending(true);
    try {
      await send("answer", answerPayload(pending, confidence));
    } catch {
      /* the answer is kept; the buttons come back */
    } finally {
      setSending(false);
    }
  }

  function questionShown() {
    shownAt.current = Date.now();
    setPending(null);
    setPictureOpen(false);
  }

  function armTimers(next: ActionPayload) {
    if (idle.current) window.clearTimeout(idle.current);
    if (hintTimer.current) window.clearTimeout(hintTimer.current);
    setNudge(false);
    idle.current = window.setTimeout(() => setNudge(true), idleNudgeMs);
    if (next.type === "show_item" && canHelp(next)) {
      setHintReady(wrongOnce);
      hintTimer.current = window.setTimeout(() => setHintReady(true), hintDelayMs);
    }
  }

  async function load() {
    const view = await getSession(params.id);
    setAction(view.action);
    setItemsDone(view.progress?.items_completed ?? 0);
    questionShown();
    armTimers(view.action);
  }

  useEffect(() => {
    load().catch(async () => {
      if (skipLogin()) {
        await ensureDevStudent();
        await load();
        return;
      }
      router.push("/login");
    });
    return () => {
      if (idle.current) window.clearTimeout(idle.current);
      if (hintTimer.current) window.clearTimeout(hintTimer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.id]);

  // Practice: "I don't know" is its own event (hint, no mastery change). The assessment keeps
  // its answer-text form, which the server scores as "don't know" there.
  const dontKnowButton =
    action && (action.dont_know_option || canHelp(action) || action.can_show_solution) ? (
      <button
        type="button"
        className="ghost"
        data-testid="dont-know"
        onClick={() =>
          send(action.dont_know_option ? "answer" : "dont_know", {
            ...(action.dont_know_option ? { response: "i don't know" } : {}),
            latency_ms: elapsedMs(shownAt.current),
          })
        }
      >
        {copy.dontKnow}
      </button>
    ) : null;

  /** Every event goes one at a time: a second tap while one is in flight is ignored. */
  async function send(event_type: string, payload: Record<string, unknown> = {}, itemId?: string | null) {
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      await sendNow(event_type, payload, itemId);
    } finally {
      inFlight.current = false;
    }
  }

  async function sendNow(event_type: string, payload: Record<string, unknown> = {}, itemId?: string | null) {
    const view = await postEvent(params.id, event_type, payload, itemId ?? action?.item_id);
    const next = view.action;
    if (event_type === "idle_nudge" && next.type === "nudge" && action) {
      setNudge(false);
      armTimers(action);
      return;
    }
    setAction(next);
    if (view.progress) setItemsDone(view.progress.items_completed ?? 0);
    questionShown();
    setAnswer("");
    setStep(1);
    setHintAfterWrong(event_type === "answer" && next.type === "hint");
    if (event_type === "request_help") setHelpAsked(true);
    if (event_type === "answer" && next.type === "hint") {
      setWrongOnce(true);
      setHintReady(true);
    }
    if (next.type === "similar_item" || next.type === "show_item") {
      setWrongOnce(false);
      setHintReady(false);
      setHelpAsked(false);
    }
    if (next.type === "check_your_work") {
      setWrongOnce(true);
      setHintReady(true);
    }
    armTimers(next);
  }

  if (!action) return <p>…</p>;

  if (action.type === "end_session" && action.session_type !== "checkpoint") {
    const summary = (action.extras as { summary?: DoneSummary } | undefined)?.summary;
    return (
      <DoneScreen
        copy={copy}
        reason={action.ended_reason || action.reason}
        summary={summary}
        encouragement={
          (action.extras as { encouragement?: { text?: string | null } } | undefined)?.encouragement?.text
        }
        onKeepGoing={(chapterId) => router.push(`/chapters/${encodeURIComponent(chapterId)}`)}
        onChapters={() => router.push("/chapters")}
      />
    );
  }

  if (action.type === "end_session" || action.type === "checkpoint_score") {
    return (
      <main className="stack column">
        <h1>{copy.done}</h1>
        <p>{reasonCopy(copy, action.ended_reason || action.reason)}</p>
        {action.extras && action.type === "checkpoint_score" ? (
          <p>Score: {String((action.extras as { score?: number }).score ?? "")}</p>
        ) : null}
        <button type="button" onClick={() => router.push("/today")}>
          {copy.backToday}
        </button>
      </main>
    );
  }

  if (action.type === "test_out_result") {
    const passed = Boolean((action.extras as { passed?: boolean } | undefined)?.passed);
    return (
      <main className="stack column" data-testid="test-out-result" data-passed={passed}>
        <h1>{copy.skipAheadTitle}</h1>
        <p className={passed ? "banner good" : "banner"}>
          {passed ? copy.skipAheadPassed : copy.skipAheadMissed}
        </p>
        <button type="button" onClick={() => router.push("/chapters")}>
          {copy.doneChapters}
        </button>
      </main>
    );
  }

  if (action.lesson && (action.type === "predict" || action.type === "worked_example")) {
    // A lesson exists for this skill: it replaces the plain predict / worked-example screens. The
    // server re-checks every widget result; beats never write BKT or FSRS.
    return (
      <LessonPlayer
        key={action.lesson.id}
        lesson={action.lesson}
        locale={activeLocale}
        mode="session"
        sources={action.sources}
        startAt={action.type === "worked_example" ? 1 : 0}
        onPredict={(choice) => send("predict_response", { response: choice ?? "" })}
        onSceneAsk={(info) => {
          postEvent(params.id, "scene_answer", {
            scene_id: info.sceneId,
            step: info.step,
            choice: info.choice,
          }).catch(() => {});
        }}
        onWidgetResult={async (r) => {
          const view = await postEvent(params.id, "interactive_result", {
            widget_id: r.widget_id,
            final_state: r.final_state,
            actions_count: r.actions_count,
          });
          return !view.action.rejected;
        }}
        onFadedAnswer={async (index, response) => {
          const view = await postEvent(params.id, "faded_answer", { faded: index, response });
          return view.action.lesson_correct === true;
        }}
        onComplete={({ latency_ms }) => send("continue", { latency_ms })}
      />
    );
  }

  if (hasNoQuestion(action)) return <BlockedState kind="no_question" />;
  if (action.type === "content_gap") return <BlockedState kind="content_gap" />;

  const item = action.item;
  const mcq = item?.type === "mcq";
  // The tap is optional and only for practice (a diagnostic or checkpoint gives no feedback to calibrate on).
  const askConfidence = action.session_type === "practice" && action.type !== "warmup_item";
  const answerArea = (label: string, submit: string) =>
    askConfidence && pending !== null ? (
      <ConfidenceAsk
        copy={copy}
        answer={mcq ? (item?.options?.find((o) => o.id === pending)?.label ?? pending) : pending}
        busy={sending}
        onChoose={sendPending}
        onChange={() => setPending(null)}
      />
    ) : mcq ? (
      <Mcq options={item?.options || []} onPick={(id) => giveAnswer(id, askConfidence)} />
    ) : (
      <AnswerForm
        value={answer}
        onChange={setAnswer}
        label={label}
        submit={submit}
        onSubmit={() => giveAnswer(answer, askConfidence)}
      />
    );
  const extras = (action.extras ?? {}) as Record<string, unknown>;
  const praise = (extras.encouragement as { text?: string | null } | undefined)?.text;
  const testOut = (action.extras as { test_out?: { index: number; of: number } } | undefined)?.test_out;

  const practiceScreen =
    action.session_type === "practice" &&
    ["show_item", "similar_item", "hint", "feedback", "reveal_solution", "check_your_work"].includes(action.type);
  const stemParse = parseIntegerStem(item?.stem);
  // The explanation panel needs a parse whose computed result equals the item's answer; else the plain solution stays.
  const solutionParse = action.type === "reveal_solution" ? verifiedParse(item?.stem, item?.answer) : null;
  const solutionSteps = visibleSteps(item?.steps, item?.stem);
  const plainSources = action.sources?.map((src) => ({ ...src, title: plainSourceLabel(src.title) }));
  const signHint = showSignHintButton(stemParse, {
    wrongOnce,
    helpAsked,
    hintShown: action.type === "hint",
  });
  const reason = readReason(extras);
  const ways = reason
    ? offeredWays(reason.offer, {
        picture: signHint && Boolean(stemParse) && !pictureOpen,
        steps: canHelp(action),
        worked: Boolean(action.can_show_solution),
      })
    : [];
  const chooseWay = (way: Way) => {
    // Recorded without waiting; the help itself is the same action the old buttons sent.
    postEvent(params.id, "move_chosen", { family: way }, action.item_id).catch(() => {});
    if (way === "steps") send("request_help");
    else if (way === "worked") send("show_solution");
    else if (way === "picture") setPictureOpen(true);
  };
  const signHintNode =
    signHint && stemParse && action.session_type === "practice" ? (
      <Suspense fallback={null}>
        <SignHint key={pictureOpen ? "open" : "closed"} copy={copy} parse={stemParse} defaultOpen={pictureOpen} />
      </Suspense>
    ) : null;

  return (
    <main className="stack column sess">
      <SessionStyles />
      {practiceScreen ? <ProgressHeader copy={copy} done={itemsDone} /> : null}
      {action.type === "warmup_item" ? (
        <header className="stack">
          <h1>{copy.warmupTitle}</h1>
          <p className="muted">{copy.warmupHint}</p>
        </header>
      ) : null}
      {testOut ? (
        <header className="stack">
          <h1>{copy.skipAheadTitle}</h1>
          <p className="muted">
            {copy.skipAheadCount} {testOut.index} {copy.skipAheadOf} {testOut.of}
          </p>
        </header>
      ) : null}
      {praise ? (
        <p className="banner good" data-testid="encouragement">
          {praise}
        </p>
      ) : null}
      {extras.support === "step_down" ? (
        <p className="muted" data-testid="support-note">
          {copy.supportStepDown}
        </p>
      ) : null}
      {nudge ? (
        <button
          type="button"
          className="ghost"
          onClick={() => {
            setNudge(false);
            send("idle_nudge", { idle_ms: idleNudgeMs });
          }}
        >
          {copy.idleNudge}
        </button>
      ) : null}

      {action.type === "break_or_switch" ? (
        <BreakOrSwitch
          copy={copy}
          choices={(extras.choices as string[] | undefined) ?? []}
          onChoose={(choice) => send("break_choice", { choice })}
        />
      ) : null}

      {action.type === "ask_stuck_point" ? (
        <StuckPoint
          copy={copy}
          stem={item?.stem}
          choices={(extras.choices as string[] | undefined) ?? []}
          onChoose={(choice) => send("stuck_choice", { choice })}
        />
      ) : null}

      {action.type === "ask_stuck_step" ? (
        <StuckStep
          copy={copy}
          stem={item?.stem}
          count={Number(extras.step_count ?? 0)}
          onPick={(index) => send("stuck_step", { index })}
        />
      ) : null}

      {action.type === "check_your_work" ? (
        <div className="stack" data-testid="check-your-work">
          <h1>{copy.checkTitle}</h1>
          <p className="stem">{item?.stem}</p>
          <p className="banner">{checkText(copy, extras.check_kind as string | undefined)}</p>
          {answerArea(copy.answerPlaceholder, copy.submit)}
          {hintReady ? (
            <button type="button" className="secondary" onClick={() => send("request_help")}>
              {copy.helpButton}
            </button>
          ) : null}
        </div>
      ) : null}

      {action.type === "predict" ? (
        <>
          <h1>{copy.predict}</h1>
          {item?.stem ? <p className="stem" data-testid="predict-problem">{item.stem}</p> : null}
          <p className="stem">{action.text || item?.prediction}</p>
          {!item?.stem ? (
            <p className="muted" data-testid="predict-no-problem">
              {copy.predictNoProblem}
            </p>
          ) : null}
          <button type="button" onClick={() => send("predict_response", { response: "yes" })}>
            {copy.yes}
          </button>
          <button type="button" className="secondary" onClick={() => send("predict_response", { response: "no" })}>
            {copy.no}
          </button>
        </>
      ) : null}

      {action.type === "worked_example" ? (
        <>
          {extras.representation_change ? (
            <p className="muted" data-testid="other-view">
              {copy.otherView}
            </p>
          ) : null}
          <h1>{item?.stem || action.text}</h1>
          <ol className="steps">
            {visibleSteps(item?.steps, item?.stem).slice(0, step).map((row) => (
              <li key={row}>{row}</li>
            ))}
          </ol>
          <SourceChips sources={plainSources} label={copy.sourceLabel} />
          {item?.steps && step < item.steps.length ? (
            <button type="button" className="secondary" onClick={() => setStep(step + 1)}>
              {copy.nextStep}
            </button>
          ) : (
            <button type="button" onClick={() => send("continue")}>
              {copy.continue}
            </button>
          )}
        </>
      ) : null}

      {action.type === "hint" ? (
        <>
          <div className="q-card">
            <p className="stem">{item?.stem}</p>
          </div>
          <HintHeading copy={copy} afterWrong={hintAfterWrong} />
          {extras.kind === "restate" || extras.kind === "step" ? (
            <p className="muted">{extras.kind === "restate" ? copy.hintRestateLabel : copy.hintStepLabel}</p>
          ) : null}
          <WhyWrong
            copy={copy}
            diagnosis={extras.diagnosis as { class?: string } | undefined}
            onNotWhy={(diagnosed) => {
              // Recorded without touching the screen: the learner stays on the same question and timer.
              postEvent(params.id, "diagnosis_correction", { diagnosed }, action.item_id).catch(() => {});
            }}
          />
          <p className="banner" data-testid="hint-text">{action.text}</p>
          {ways.length > 0 ? (
            <Suspense fallback={null}>
              <AnotherWay copy={copy} ways={ways} busy={sending} onChoose={chooseWay} />
            </Suspense>
          ) : null}
          {ways.length === 0 || pictureOpen ? signHintNode : null}
          {answerArea(copy.answerPlaceholder, copy.submit)}
          {dontKnowButton}
          {ways.length === 0 && canHelp(action) ? (
            <button type="button" className="secondary" data-testid="help-button" onClick={() => send("request_help")}>
              {copy.helpButton}
            </button>
          ) : null}
          {ways.length === 0 && action.can_show_solution ? (
            <button type="button" className="ghost" onClick={() => send("show_solution")}>
              {copy.reveal}
            </button>
          ) : null}
        </>
      ) : null}

      {action.type === "reveal_solution" ? (
        <>
          <h1>{copy.revealTitle}</h1>
          <div className="q-card">
            <p className="stem">{item?.stem}</p>
            <p className="ans-label">{copy.answerLabel}</p>
            <p className="math ans-value" data-testid="solution-answer">{item?.answer || action.text}</p>
          </div>
          {solutionParse ? (
            <Suspense fallback={null}>
              <SignExplanation copy={copy} parse={solutionParse} />
            </Suspense>
          ) : null}
          {solutionSteps.length > 0 && solutionParse ? (
            <details className="more-steps">
              <summary>{copy.moreStepsLabel}</summary>
              <ol className="steps">
                {solutionSteps.map((row) => (
                  <li key={row}>{row}</li>
                ))}
              </ol>
            </details>
          ) : solutionSteps.length > 0 ? (
            <ol className="steps" aria-label={copy.stepsLabel}>
              {solutionSteps.map((row) => (
                <li key={row}>{row}</li>
              ))}
            </ol>
          ) : null}
          <SourceChips sources={plainSources} label={copy.sourceLabel} />
          <button type="button" onClick={() => send("continue")}>
            {copy.similar}
          </button>
        </>
      ) : null}

      {action.type === "similar_item" || action.type === "show_item" || action.type === "warmup_item" ? (
        <>
          {extras.probe ? (
            <header className="stack" data-testid="probe">
              <h1>{copy.probeTitle}</h1>
              <p className="muted">{copy.probeHint}</p>
            </header>
          ) : null}
          {extras.challenge ? (
            <header className="stack" data-testid="challenge">
              <h1>{copy.challengeLabel}</h1>
              <p className="muted">{copy.challengeHint}</p>
            </header>
          ) : null}
          {extras.win ? (
            <p className="muted" data-testid="win">
              {copy.winLabel}
            </p>
          ) : null}
          <div className="q-card">
            <p className="stem">{item?.stem}</p>
            <ReadAloud text={item?.stem || ""} lang={activeLocale} ui={ui} />
            <ItemLabels labels={item?.labels} />
          </div>
          {signHintNode}
          {answerArea(copy.answerPlaceholder, copy.submit)}
          {dontKnowButton}
          {extras.prompt_submit ? <p className="banner">{copy.promptSubmit}</p> : null}
          {canHelp(action) ? (
            <button type="button" className="secondary" data-testid="help-button" onClick={() => send("request_help")}>
              {copy.helpButton}
            </button>
          ) : null}
          {action.can_show_solution ? (
            <button type="button" className="ghost" onClick={() => send("show_solution")}>
              {copy.reveal}
            </button>
          ) : null}
        </>
      ) : null}

      {action.type === "explain_back_prompt" || action.type === "explain_back_result" ? (
        <>
          <h1>{copy.explainBack}</h1>
          {action.type === "explain_back_result" ? <ExplainGrade copy={copy} grade={action.grade} /> : null}
          <p>{action.text}</p>
          {action.type === "explain_back_result" ? (
            <SourceChips sources={action.sources} label={copy.sourceLabel} />
          ) : null}
          {action.type === "explain_back_prompt" ? (
            <AnswerForm
              value={answer}
              onChange={setAnswer}
              label={copy.explainBack}
              submit={copy.explainContinue}
              area
              onSubmit={() => send("explain_back", { text: answer })}
            />
          ) : (
            <button type="button" onClick={() => send("continue")}>
              {copy.continue}
            </button>
          )}
        </>
      ) : null}

      {action.type === "nudge" ? (
        <button type="button" onClick={() => send("continue")}>
          {copy.continue}
        </button>
      ) : null}

      {action.type === "feedback" ? (
        <>
          <FeedbackBlock copy={copy} correct={Boolean(action.correct)} />
          <button type="button" onClick={() => send("continue")}>
            {copy.continue}
          </button>
        </>
      ) : null}

      {action.type === "content_gap" ? (
        <button type="button" onClick={() => router.push("/today")}>
          {copy.backToday}
        </button>
      ) : null}
    </main>
  );
}

function Mcq({
  options,
  onPick,
}: {
  options: { id: string; label: string }[];
  onPick: (id: string) => void;
}) {
  return (
    <div className="stack">
      {options.map((opt) => (
        <button key={opt.id} type="button" className="secondary" onClick={() => onPick(opt.id)}>
          {opt.label || opt.id}
        </button>
      ))}
    </div>
  );
}

function AnswerForm({
  value,
  onChange,
  onSubmit,
  label,
  submit,
  area,
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  label: string;
  submit: string;
  area?: boolean;
}) {
  return (
    <form
      className="stack"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      {area ? (
        <textarea className="math" value={value} onChange={(e) => onChange(e.target.value)} placeholder={label} />
      ) : (
        <input
          className="math"
          inputMode="decimal"
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={label}
        />
      )}
      <button type="submit">{submit}</button>
    </form>
  );
}
