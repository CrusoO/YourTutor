"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getSession, locale, postEvent, type ActionPayload } from "@/lib/api";
import { t } from "@/lib/messages";
import { hintDelayMs, idleNudgeMs } from "@/lib/session-timers";

export default function SessionPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const copy = t(locale());
  const [action, setAction] = useState<ActionPayload | null>(null);
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
    if (next.type === "show_item" && (next.can_request_hint ?? next.allow_hint)) {
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
    load().catch(() => router.push("/login"));
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
    armTimers(next);
  }

  if (!action) return <p>…</p>;

  if (action.type === "end_session" || action.type === "checkpoint_score") {
    return (
      <main className="stack">
        <h1>{copy.done}</h1>
        <p>{action.ended_reason || action.reason || action.type}</p>
        {action.extras && action.type === "checkpoint_score" ? (
          <p>Score: {String((action.extras as { score?: number }).score ?? "")}</p>
        ) : null}
        <button type="button" onClick={() => router.push("/today")}>
          {copy.backToday}
        </button>
      </main>
    );
  }

  const item = action.item;
  const mcq = item?.type === "mcq";

  return (
    <main className="stack">
      <p className="muted">{action.session_type}</p>
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
          <h1>{item?.stem || action.text}</h1>
          <ol className="steps">
            {(item?.steps || []).slice(0, step).map((row) => (
              <li key={row}>{row}</li>
            ))}
          </ol>
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
          <p className="banner">{action.text}</p>
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
          <button type="button" onClick={() => send("continue")}>
            {copy.similar}
          </button>
        </>
      ) : null}

      {action.type === "similar_item" || action.type === "show_item" || action.type === "warmup_item" ? (
        <>
          <p className="stem">{item?.stem}</p>
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
          {(action.can_request_hint ?? action.allow_hint) && hintReady ? (
            <button type="button" className="secondary" onClick={() => send("request_hint")}>
              {copy.hint}
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
          <p className="banner">{action.correct ? copy.feedbackCorrect : copy.feedbackWrong}</p>
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
