"use client";

import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { explainChat, type TutorFallback, type TutorTurn } from "@/lib/api";
import { useCopy } from "@/lib/locale";

/** The tutor keeps only the last few turns, and so does this box: nothing is stored anywhere. */
const MAX_TURNS = 8;

/**
 * Follow-up questions about the lesson just finished, answered one short Socratic reply at a time. The
 * conversation lives in this component only; closing the lesson drops it, like the question itself.
 */
export function AskAbout({ prompt, language, onPractice }: { prompt: string; language: "en" | "hi"; onPractice?: () => void }) {
  const copy = useCopy();
  const [turns, setTurns] = useState<TutorTurn[]>([]);
  // The choices under Brownie's last "I can't answer that" line; gone as soon as the learner moves on.
  const [offers, setOffers] = useState<TutorFallback["offers"]>([]);
  const lastQuestion = useRef("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function send() {
    const question = text.trim();
    if (!question || busy) return;
    // The tutor needs to know what the lesson was about: the original question always leads the history.
    const history: TutorTurn[] = [{ role: "user", content: prompt.slice(0, 500) }, ...turns.slice(-(MAX_TURNS - 1))];
    lastQuestion.current = question;
    setTurns((prev) => [...prev, { role: "user", content: question }]);
    setText("");
    setBusy(true);
    setFailed(false);
    setOffers([]);
    try {
      const reply = await explainChat(question, language, history);
      const answer =
        reply.kind === "reply"
          ? reply.text
          : reply.kind === "unavailable"
            ? (reply.fallback?.text ?? null)
            : "message" in reply
              ? reply.message
              : null;
      if (answer) setTurns((prev) => [...prev, { role: "assistant", content: answer }]);
      else setFailed(true);
      // Only a choice that can be acted on here is shown: practice needs the chat to start it.
      if (reply.kind === "unavailable" && reply.fallback) setOffers(reply.fallback.offers.filter((o) => o.id !== "practice" || onPractice));
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
      inputRef.current?.focus();
    }
  }

  /** A choice under a fallback line. Only ids this client knows do anything; any other is ignored. */
  function choose(id: string) {
    setOffers([]);
    if (id === "ask_again") {
      setText(lastQuestion.current);
      inputRef.current?.focus();
    } else if (id === "practice") {
      onPractice?.();
    }
  }

  return (
    <section className="flex flex-col gap-3 border-0 border-t border-line pt-6" aria-labelledby="ask-about-title" data-testid="ask-about">
      <h2 id="ask-about-title" className="m-0 text-[1.0625rem] font-medium text-ink">
        {copy.lessonAskAbout}
      </h2>
      {turns.length > 0 ? (
        <ul className="m-0 flex list-none flex-col gap-2 p-0" aria-live="polite">
          {turns.map((turn, i) => (
            <li
              key={i}
              data-testid={turn.role === "user" ? "ask-about-you" : "ask-about-tutor"}
              className={`max-w-[90%] rounded-2xl px-4 py-2.5 text-[0.9375rem] leading-[1.6] text-ink ${turn.role === "user" ? "self-end bg-accent-soft" : "self-start bg-surface-2"}`}
            >
              {turn.content}
            </li>
          ))}
          {busy ? <li className="self-start text-[0.8125rem] text-muted">{copy.lessonTutorThinking}</li> : null}
        </ul>
      ) : null}
      {offers.length > 0 ? (
        <div className="flex flex-wrap gap-2" data-testid="ask-about-offers">
          {offers.map((offer) => (
            <Button key={offer.id} type="button" variant="secondary" onClick={() => choose(offer.id)} data-testid={`offer-${offer.id}`}>
              {offer.label}
            </Button>
          ))}
        </div>
      ) : null}
      {failed ? (
        <p className="m-0 text-[0.875rem] text-warning" role="alert">
          {copy.lessonTutorFailed}
        </p>
      ) : null}
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
      >
        <input
          ref={inputRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={500}
          placeholder={copy.lessonAskAboutPlaceholder}
          aria-label={copy.lessonAskAboutPlaceholder}
          autoComplete="off"
          className="min-h-12 min-w-0 flex-1 rounded-xl border border-line bg-surface px-4 font-[inherit] text-[0.9375rem] text-ink outline-none focus:border-accent"
          data-testid="ask-about-input"
        />
        <Button type="submit" disabled={busy || !text.trim()}>
          {copy.lessonAskAboutSend}
        </Button>
      </form>
    </section>
  );
}
