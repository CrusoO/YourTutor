"use client";

import { Fragment, useEffect, useRef, useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { createSourceVideoJob, createStoryVideoJob, explainQuestion, explainStory, getVideoJob, type Explanation, type StoryResult, type VideoJob, type VideoSource } from "@/lib/api";
import { currentLocale, useCopy } from "@/lib/locale";
import { SourcesDrawer } from "./SourcesDrawer";
import { VideoCard } from "./VideoCard";
import { useChatApi } from "./ChatProvider";

const FAST_MS = 3_000;
const SLOW_MS = 15_000;

/** **bold** inside a line; nothing else is interpreted, so model text can never inject markup. */
function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") && part.length > 4 ? <strong key={i}>{part.slice(2, -2)}</strong> : <Fragment key={i}>{part}</Fragment>,
  );
}

/** Paragraphs, bullet lists and numbered lists from plain text. */
function Prose({ text }: { text: string }) {
  const blocks = text.split(/\n{2,}/).map((b) => b.trim()).filter(Boolean);
  return (
    <>
      {blocks.map((block, i) => {
        const lines = block.split("\n").map((l) => l.trim()).filter(Boolean);
        if (lines.every((l) => /^[-*•]\s+/.test(l))) {
          return (
            <ul key={i} className="m-0 flex list-disc flex-col gap-1.5 pl-5">
              {lines.map((l, j) => (
                <li key={j}>{inline(l.replace(/^[-*•]\s+/, ""))}</li>
              ))}
            </ul>
          );
        }
        if (lines.every((l) => /^\d+[.)]\s+/.test(l))) {
          return (
            <ol key={i} className="m-0 flex list-decimal flex-col gap-1.5 pl-5">
              {lines.map((l, j) => (
                <li key={j}>{inline(l.replace(/^\d+[.)]\s+/, ""))}</li>
              ))}
            </ol>
          );
        }
        return (
          <p key={i} className="m-0">
            {lines.map((l, j) => (
              <Fragment key={j}>
                {j > 0 ? <br /> : null}
                {inline(l)}
              </Fragment>
            ))}
          </p>
        );
      })}
    </>
  );
}

type VideoState =
  | { phase: "starting" }
  | { phase: "english" }
  | { phase: "none" }
  | { phase: "error" }
  | { phase: "job"; job: VideoJob };

const TERMINAL = new Set(["done", "failed", "cancelled"]);

function progressOf(job: VideoJob): number {
  if (job.status === "done") return 100;
  const byStage: Record<string, number> = { retrieve: 12, ground: 24, build: 40, render: 68, qa: 92 };
  return byStage[job.stage ?? ""] ?? (job.status === "running" ? 15 : 4);
}

/** The video for the question: started with the question, polled while the student reads, shown at the end. */
function VideoSection({ video, onRetry }: { video: VideoState; onRetry: () => void }) {
  const copy = useCopy();
  const job = video.phase === "job" ? video.job : null;
  const done = job?.status === "done";
  const unavailable = video.phase === "none" || video.phase === "english" || (job && job.status === "failed" && (job.error_code === "no_curriculum_data" || job.error_code === "no_lesson_for_topic"));
  const failed = video.phase === "error" || (job && (job.status === "failed" || job.status === "cancelled") && !unavailable);
  const progress = job ? progressOf(job) : 4;

  return (
    <section aria-labelledby="lesson-video-title" className="flex flex-col gap-3 border-0 border-t border-line pt-6" data-testid="lesson-video">
      <h2 id="lesson-video-title" className="m-0 text-[1.0625rem] font-medium text-ink">
        {copy.lessonVideoTitle}
      </h2>
      {done && job ? (
        <>
          <p className="m-0 text-[0.8125rem] text-muted" role="status">
            {copy.lessonVideoReady}
          </p>
          <VideoCard jobId={job.id} autoLoad />
          <p className="m-0 text-[0.75rem] text-muted">{copy.lessonVideoVoice}</p>
          <SourcesDrawer jobId={job.id} />
        </>
      ) : unavailable ? (
        <p className="m-0 text-[0.9375rem] text-muted" role="status">
          {video.phase === "english" ? copy.lessonVideoEnglishOnly : copy.lessonVideoNone}
        </p>
      ) : failed ? (
        <div className="flex flex-wrap items-center gap-3">
          <p className="m-0 text-[0.9375rem] text-danger" role="alert">
            {copy.lessonVideoFailed}
          </p>
          <Button variant="outline" size="sm" onClick={onRetry}>
            {copy.lessonVideoRetry}
          </Button>
        </div>
      ) : (
        <div className="flex flex-col gap-2" role="status">
          <p className="m-0 text-[0.9375rem] text-muted">{job?.stage_label ?? (job?.status === "queued" ? copy.lessonVideoWaiting : copy.lessonVideoMaking)}</p>
          <div className="relative h-[3px] w-full overflow-hidden rounded-full bg-surface-2" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress}>
            <div className="absolute inset-y-0 left-0 rounded-full bg-accent transition-[width] duration-700 ease-out" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}
    </section>
  );
}

