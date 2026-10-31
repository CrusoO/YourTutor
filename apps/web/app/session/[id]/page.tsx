"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ensureDevStudent, skipLogin } from "@/lib/dev-auth";
import { getSession, locale, postEvent, type ActionPayload } from "@/lib/api";
import { t } from "@/lib/messages";
import { hintDelayMs, idleNudgeMs } from "@/lib/session-timers";
import { applyBodyClasses, loadUi } from "@/lib/ui";
import ReadAloud from "@/components/flow/ReadAloud";
import SourceChips from "@/components/flow/SourceChips";
import LessonPlayer from "@/components/lessons/LessonPlayer";
import DoneScreen from "@/components/flow/DoneScreen";
import { StuckPoint, StuckStep, checkText } from "@/components/session/StuckPoint";
import BreakOrSwitch from "@/components/session/BreakOrSwitch";
import { reasonCopy, type DoneSummary } from "@/lib/flow";
import { useCopy, useLocale } from "@/lib/locale";

/** Help is always allowed when the server says so; `can_request_hint` is the deprecated name. */
function canHelp(a: ActionPayload): boolean {
  return Boolean(a.can_request_help ?? a.can_request_hint ?? a.allow_hint);
}

export default function SessionPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const copy = useCopy();
  const activeLocale = useLocale();
  const [action, setAction] = useState<ActionPayload | null>(null);
  const ui = typeof window === "undefined" ? undefined : loadUi();
  useEffect(() => applyBodyClasses(loadUi()), []);
  const [answer, setAnswer] = useState("");
  const [step, setStep] = useState(1);
  const [hintReady, setHintReady] = useState(false);
  const [nudge, setNudge] = useState(false);
  const [wrongOnce, setWrongOnce] = useState(false);
  const idle = useRef<number | null>(null);
  const hintTimer = useRef<number | null>(null);

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

  async function send(event_type: string, payload: Record<string, unknown> = {}, itemId?: string | null) {
    const view = await postEvent(params.id, event_type, payload, itemId ?? action?.item_id);
    const next = view.action;
    if (event_type === "idle_nudge" && next.type === "nudge" && action) {
      setNudge(false);
      armTimers(action);
      return;
    }
    setAction(next);
    setAnswer("");
    setStep(1);
    if (event_type === "answer" && next.type === "hint") {
      setWrongOnce(true);
      setHintReady(true);
    }
    if (next.type === "similar_item" || next.type === "show_item") {
      setWrongOnce(false);
      setHintReady(false);
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

  const item = action.item;
  const mcq = item?.type === "mcq";
  const extras = (action.extras ?? {}) as Record<string, unknown>;
  const praise = (extras.encouragement as { text?: string | null } | undefined)?.text;
  const testOut = (action.extras as { test_out?: { index: number; of: number } } | undefined)?.test_out;

  return (
    <main className="stack column">
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
          {mcq ? (
            <Mcq options={item?.options || []} onPick={(id) => send("answer", { response: id, latency_ms: 500 })} />
          ) : (
            <AnswerForm
              value={answer}
              onChange={setAnswer}
              label={copy.answerPlaceholder}
              submit={copy.submit}
              onSubmit={() => send("answer", { response: answer, latency_ms: 500 })}
            />
          )}
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
          <p className="stem">{action.text || item?.prediction}</p>
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
            {(item?.steps || []).slice(0, step).map((row) => (
              <li key={row}>{row}</li>
            ))}
          </ol>
          <SourceChips sources={action.sources} label={copy.sourceLabel} />
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
          <p className="stem">{item?.stem}</p>
          {extras.kind === "restate" || extras.kind === "step" ? (
            <p className="muted">{extras.kind === "restate" ? copy.hintRestateLabel : copy.hintStepLabel}</p>
          ) : null}
          <p className="banner" data-testid="hint-text">{action.text}</p>
          {mcq ? (
            <Mcq options={item?.options || []} onPick={(id) => send("answer", { response: id, latency_ms: 500 })} />
          ) : (
            <AnswerForm
              value={answer}
              onChange={setAnswer}
              label={copy.answerPlaceholder}
              submit={copy.submit}
              onSubmit={() => send("answer", { response: answer, latency_ms: 500 })}
            />
          )}
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

      {action.type === "reveal_solution" ? (
        <>
          <h1>{copy.reveal}</h1>
          <p className="stem">{item?.stem}</p>
          <p className="math">{item?.answer || action.text}</p>
          <ol className="steps">
            {(item?.steps || []).map((row) => (
              <li key={row}>{row}</li>
            ))}
          </ol>
          <SourceChips sources={action.sources} label={copy.sourceLabel} />
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
          <p className="stem">{item?.stem}</p>
          <ReadAloud text={item?.stem || ""} lang={activeLocale} ui={ui} />
          {mcq ? (
            <Mcq options={item?.options || []} onPick={(id) => send("answer", { response: id, latency_ms: 400 })} />
          ) : (
            <AnswerForm
              value={answer}
              onChange={setAnswer}
              label={copy.answerPlaceholder}
              submit={copy.submit}
              onSubmit={() => send("answer", { response: answer, latency_ms: 400 })}
            />
          )}
          {action.dont_know_option ? (
            <button
              type="button"
              className="ghost"
              onClick={() => send("answer", { response: "i don't know", latency_ms: 200 })}
            >
              {copy.dontKnow}
            </button>
          ) : null}
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
          <p className={action.correct ? "fb ok" : "fb try"} role="status" data-testid="feedback">
            {action.correct ? copy.feedbackCorrect : copy.feedbackWrong}
          </p>
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
