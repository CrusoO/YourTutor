"use client";

import { useEffect, useRef, useState } from "react";
import { ask, guess, notesFor, pickedChoice, remaining, START, type DemoState } from "./chat-demo";
import {
  chatScenarios,
  chatUi,
  comingSoon,
  howItWorks,
  learningMap,
  trust,
  videoDemos,
  videoUi,
  type NoteState,
} from "./landing-extras";
import { useSeen } from "./StoryArt";
import styles from "./BrownieLanding.module.css";
import x from "./LandingExtras.module.css";

const STATE_CLASS: Record<NoteState | "unseen", string> = {
  solid: x.stateSolid!,
  shaky: x.stateShaky!,
  tried: x.stateTried!,
  unseen: x.stateUnseen!,
};

function StateChip({ state, label }: { state: NoteState | "unseen"; label: string }) {
  return <span className={`${x.stateChip} ${STATE_CLASS[state]}`}>{label}</span>;
}

/**
 * The sample chat for English: Brownie asks one question first, a wrong guess is shown as useful, and a side
 * card shows what Brownie wrote down. Scripted and labelled as such; nothing here is sent or saved.
 */
export function GuessChat() {
  const [scenarioId, setScenarioId] = useState(chatScenarios[0]!.id);
  const [state, setState] = useState<DemoState>(START);
  const latest = useRef<HTMLDivElement>(null);
  const scenario = chatScenarios.find((s) => s.id === scenarioId) ?? chatScenarios[0]!;
  const choice = pickedChoice(scenario, state);
  const notes = notesFor(scenario, state);
  const left = remaining(scenario, state);
  const moves = (choice ? 1 : 0) + state.asked.length;

  useEffect(() => {
    if (moves === 0) return;
    latest.current?.scrollIntoView?.({
      behavior: window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
      block: "nearest",
    });
  }, [moves]);

  const choose = (id: string) => {
    setScenarioId(id);
    setState(START);
  };

  return (
    <section className={`${styles.questionPanel} ${styles.demoChat}`} aria-label="A scripted sample conversation" data-testid="demo-chat">
      <header className={styles.demoChatHeader}>
        <p className={styles.panelLabel}>A SAMPLE CHAT · SCRIPTED</p>
        <p className={styles.demoDisclosure} data-testid="demo-disclosure">
          A scripted preview. Brownie is not responding live here.
        </p>
      </header>

      <div>
        <p className={x.pickerLabel}>{chatUi.pickTopic}</p>
        <div className={x.tabRow} role="group" aria-label={chatUi.pickTopic}>
          {chatScenarios.map((s) => (
            <button
              key={s.id}
              type="button"
              aria-pressed={s.id === scenario.id}
              className={`${x.tab} ${s.id === scenario.id ? x.tabOn : ""}`}
              onClick={() => choose(s.id)}
              data-testid={`demo-scenario-${s.id}`}
            >
              {s.tab}
            </button>
          ))}
        </div>
      </div>

      <div className={x.chatGrid}>
        <div className={`${styles.demoConversation} ${x.chatTranscript}`} aria-live="polite">
          <div className={`${styles.demoMessage} ${styles.demoMessageUser}`}>
            <span className={styles.demoSpeaker}>You</span>
            <p className={styles.demoBubble}>{scenario.studentQuestion}</p>
          </div>

          <div className={styles.demoMessage} data-testid="demo-opening">
            <span className={styles.demoSpeaker}>Brownie</span>
            <div className={`${styles.demoBubble} ${styles.demoBubbleTutor}`}>
              <p>{scenario.opening}</p>
              <p data-testid="demo-diagnostic" style={{ marginTop: 10 }}>
                <strong>{scenario.diagnostic.prompt}</strong>
              </p>
              {choice === null ? (
                <div className={x.choiceStack}>
                  {scenario.diagnostic.choices.map((c) => (
                    <button
                      key={c.id}
                      type="button"
                      className={x.choiceWide}
                      onClick={() => setState((s) => guess(s, c.id))}
                      data-testid={`demo-choice-${c.id}`}
                    >
                      {c.text}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
          </div>

          {choice ? (
            <>
              <div className={`${styles.demoMessage} ${styles.demoMessageUser}`}>
                <span className={styles.demoSpeaker}>You</span>
                <p className={styles.demoBubble}>{choice.text}</p>
              </div>
              <div className={styles.demoMessage} data-testid="demo-reply" ref={state.asked.length === 0 ? latest : undefined}>
                <span className={styles.demoSpeaker}>Brownie</span>
                <div className={`${styles.demoBubble} ${styles.demoBubbleTutor}`}>
                  {choice.correct ? null : (
                    <span className={x.slipTag} data-testid="demo-misconception">
                      The idea that slipped
                    </span>
                  )}
                  <p>{choice.reply}</p>
                </div>
              </div>
            </>
          ) : null}

          {state.asked.map((id, index) => {
            const explanation = scenario.explanations.find((e) => e.id === id)!;
            return (
              <div className={styles.demoReply} key={id} ref={index === state.asked.length - 1 ? latest : undefined}>
                <div className={`${styles.demoMessage} ${styles.demoMessageUser}`}>
                  <span className={styles.demoSpeaker}>You</span>
                  <p className={styles.demoBubble}>{explanation.user}</p>
                </div>
                <div className={styles.demoMessage} data-testid={`demo-follow-up-${id}`}>
                  <span className={styles.demoSpeaker}>Brownie</span>
                  <div className={`${styles.demoBubble} ${styles.demoBubbleTutor}`}>
                    <p>{explanation.text}</p>
                    {explanation.drawing === "pieces" ? (
                      <div className={styles.fractionDiagram}>
                        <div
                          className={styles.fractionPieces}
                          aria-label="Six equal pieces: three from one half, two from one third"
                          data-testid="fraction-pieces"
                        >
                          {Array.from({ length: 6 }, (_, i) => (
                            <span key={i} aria-hidden="true" className={i < 3 ? styles.fractionHalf : i < 5 ? styles.fractionThird : styles.fractionEmpty} />
                          ))}
                        </div>
                        <div className={styles.fractionLegend}>
                          <span>3/6 (one half)</span>
                          <span>2/6 (one third)</span>
                        </div>
                      </div>
                    ) : null}
                  </div>
                </div>
              </div>
            );
          })}

          {choice ? (
            <div className={styles.demoChatActions}>
              {left.length > 0 ? <p>{chatUi.askNext}</p> : null}
              <div className={styles.choiceRow}>
                {left.map((e) => (
                  <button key={e.id} type="button" className={styles.choice} onClick={() => setState((s) => ask(s, e.id))} data-testid={`demo-ask-${e.id}`}>
                    {e.choice}
                  </button>
                ))}
                <button type="button" className={styles.demoRestart} onClick={() => setState(START)} data-testid="demo-restart">
                  Start over
                </button>
              </div>
              {left.length === 0 ? (
                <a className={x.tryOwn} href="/brownie-chat" data-testid="demo-try-own">
                  {chatUi.tryOwn} →
                </a>
              ) : null}
            </div>
          ) : null}
        </div>

        <aside className={x.noteCard} aria-label={chatUi.noteTitle} data-testid="demo-notes">
          <p className={x.noteTitle}>{chatUi.noteTitle}</p>
          {notes.length === 0 ? (
            <p className={x.noteHelp}>{chatUi.noteEmpty}</p>
          ) : (
            <ul className={x.noteList} aria-live="polite">
              {notes.map((note, i) => (
                <li key={note.label} className={x.noteItem} data-testid={`demo-note-${i}`}>
                  <span className={x.noteLabel}>
                    <StateChip state={note.state} label={chatUi.stateLabels[note.state]} />
                    {note.label}
                  </span>
                  <span className={x.noteEvidence}>{note.evidence}</span>
                </li>
              ))}
            </ul>
          )}
          <p className={x.noteHelp}>{chatUi.noteHelp}</p>
        </aside>
      </div>
    </section>
  );
}

/** What Brownie has seen, as a state plus the evidence behind it. Never a probability. */
export function LearningMapView() {
  const [ref, seen] = useSeen<HTMLOListElement>();
  return (
    <>
      <ol ref={ref} className={x.mapList} aria-label={learningMap.aria} data-seen={seen} data-testid="learning-map">
        {learningMap.topics.map((topic) => (
          <li key={topic.id} className={x.mapRow}>
            <span className={x.mapName}>{topic.name}</span>
            <span>
              <StateChip state={topic.state} label={learningMap.states[topic.state]} />
            </span>
            <span className={x.mapEvidence}>{topic.evidence}</span>
          </li>
        ))}
      </ol>
      <p className={x.mapCaveat}>{learningMap.caveat}</p>
    </>
  );
}

/** Three example videos. A tab appears only when its video exists, so the page never shows an empty player. */
export function VideoDemos() {
  const ready = videoDemos.filter((v) => v.src);
  const [activeId, setActiveId] = useState(ready[0]?.id ?? "");
  const active = ready.find((v) => v.id === activeId) ?? ready[0];

  if (!active) {
    return (
      <p className={x.videoSoon} data-testid="video-soon">
        {videoUi.soon}
      </p>
    );
  }
  return (
    <div className={x.videoStage} data-testid="video-demos">
      {ready.length > 1 ? (
        <div className={x.tabRow} role="group" aria-label={videoUi.tabs}>
          {ready.map((v) => (
            <button
              key={v.id}
              type="button"
              aria-pressed={v.id === active.id}
              className={`${x.tab} ${v.id === active.id ? x.tabOn : ""}`}
              onClick={() => setActiveId(v.id)}
              data-testid={`video-tab-${v.id}`}
            >
              {v.tab}
            </button>
          ))}
        </div>
      ) : null}
      <video key={active.id} className={x.videoFrame} controls playsInline preload="metadata" poster={active.poster || undefined} src={active.src} aria-label={active.title}>
        {active.captions ? <track kind="captions" src={active.captions} srcLang="en" label="English" default /> : null}
      </video>
      <div className={x.videoMeta}>
        <span className={x.videoTitle}>{active.title}</span>
        {active.length ? <span>{active.length}</span> : null}
      </div>
      <p className={x.noteEvidence}>{active.summary}</p>
      {active.transcript ? (
        <details className={x.transcript}>
          <summary>{videoUi.transcript}</summary>
          <p>{active.transcript}</p>
        </details>
      ) : null}
      <p className={x.noteHelp}>{videoUi.disclosure}</p>
    </div>
  );
}

/** What Brownie looks at and what it does with it, step by step, so the promise "finds out first" can be checked. */
export function HowItWorks() {
  return (
    <section className={x.howSection} aria-labelledby="how-title" data-testid="how-it-works">
      <h2 id="how-title" className={x.trustTitle}>
        {howItWorks.title}
      </h2>
      <p className={x.trustIntro}>{howItWorks.intro}</p>
      <ol className={x.howSteps}>
        {howItWorks.steps.map((step, index) => (
          <li key={step.id} className={x.howStep} data-testid={`how-${step.id}`}>
            <span className={x.howNumber} aria-hidden="true">
              {index + 1}
            </span>
            <div>
              <h3>{step.title}</h3>
              <p>{step.body}</p>
            </div>
          </li>
        ))}
      </ol>
      <p className={x.noteHelp}>{howItWorks.limits}</p>
    </section>
  );
}

/** What is not here yet, with an apology for the language gap. */
export function ComingSoon() {
  return (
    <section className={x.trustSection} aria-labelledby="soon-title" data-testid="coming-soon">
      <h2 id="soon-title" className={x.trustTitle}>
        {comingSoon.title}
      </h2>
      <p className={x.trustIntro}>{comingSoon.apology}</p>
      <ul className={x.soonList}>
        {comingSoon.items.map((item) => (
          <li key={item.id} data-testid={`soon-${item.id}`}>
            <h3>{item.title}</h3>
            <p>{item.body}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Plain answers to the doubts a visitor has. */
export function TrustStrip() {
  return (
    <section className={x.trustSection} aria-labelledby="trust-title" data-testid="trust">
      <h2 id="trust-title" className={x.trustTitle}>
        {trust.title}
      </h2>
      <p className={x.trustIntro}>{trust.intro}</p>
      <ul className={x.trustList}>
        {trust.items.map((item) => (
          <li key={item.id} className={x.trustRow}>
            <details className={x.trustItem} data-testid={`trust-${item.id}`}>
              <summary>
                <span>{item.q}</span>
              </summary>
              <p>{item.a}</p>
            </details>
          </li>
        ))}
      </ul>
    </section>
  );
}