function LessonBody({ prompt }: { prompt: string }) {
  const copy = useCopy();
  const { closeLesson } = useChatApi();
  const [explanation, setExplanation] = useState<Explanation | "loading">("loading");
  const [video, setVideo] = useState<VideoState>({ phase: "starting" });
  const [attempt, setAttempt] = useState(0);
  const mounted = useRef(true);
  const started = useRef(false);
  const language = useRef<"en" | "hi">(currentLocale() === "hi" ? "hi" : "en");
  const launch = useRef<(() => Promise<VideoJob>) | null>(null);
  const explained = useRef<Explanation | null>(null);
  const storyState = useRef<"pending" | "ok" | "failed">("pending");
  const launched = useRef(false);

  function startVideo() {
    const make = launch.current;
    if (!make) return;
    launched.current = true;
    setVideo({ phase: "starting" });
    make()
      .then((job) => mounted.current && setVideo({ phase: "job", job }))
      .catch(() => mounted.current && setVideo({ phase: "error" }));
  }

  // The video is an animated story the model plans and draws (ADR 0091), started the moment it arrives so it is
  // being made while the student reads. If there is no story, the written explanation is drawn as text cards (ADR 0090).
  // A guest can ask any topic — we never fall back to a curriculum-bound prompt job.
  function fallbackVideo() {
    const result = explained.current;
    if (launched.current || result === null || storyState.current === "pending") return;
    if (result.kind === "explanation" && result.video) {
      const signed = result.video;
      if ("story" in signed) {
        // /explain embedded the animated story — use it directly
        launch.current = () => createStoryVideoJob(
          (signed as { story: Record<string, unknown>; proof: string }).story,
          signed.proof,
          crypto.randomUUID()
        );
      } else {
        // /explain provided text cards
        launch.current = () => createSourceVideoJob(
          signed as { source: VideoSource; proof: string },
          crypto.randomUUID()
        );
      }
    } else {
      // No explanation or story available — show the no-video state, not a curriculum prompt job.
      launched.current = true;
      return setVideo({ phase: "none" });
    }
    startVideo();
  }

  function onStory(result: StoryResult) {
    if (result.kind === "story") {
      storyState.current = "ok";
      launch.current = () => createStoryVideoJob(result.story, result.proof, crypto.randomUUID());
      startVideo();
      return;
    }
    storyState.current = "failed";
    // a request the safety checks refused gets no video at all
    if (result.kind === "refused" || result.kind === "distress") {
      launched.current = true;
      return setVideo({ phase: "none" });
    }
    fallbackVideo();
  }

  function onExplained(result: Explanation) {
    setExplanation(result);
    explained.current = result;
    if (result.kind === "refused" || result.kind === "distress") {
      launched.current = true;
      return setVideo({ phase: "none" });
    }
    fallbackVideo();
  }

  // The written explanation and the story start together.
  useEffect(() => {
    mounted.current = true;
    if (!started.current) {
      started.current = true;
      explainQuestion(prompt, language.current)
        .then((result) => mounted.current && onExplained(result))
        .catch(() => mounted.current && onExplained({ kind: "unavailable", reason: "provider_error" }));
      if (language.current === "hi") {
        storyState.current = "failed";
        launched.current = true;
        setVideo({ phase: "english" }); // the engine's voices are English
      } else {
        explainStory(prompt, "en")
          .then((result) => mounted.current && onStory(result))
          .catch(() => mounted.current && onStory({ kind: "unavailable", reason: "provider_error" }));
      }
    }
    return () => {
      mounted.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const jobId = video.phase === "job" ? video.job.id : null;
  const finished = video.phase === "job" && TERMINAL.has(video.job.status);
  useEffect(() => {
    if (!jobId || finished) return;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let cancelled = false;
    const poll = async () => {
      if (cancelled) return;
      if (document.visibilityState === "hidden") {
        timer = setTimeout(poll, SLOW_MS);
        return;
      }
      try {
        const job = await getVideoJob(jobId);
        if (cancelled) return;
        setVideo({ phase: "job", job });
        if (!TERMINAL.has(job.status)) timer = setTimeout(poll, job.status === "running" ? FAST_MS : SLOW_MS);
      } catch {
        if (!cancelled) timer = setTimeout(poll, SLOW_MS);
      }
    };
    void poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [jobId, finished, attempt]);

  const sections = explanation !== "loading" && explanation.kind === "explanation" ? explanation.sections : [];
  const note = explanation !== "loading" && (explanation.kind === "refused" || explanation.kind === "distress" || explanation.kind === "out_of_scope") ? explanation.message : null;
  const unavailable = explanation !== "loading" && (explanation.kind === "unavailable" || explanation.kind === "empty");
  // A refused or crisis question never gets a video: the API refuses the job too.
  const showVideo = !(explanation !== "loading" && (explanation.kind === "refused" || explanation.kind === "distress"));
  const job = video.phase === "job" ? video.job : null;

  return (
    <div className="flex min-h-0 w-full flex-1 justify-center overflow-y-auto px-4 pb-8 pt-2 lg:pt-8" data-testid="lesson">
      <article className="flex w-full max-w-[40rem] min-w-0 flex-col gap-7" aria-busy={explanation === "loading"}>
        {job && !TERMINAL.has(job.status) && showVideo ? (
          <div className="sticky top-0 z-10 -mx-1 flex items-center gap-2.5 rounded-full border border-line bg-surface px-3.5 py-2 text-[0.75rem] text-muted shadow-[var(--shadow-card)]" role="status" data-testid="lesson-pill">
            <span className="size-1.5 animate-pulse rounded-full bg-accent" aria-hidden="true" />
            <span className="min-w-0 flex-1 truncate">{copy.lessonVideoMaking}</span>
            <span className="tabular-nums">{progressOf(job)}%</span>
          </div>
        ) : null}

        <header className="flex flex-col gap-2">
          <p className="m-0 text-[0.75rem] text-muted">{copy.lessonYouAsked}</p>
          <p className="m-0 break-words text-[0.9375rem] text-ink" data-testid="lesson-prompt">
            {prompt}
          </p>
          {explanation !== "loading" && explanation.kind === "explanation" && explanation.title ? (
            <h1 className="home-display m-0 mt-3 text-[clamp(1.5rem,2.6vw,2.1rem)] font-light leading-[1.15] tracking-[-0.03em] text-ink" style={{ fontFamily: "var(--ff-body)" }}>
              {explanation.title}
            </h1>
          ) : null}
        </header>

        {explanation === "loading" ? (
          <div className="flex flex-col gap-4" role="status">
            <p className="m-0 text-[0.9375rem] text-muted">{copy.lessonWriting}</p>
            <Skeleton className="h-4 w-11/12" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-4/5" />
            <Skeleton className="h-4 w-10/12" />
          </div>
        ) : null}

        {note ? (
          <p className="m-0 rounded-2xl border border-line bg-surface px-4 py-3 text-[0.9375rem] text-ink" role="status">
            {note}
          </p>
        ) : null}
        {unavailable ? (
          <p className="m-0 rounded-2xl border border-line bg-surface px-4 py-3 text-[0.9375rem] text-muted" role="status">
            {copy.lessonUnavailable}
          </p>
        ) : null}

        {sections.map((section, i) => (
          <section key={i} className="flex flex-col gap-2.5" aria-labelledby={`lesson-h-${i}`}>
            <h2 id={`lesson-h-${i}`} className="m-0 flex items-baseline gap-3 text-[1.0625rem] font-medium text-ink">
              <span className="text-[0.75rem] font-normal tabular-nums text-accent-ink" aria-hidden="true">
                {String(i + 1).padStart(2, "0")}
              </span>
              {section.heading}
            </h2>
            <div className="flex flex-col gap-3 text-[0.9375rem] leading-[1.7] text-ink">
              <Prose text={section.body} />
            </div>
          </section>
        ))}

        {showVideo ? <VideoSection video={video} onRetry={() => { startVideo(); setAttempt((n) => n + 1); }} /> : null}

        <div>
          <Button variant="outline" size="sm" onClick={closeLesson} data-testid="lesson-new">
            {copy.lessonAskElse}
          </Button>
        </div>
      </article>
    </div>
  );
}

/** The page a signed-out visitor gets after typing a question. Replaced whenever a new question is asked. */
export function LessonView() {
  const { lesson } = useChatApi();
  if (!lesson) return null;
  return <LessonBody key={lesson.id} prompt={lesson.prompt} />;
}
