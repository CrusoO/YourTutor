import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Instrument_Serif, Inter, Noto_Serif_Devanagari } from "next/font/google";
import { BrownieFeedback, BrownieQuestion, DemoVideo, LandingLanguages, MasteryChart } from "./Interactions";
import styles from "./BrownieLanding.module.css";
import { landingContent } from "./content";

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

export const metadata: Metadata = {
  title: landingContent.metadata.title,
  description: landingContent.metadata.description,
  openGraph: {
    title: landingContent.metadata.title,
    description: landingContent.metadata.description,
    type: "website",
  },
};

export default function BrownieLandingPage() {
  const flag = process.env.NEXT_PUBLIC_BROWNIE_LANDING?.trim().toLowerCase();
  if (flag && ["false", "off", "0"].includes(flag)) notFound();

  return (
    <main
      className={`${styles.landing} ${instrument.variable} ${inter.variable} ${notoSerifDevanagari.variable}`}
      aria-label={landingContent.accessibility.main}
    >
      <header className={styles.hero}>
        <div className={styles.heroTop}>
          <p>{landingContent.hero.topLabel}</p>
          <div className={styles.heroTopRight}>
            <p>{landingContent.hero.topNote}</p>
            <LandingLanguages />
          </div>
        </div>
        <h1 className={styles.wordmark}>
          <span className={styles.askWord}>{landingContent.hero.ask}</span>
          <span className={styles.brownieWord}>{landingContent.hero.name}</span>
        </h1>
        <div className={styles.heroBottom}>
          <p>{landingContent.hero.tagline}</p>
          <p>{landingContent.hero.languages}</p>
        </div>
      </header>

      <section className={`${styles.section} ${styles.hook}`} aria-labelledby="hook-title">
        <h2 id="hook-title">
          {landingContent.hook.firstLine}<br />
          <em>{landingContent.hook.secondLine}</em>
        </h2>
        <p>{landingContent.hook.body}</p>
        <div className={styles.actions}>
          <a className={styles.primaryButton} href="#chapter-two">{landingContent.hook.seeHow}</a>
          <a className={styles.ghostButton} href="#demo">{landingContent.hook.watchDemo}</a>
        </div>
      </section>

      <div className={styles.story} aria-label={landingContent.accessibility.chapters}>
        <section className={styles.chapter} aria-labelledby="chapter-one-title">
          <div className={styles.chapterMarker}>
            <p>{landingContent.chapterOne.chapter}</p>
            <span>{landingContent.chapterOne.label}</span>
          </div>
          <div className={styles.chapterContent}>
            <p className={styles.storyHook}>{landingContent.chapterOne.hook}</p>
            <h2 id="chapter-one-title">{landingContent.chapterOne.headline}</h2>
            {landingContent.chapterOne.paragraphs.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
            <p className={styles.storyInvitation}>{landingContent.chapterOne.invitation}</p>
            <p className={styles.storyStats}>{landingContent.chapterOne.stats}</p>
          </div>
        </section>

        <section id="chapter-two" className={styles.chapter} aria-labelledby="chapter-two-title">
          <div className={styles.chapterMarker}>
            <p>{landingContent.chapterTwo.chapter}</p>
            <span>{landingContent.chapterTwo.label}</span>
          </div>
          <div className={styles.chapterContent}>
            <h2 id="chapter-two-title">
              {landingContent.chapterTwo.headlineStart}<br />
              <em>{landingContent.chapterTwo.headlineEmphasis}</em>
            </h2>
            {landingContent.chapterTwo.paragraphs.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
            <ul className={styles.questionList}>
              {landingContent.chapterTwo.questions.map((question) => <li key={question}>{question}</li>)}
            </ul>
            <p>{landingContent.chapterTwo.invitation}</p>
            <BrownieQuestion />
            {landingContent.chapterTwo.afterPanel.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
          </div>
        </section>

        <section className={styles.chapter} aria-labelledby="chapter-three-title">
          <div className={styles.chapterMarker}>
            <p>{landingContent.chapterThree.chapter}</p>
            <span>{landingContent.chapterThree.label}</span>
          </div>
          <div className={styles.chapterContent}>
            <h2 id="chapter-three-title">
              {landingContent.chapterThree.headlineStart}<br />
              {landingContent.chapterThree.headlineEnd}
            </h2>
            <p>{landingContent.chapterThree.body}</p>
            <div className={styles.chartFrame}>
              <div className={styles.chartHeading}>
                <span>{landingContent.chapterThree.chartTitle}</span>
                <span>{landingContent.chapterThree.chartLabel}</span>
              </div>
              <MasteryChart />
            </div>
          </div>
        </section>
      </div>

      <section id="demo" className={styles.demoSection} aria-labelledby="demo-title">
        <div className={styles.demoHeading}>
          <h2 id="demo-title">
            {landingContent.demo.headlineStart}<br />
            <em>{landingContent.demo.headlineEnd}</em>
          </h2>
          <p>{landingContent.demo.note}</p>
        </div>
        <DemoVideo />
      </section>

      <section className={styles.closing} aria-label={landingContent.accessibility.close}>
        <p className={styles.closingEyebrow}>{landingContent.footer.brand}</p>
        <h2>
          <span>{landingContent.close.ask}</span>
          <span>{landingContent.close.name}</span>
        </h2>
        <p className={styles.closingTagline}>{landingContent.close.tagline}</p>
        <div className={styles.actions}>
          <a className={styles.primaryButton} href="/">{landingContent.close.start}</a>
          <a className={styles.ghostButton} href="#demo">{landingContent.close.watchDemo}</a>
        </div>
      </section>

      <BrownieFeedback />

      <footer className={styles.footer}>
        <span>{landingContent.footer.brand}</span>
        <span>{landingContent.footer.line}</span>
      </footer>
    </main>
  );
}