"use client";

import { useEffect, useState } from "react";
import {
  BrownieChatDemo,
  BrownieFeedback,
  DemoVideo,
  LandingLanguages,
  MasteryChart,
  RobinOpening,
} from "./Interactions";
import { LandingLanguageProvider, useLandingLanguage } from "./LandingLanguage";
import { ComingSoon, GuessChat, HowItWorks, LearningMapView, TrustStrip, VideoDemos } from "./LandingExtras";
import { heroExtras, learningMap, videoUi, type SettingId, type StoryBeatId } from "./landing-extras";
import { legalLinks, legalNavLabel } from "@/lib/legal-copy";
import { INDEPENDENCE_FOOTER } from "@/lib/independence";
import { StoryArt } from "./StoryArt";
import styles from "./BrownieLanding.module.css";
import { instrumentSerif, inter, notoSerifDevanagari } from "../fonts";

const storyBeatParagraphs = [[0], [1], [2], [3, 4], [5]];
const storyBeatIds: StoryBeatId[] = ["nod", "silence", "missed", "belief", "asked"];
const SETTINGS: readonly SettingId[] = ["class", "work", "alone"];

function StoryBeatIllustration({ index }: { index: number }) {
  if (index === 0) {
    return (
      <div className={styles.classroomArt}>
        {Array.from({ length: 24 }, (_, dot) => (
          <span key={dot} className={dot === 14 ? styles.studentDot : ""} />
        ))}
      </div>
    );
  }

  if (index === 1) {
    return (
      <div className={styles.silenceArt}>
        <span className={styles.studentSilhouette} />
        <span className={styles.unaskedQuestions} aria-hidden="true">? ? ?</span>
        <span className={styles.silenceMark} aria-hidden="true">···</span>
      </div>
    );
  }

  if (index === 2) {
    return (
      <div className={styles.lessonPathArt}>
        {[5, 4, 3, 2, 1].map((lesson, step) => (
          <span key={lesson} className={step === 3 ? styles.missedLesson : ""}>
            <i />
          </span>
        ))}
      </div>
    );
  }

  if (index === 3) {
    return (
      <div className={styles.beliefArt}>
        <span className={styles.quoteMark} aria-hidden="true">“</span>
        <span className={styles.beliefLine} />
        <span className={styles.notTrueMark} />
      </div>
    );
  }

  return (
    <div className={styles.conversationArt}>
      <div className={styles.lessonPathMini}>
        {[5, 4, 3, 2, 1].map((lesson) => <span key={lesson} className={lesson === 2 ? styles.foundLesson : ""} />)}
      </div>
      <div className={styles.questionBubble}>
        <span />
        <i />
        <i />
      </div>
      <span className={styles.conversationLine} aria-hidden="true" />
    </div>
  );
}

