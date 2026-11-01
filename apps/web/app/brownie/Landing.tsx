"use client";

import { useEffect, useState } from "react";
import { Instrument_Serif, Inter, Noto_Serif_Devanagari } from "next/font/google";
import {
  BrownieChatDemo,
  BrownieFeedback,
  DemoVideo,
  LandingLanguages,
  MasteryChart,
} from "./Interactions";
import { LandingLanguageProvider, useLandingLanguage } from "./LandingLanguage";
import styles from "./BrownieLanding.module.css";

const instrument = Instrument_Serif({
  weight: "400",
  style: ["normal", "italic"],
  subsets: ["latin"],
  display: "swap",
  variable: "--font-instrument-serif",
});

const inter = Inter({
  weight: ["400", "500"],
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

const notoSerifDevanagari = Noto_Serif_Devanagari({
  weight: ["400", "500"],
  subsets: ["devanagari"],
  display: "swap",
  variable: "--font-noto-serif-deva",
});

function LandingPageContent() {
  const { language, copy } = useLandingLanguage();
  const [audienceIndex, setAudienceIndex] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setAudienceIndex((index) => (index + 1) % copy.hero.audiences.length);
    }, 3200);
    return () => window.clearInterval(timer);
  }, [copy.hero.audiences.length]);

  useEffect(() => setAudienceIndex(0), [language]);

  return (
    <main
      className={`${styles.landing} ${instrument.variable} ${inter.variable} ${notoSerifDevanagari.variable}`}
      aria-label={copy.accessibility.main}
      lang={language}
      data-testid="brownie-landing"
    >
      <header id="top" className={styles.hero}>
        <nav className={styles.heroTop} aria-label={copy.accessibility.main}>
          <a className={styles.heroBrand} href="/" aria-label={copy.hero.homepage}>
            {copy.hero.topLabel}
          </a>
          <div className={styles.heroTopRight}>
            <a className={styles.signInLink} href={`/login?lang=${language}`}>{copy.hero.signIn}</a>
            <LandingLanguages />
          </div>
        </nav>

        <div className={styles.heroLayout}>
          <h1 className={styles.wordmark} data-testid="landing-wordmark">
            <span className={styles.askWord}>{copy.hero.ask}</span>
            <span className={styles.brownieWord}>{copy.hero.name}</span>
          </h1>
          <div className={styles.heroCopy} data-testid="landing-hero-copy">
            <h2 className={styles.audienceLine}>
              <span>{copy.hero.audienceLead}</span>
              <span className={styles.audienceWords} aria-live="polite" data-testid="audience-words" data-active-index={audienceIndex}>
                {copy.hero.audiences.map((audience, index) => (
                  <span
                    key={audience}
                    className={index === audienceIndex ? styles.audienceCurrent : styles.audienceHidden}
                    aria-hidden={index !== audienceIndex}
                  >
                    {audience}
                  </span>
                ))}
              </span>
            </h2>
            <p className={styles.heroTagline}>{copy.hero.tagline}</p>
            <p className={styles.heroDescription}>{copy.hero.description}</p>
            <div className={styles.actions}>
              <a className={styles.primaryButton} href="/brownie-chat">{copy.hero.tryBrownie}</a>
              <a className={styles.ghostButton} href="#chapter-one">{copy.hero.readStory}</a>
            </div>
            <div className={styles.exploreMessage}>
              <p>{copy.hero.explore}</p>
              <span>{copy.hero.exploreNote}</span>
            </div>
          </div>
        </div>
      </header>

      <section className={`${styles.section} ${styles.hook}`} aria-labelledby="hook-title">
        <h2 id="hook-title">
          {copy.hook.firstLine}<br />
          <em>{copy.hook.secondLine}</em>
        </h2>
        <p>{copy.hook.body}</p>
        <div className={styles.actions}>
          <a className={styles.primaryButton} href="#chapter-two">{copy.hook.seeHow}</a>
          <a className={styles.ghostButton} href="#demo">{copy.hook.watchDemo}</a>
        </div>
      </section>

      <div className={styles.story} aria-label={copy.accessibility.chapters}>
        <section id="chapter-one" className={styles.chapter} aria-labelledby="chapter-one-title">
          <div className={styles.chapterMarker}>
            <p>{copy.chapterOne.chapter}</p>
            <span>{copy.chapterOne.label}</span>
          </div>
          <div className={styles.chapterContent}>
            <p className={styles.storyHook}>{copy.chapterOne.hook}</p>
            <h2 id="chapter-one-title">{copy.chapterOne.headline}</h2>
            {copy.chapterOne.paragraphs.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
            <p className={styles.storyInvitation}>{copy.chapterOne.invitation}</p>
            <p className={styles.storyStats}>{copy.chapterOne.stats}</p>
          </div>
        </section>

        <section id="chapter-two" className={styles.chapter} aria-labelledby="chapter-two-title">
          <div className={styles.chapterMarker}>
            <p>{copy.chapterTwo.chapter}</p>
            <span>{copy.chapterTwo.label}</span>
          </div>
          <div className={styles.chapterContent}>
            <h2 id="chapter-two-title">
              {copy.chapterTwo.headlineStart}<br />
              <em>{copy.chapterTwo.headlineEmphasis}</em>
            </h2>
            {copy.chapterTwo.paragraphs.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
            <ul className={styles.questionList}>
              {copy.chapterTwo.questions.map((question) => <li key={question}>{question}</li>)}
            </ul>
            <p>{copy.chapterTwo.invitation}</p>
            <BrownieChatDemo />
            {copy.chapterTwo.afterPanel.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
          </div>
        </section>

        <section id="demo" className={styles.demoSection} aria-labelledby="demo-title">
          <div className={styles.demoHeading}>
            <h2 id="demo-title">
              {copy.demo.headlineStart}<br />
              <em>{copy.demo.headlineEnd}</em>
            </h2>
            <p>{copy.demo.note}</p>
          </div>
          <DemoVideo />
        </section>

        <section className={styles.chapter} aria-labelledby="chapter-three-title">
          <div className={styles.chapterMarker}>
            <p>{copy.chapterThree.chapter}</p>
            <span>{copy.chapterThree.label}</span>
          </div>
          <div className={styles.chapterContent}>
            <h2 id="chapter-three-title">
              {copy.chapterThree.headlineStart}<br />
              {copy.chapterThree.headlineEnd}
            </h2>
            <p>{copy.chapterThree.body}</p>
            <div className={styles.chartFrame}>
              <div className={styles.chartHeading}>
                <span>{copy.chapterThree.chartTitle}</span>
                <span>{copy.chapterThree.chartLabel}</span>
              </div>
              <MasteryChart />
            </div>
          </div>
        </section>
      </div>

      <BrownieFeedback />

      <footer className={styles.footer}>
        <span>{copy.footer.brand}</span>
        <span>{copy.footer.line}</span>
      </footer>
    </main>
  );
}

export default function BrownieLanding() {
  return (
    <LandingLanguageProvider>
      <LandingPageContent />
    </LandingLanguageProvider>
  );
}
