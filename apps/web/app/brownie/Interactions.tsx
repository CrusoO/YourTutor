"use client";

import { useEffect, useRef, useState, type ChangeEvent, type DragEvent, type FormEvent } from "react";
import { landingContent, type LandingLanguage, type LevelId, type StyleId } from "./content";
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

export function BrownieQuestion() {
  const { copy } = useLandingLanguage();
  const [level, setLevel] = useState<LevelId>("new");
  const [style, setStyle] = useState<StyleId>("picture");
  const firstReply = copy.chapterTwo.firstReplies[level];
  const explanation = copy.chapterTwo.explanations[style];

  return (
    <section className={styles.questionPanel} aria-label={copy.chapterTwo.questionAria}>
      <p className={styles.panelLabel}>{copy.chapterTwo.problemLabel}</p>
      <p className={styles.problem}>{copy.chapterTwo.problem}</p>

      <fieldset className={styles.choiceGroup}>
        <legend>{copy.chapterTwo.levelQuestion}</legend>
        <div className={styles.choiceRow}>
          {copy.chapterTwo.levels.map((option) => (
            <button
              key={option.id}
              type="button"
              aria-pressed={level === option.id}
              className={`${styles.choice} ${level === option.id ? styles.choiceSelected : ""}`}
              onClick={() => setLevel(option.id)}
            >
              {option.label}
            </button>
          ))}
        </div>
      </fieldset>

      <fieldset className={styles.choiceGroup}>
        <legend>{copy.chapterTwo.styleQuestion}</legend>
        <div className={styles.choiceRow}>
          {copy.chapterTwo.styles.map((option) => (
            <button
              key={option.id}
              type="button"
              aria-pressed={style === option.id}
              className={`${styles.choice} ${style === option.id ? styles.choiceSelected : ""}`}
              onClick={() => setStyle(option.id)}
            >
              {option.label}
            </button>
          ))}
        </div>
      </fieldset>

      <div className={styles.readout} aria-live="polite" aria-atomic="true">
        <p className={styles.readLabel}>{copy.chapterTwo.firstReplyLabel}</p>
        <p className={styles.readBody}>{firstReply}</p>
        <p className={`${styles.readLabel} ${styles.explanationReadLabel}`}>{copy.chapterTwo.explanationLabel}</p>
        <p className={styles.readBody}>{explanation}</p>
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