function LandingPageContent() {
  const { language, copy } = useLandingLanguage();
  const [audienceIndex, setAudienceIndex] = useState(0);
  const [sceneId, setSceneId] = useState<string | null>(null);
  const [preview, setPreview] = useState(false);
  const english = language === "en";
  // The pictures follow the reader's choice of who Robin is; a classroom is the default.
  const setting: SettingId = SETTINGS.find((id) => id === sceneId) ?? "class";

  // The owner's local video picker stays reachable at /?preview=1; visitors never see it.
  useEffect(() => setPreview(new URLSearchParams(window.location.search).get("preview") === "1"), []);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setAudienceIndex((index) => (index + 1) % copy.hero.audiences.length);
    }, 3200);
    return () => window.clearInterval(timer);
  }, [copy.hero.audiences.length]);

  useEffect(() => setAudienceIndex(0), [language]);

  return (
    <main
      className={`${styles.landing} ${instrumentSerif.variable} ${inter.variable} ${notoSerifDevanagari.variable}`}
      aria-label={copy.accessibility.main}
      lang={language}
      data-testid="brownie-landing"
    >
      <header id="top" className={styles.hero}>
        <nav className={styles.heroTop} aria-label={copy.accessibility.main}>
          <a className={styles.heroBrand} href="/" aria-label={copy.hero.homepage}>
            <span className={styles.brandIdentity}>
              <img
                className={`${styles.brandLogo} ${styles.brandLogoDark}`}
                src="/brand/brownie-wordmark-dark.png"
                alt=""
                data-testid="landing-brand-dark"
              />
              <img
                className={`${styles.brandLogo} ${styles.brandLogoLight}`}
                src="/brand/brownie-wordmark-light.png"
                alt=""
                data-testid="landing-brand-light"
              />
              <span className={styles.brandSlogan} data-testid="landing-brand-slogan">
                {copy.hero.topNote}
              </span>
            </span>
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
            <p className={styles.heroDescription}>{english ? heroExtras.description : copy.hero.description}</p>
            <div className={styles.actions}>
              <a className={styles.primaryButton} href="/brownie-chat">{copy.hero.tryBrownie}</a>
              <a className={styles.ghostButton} href="#chapter-one">{copy.hero.readStory}</a>
            </div>
            <div className={styles.exploreMessage}>
              <span>{english ? heroExtras.note : copy.hero.exploreNote}</span>
            </div>
          </div>
        </div>
      </header>

      <div className={styles.story} aria-label={copy.accessibility.chapters}>
        <section id="chapter-one" className={`${styles.chapter} ${styles.chapterStory}`} aria-labelledby="chapter-one-title">
          <div className={styles.chapterMarker}>
            <p>{copy.chapterOne.chapter}</p>
            <span>{copy.chapterOne.label}</span>
          </div>
          <div className={styles.chapterContent}>
            <p className={styles.storyHook}>{copy.chapterOne.hook}</p>
            <h2 id="chapter-one-title">{copy.chapterOne.headline}</h2>
            <div className={styles.storyTimeline} data-testid="story-timeline">
              {storyBeatParagraphs.map((paragraphIndexes, index) => (
                <article className={styles.storyBeat} key={index} data-testid="story-beat">
                  <span className={styles.storyBeatNumber} aria-hidden="true">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <div className={styles.storyBeatArt} aria-hidden={english ? undefined : true}>
                    {english ? <StoryArt beat={storyBeatIds[index]!} setting={setting} /> : <StoryBeatIllustration index={index} />}
                  </div>
                  <div className={styles.storyBeatCopy}>
                    {paragraphIndexes.map((paragraphIndex) =>
                      paragraphIndex === 0 ? (
                        <RobinOpening
                          key={paragraphIndex}
                          fallback={copy.chapterOne.paragraphs[paragraphIndex]}
                          sceneId={sceneId}
                          onSceneChange={setSceneId}
                        />
                      ) : (
                        <p key={paragraphIndex}>{copy.chapterOne.paragraphs[paragraphIndex]}</p>
                      ),
                    )}
                  </div>
                </article>
              ))}
            </div>
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
            {english ? <GuessChat /> : <BrownieChatDemo />}
            {copy.chapterTwo.afterPanel.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
          </div>
        </section>

        <section id="demo" className={styles.demoSection} aria-labelledby="demo-title">
          <div className={styles.demoHeading}>
            <h2 id="demo-title">
              {english ? videoUi.heading : <>{copy.demo.headlineStart}<br /><em>{copy.demo.headlineEnd}</em></>}
            </h2>
            <p>{english ? videoUi.note : copy.demo.note}</p>
          </div>
          {english && !preview ? <VideoDemos /> : <DemoVideo />}
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
            <p>{english ? learningMap.lead : copy.chapterThree.body}</p>
            <div className={styles.chartFrame}>
              <div className={styles.chartHeading}>
                <span>{english ? learningMap.title : copy.chapterThree.chartTitle}</span>
                <span>{english ? learningMap.label : copy.chapterThree.chartLabel}</span>
              </div>
              {english ? <LearningMapView /> : <MasteryChart />}
            </div>
          </div>
        </section>
      </div>

      {english ? <HowItWorks /> : null}

      {english ? <TrustStrip /> : null}

      {english ? <ComingSoon /> : null}

      <BrownieFeedback />

      <footer className={styles.footer}>
        <span>{copy.footer.brand}</span>
        <span>{copy.footer.line}</span>
        <nav aria-label={legalNavLabel} className={styles.footerLinks} data-testid="footer-legal">
          {legalLinks.map((link) => (
            <a key={link.id} href={link.href}>
              {link.label}
            </a>
          ))}
        </nav>
        <small data-testid="footer-independence" style={{ flexBasis: "100%" }}>
          {INDEPENDENCE_FOOTER}
        </small>
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
