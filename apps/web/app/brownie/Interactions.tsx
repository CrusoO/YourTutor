"use client";

import { useEffect, useRef, useState, type ChangeEvent, type DragEvent, type FormEvent } from "react";
import { landingContent, type LandingLanguage } from "./content";
import { useLandingLanguage } from "./LandingLanguage";
import styles from "./BrownieLanding.module.css";

// Set to a path under /public or a public URL to show a permanent demo. Local selections are never uploaded.
const DEMO_VIDEO_SRC = "";
const DEMO_VIDEO_POSTER = "";

export function LandingLanguages() {
  const { language, setLanguage, copy } = useLandingLanguage();

  return (
    <div className={styles.languageBlock}>
      <div className={styles.languageSwitch} role="group" aria-label={copy.hero.languageLabel}>
        {copy.hero.languageOptions.map((option) => (
          <button
            key={option.id}
            type="button"
            lang={option.id}
            aria-pressed={language === option.id}
            className={styles.languageOption}
            onClick={() => setLanguage(option.id as LandingLanguage)}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}

type DemoReply = "picture" | "steps";

export function BrownieChatDemo() {
  const { copy } = useLandingLanguage();
  const [replies, setReplies] = useState<DemoReply[]>([]);
  const latestReply = useRef<HTMLDivElement>(null);
  const chat = copy.chapterTwo.demoChat;

  useEffect(() => {
    if (replies.length === 0) return;
    latestReply.current?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
      block: "nearest",
    });
  }, [replies.length]);

  return (
    <section
      className={`${styles.questionPanel} ${styles.demoChat}`}
      aria-label={copy.chapterTwo.questionAria}
      data-testid="demo-chat"
    >
      <header className={styles.demoChatHeader}>
        <p className={styles.panelLabel}>{chat.label}</p>
        <p className={styles.demoDisclosure} data-testid="demo-disclosure">{chat.disclosure}</p>
      </header>

      <div className={styles.demoConversation} aria-live="polite">
        <div className={`${styles.demoMessage} ${styles.demoMessageUser}`}>
          <span className={styles.demoSpeaker}>{chat.studentLabel}</span>
          <p className={styles.demoBubble}>{chat.studentQuestion}</p>
        </div>
        <div className={styles.demoMessage} data-testid="demo-opening">
          <span className={styles.demoSpeaker}>{chat.tutorLabel}</span>
          <p className={`${styles.demoBubble} ${styles.demoBubbleTutor}`}>{chat.brownieOpening}</p>
        </div>

        {replies.map((reply, index) => (
          <div
            className={styles.demoReply}
            key={reply}
            ref={index === replies.length - 1 ? latestReply : undefined}
          >
            <div className={`${styles.demoMessage} ${styles.demoMessageUser}`}>
              <span className={styles.demoSpeaker}>{chat.studentLabel}</span>
              <p className={styles.demoBubble}>
                {reply === "picture" ? chat.pictureUser : chat.stepsUser}
              </p>
            </div>
            <div className={styles.demoMessage} data-testid={`demo-follow-up-${reply}`}>
              <span className={styles.demoSpeaker}>{chat.tutorLabel}</span>
              <div className={`${styles.demoBubble} ${styles.demoBubbleTutor}`}>
                <p>{reply === "picture" ? chat.pictureExplanation : chat.stepsExplanation}</p>
                {reply === "picture" ? (
                  <div className={styles.fractionDiagram}>
                    <div className={styles.fractionPieces} aria-label={chat.piecesAria} data-testid="fraction-pieces">
                      {Array.from({ length: 6 }, (_, index) => (
                        <span
                          key={index}
                          aria-hidden="true"
                          className={
                            index < 3
                              ? styles.fractionHalf
                              : index < 5
                                ? styles.fractionThird
                                : styles.fractionEmpty
                          }
                        />
                      ))}
                    </div>
                    <div className={styles.fractionLegend}>
                      <span>{chat.halfLegend}</span>
                      <span>{chat.thirdLegend}</span>
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className={styles.demoChatActions}>
        {replies.length < 2 ? <p>{chat.followUpPrompt}</p> : null}
        <div className={styles.choiceRow}>
          {!replies.includes("picture") ? (
            <button type="button" className={styles.choice} onClick={() => setReplies((current) => [...current, "picture"])}>
              {chat.pictureChoice}
            </button>
          ) : null}
          {!replies.includes("steps") ? (
            <button type="button" className={styles.choice} onClick={() => setReplies((current) => [...current, "steps"])}>
              {chat.stepsChoice}
            </button>
          ) : null}
          {replies.length > 0 ? (
            <button type="button" className={styles.demoRestart} onClick={() => setReplies([])}>
              {chat.restart}
            </button>
          ) : null}
        </div>
      </div>
    </section>
  );
}

export function MasteryChart() {
  const { copy } = useLandingLanguage();
  const chartRef = useRef<HTMLOListElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = chartRef.current;
    if (!node) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches || !("IntersectionObserver" in window)) {
      setVisible(true);
      return;
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.24 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <ol
      ref={chartRef}
      className={styles.masteryChart}
      aria-label={copy.chapterThree.chartAria}
      data-visible={visible}
    >
      {copy.chapterThree.topics.map((topic) => (
        <li key={topic.id} className={styles.masteryItem}>
          <div className={styles.masteryValue}>
            {topic.percent}<span>%</span>
          </div>
          <p className={styles.masteryName}>{topic.name}</p>
          <div
            className={styles.masteryTrack}
            role="meter"
            aria-label={topic.name}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={topic.percent}
          >
            <span
              className={`${styles.masteryBar} ${topic.id === "quadratic" ? styles.masteryBarHighlight : ""}`}
              style={{ height: `${topic.percent}%` }}
            />
          </div>
        </li>
      ))}
    </ol>
  );
}

type LocalVideo = { src: string; name: string; size: number };

function videoFromFile(file: File): LocalVideo | null {
  if (!file.type.startsWith("video/")) return null;
  return { src: URL.createObjectURL(file), name: file.name, size: file.size };
}

function displaySize(size: number): string {
  if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export function DemoVideo() {
  const { copy } = useLandingLanguage();
  const inputRef = useRef<HTMLInputElement>(null);
  const currentUrl = useRef<string | null>(null);
  const [localVideo, setLocalVideo] = useState<LocalVideo | null>(null);
  const [dragging, setDragging] = useState(false);
  const [fileError, setFileError] = useState(false);

  useEffect(() => () => {
    if (currentUrl.current) URL.revokeObjectURL(currentUrl.current);
  }, []);

  const selectFile = (file?: File) => {
    if (!file) return;
    const next = videoFromFile(file);
    if (!next) {
      setFileError(true);
      return;
    }
    if (currentUrl.current) URL.revokeObjectURL(currentUrl.current);
    currentUrl.current = next.src;
    setLocalVideo(next);
    setFileError(false);
  };

  const onChange = (event: ChangeEvent<HTMLInputElement>) => selectFile(event.target.files?.[0]);
  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    selectFile(event.dataTransfer.files[0]);
  };

  if (DEMO_VIDEO_SRC) {
    return (
      <video
        className={styles.video}
        controls
        playsInline
        preload="metadata"
        poster={DEMO_VIDEO_POSTER || undefined}
        src={DEMO_VIDEO_SRC}
        aria-label={copy.demo.playerAria}
      />
    );
  }

  if (localVideo) {
    return (
      <div className={styles.videoPreview}>
        <video
          className={styles.video}
          controls
          playsInline
          preload="metadata"
          src={localVideo.src}
          aria-label={copy.demo.playerAria}
        />
        <div className={styles.videoFileRow}>
          <p title={localVideo.name}>{localVideo.name} <span>{displaySize(localVideo.size)}</span></p>
          <button type="button" className={styles.videoReplace} onClick={() => inputRef.current?.click()}>
            {copy.demo.replace}
          </button>
        </div>
        {fileError ? <p className={styles.fileError} role="alert">{copy.demo.invalidFile}</p> : null}
        <input ref={inputRef} className={styles.srOnly} type="file" accept="video/*" onChange={onChange} aria-label={copy.demo.fileAria} aria-hidden="true" tabIndex={-1} />
      </div>
    );
  }

  return (
    <div
      role="group"
      aria-label={copy.demo.dropAria}
      onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
    >
      <input ref={inputRef} className={styles.srOnly} type="file" accept="video/*" onChange={onChange} aria-label={copy.demo.fileAria} aria-hidden="true" tabIndex={-1} />
      <button
        type="button"
        className={`${styles.dropZone} ${dragging ? styles.dropZoneActive : ""}`}
        aria-label={copy.demo.dropAria}
        onClick={() => inputRef.current?.click()}
      >
        <p className={styles.dropTitle}>{copy.demo.dropTitle} <em>{copy.demo.dropAccent}</em></p>
        <p className={styles.dropHint}>{copy.demo.dropHint}</p>
        <span className={styles.videoChoose}>{copy.demo.choose}</span>
        {fileError ? <p className={styles.fileError} role="alert">{copy.demo.invalidFile}</p> : null}
      </button>
    </div>
  );
}

type FeedbackCategory = (typeof landingContent.feedback.categories)[number]["id"];

export function BrownieFeedback() {
  const { copy } = useLandingLanguage();
  const [category, setCategory] = useState<FeedbackCategory | null>(null);
  const [message, setMessage] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const feedback = copy.feedback;

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!category && !message.trim()) return;
    setSubmitted(true);
  };

  return (
    <section className={styles.feedbackSection} aria-labelledby="feedback-title">
      <div className={styles.feedbackIntro}>
        <h2 id="feedback-title">{feedback.headlineStart} <em>{feedback.headlineEmphasis}</em></h2>
        <p>{feedback.intro}</p>
      </div>
      <form className={styles.feedbackForm} onSubmit={submit}>
        <fieldset className={styles.feedbackChoices}>
          <legend>{feedback.categoryLabel}</legend>
          <div className={styles.feedbackChoiceRow}>
            {feedback.categories.map((option) => (
              <button
                key={option.id}
                type="button"
                aria-pressed={category === option.id}
                className={`${styles.feedbackChoice} ${category === option.id ? styles.feedbackChoiceSelected : ""}`}
                onClick={() => { setCategory(category === option.id ? null : option.id); setSubmitted(false); }}
              >
                {option.label}
              </button>
            ))}
          </div>
        </fieldset>
        <label className={styles.feedbackMessageLabel} htmlFor="brownie-feedback-message">{feedback.messageLabel}</label>
        <textarea
          id="brownie-feedback-message"
          className={styles.feedbackTextarea}
          maxLength={1000}
          placeholder={feedback.placeholder}
          value={message}
          onChange={(event) => { setMessage(event.target.value); setSubmitted(false); }}
        />
        <div className={styles.feedbackActions}>
          <p>{feedback.localNote}</p>
          <button className={styles.feedbackSubmit} type="submit" disabled={!category && !message.trim()}>{feedback.submit}</button>
        </div>
        {submitted ? <p className={styles.feedbackThanks} role="status" aria-live="polite">{feedback.thanks}</p> : null}
      </form>
    </section>
  );
}