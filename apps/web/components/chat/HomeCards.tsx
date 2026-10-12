"use client";

import { useEffect, useState } from "react";
import { SuggestionCard, SuggestionCardSkeleton } from "@/components/ui/suggestion-card";
import {
  classView,
  getChapterSkills,
  getChapters,
  reviewQueue,
  studentId,
  teacherClasses,
  today,
  type ChapterCard,
} from "@/lib/api";
import { planFor, progressShare, type Share } from "@/lib/chat/today";
import { useChatApi } from "./ChatProvider";
import dynamic from "next/dynamic";
// The strip is a separate chunk (students only); the placeholder keeps its footprint so nothing jumps.
const TodayStrip = dynamic(() => import("./TodayStrip").then((m) => m.TodayStrip), {
  ssr: false,
  loading: () => <div aria-hidden="true" className="min-h-[15rem] w-full max-w-3xl animate-pulse rounded-[var(--radius-card)] border border-line bg-surface @2xl:min-h-[12rem]" />,
});

type StudentHome = {
  resume: { session_id: string } | null;
  minutesLeft: number | null;
  current: { chapter: ChapterCard; skill?: string } | null;
  started: boolean;
  due: number;
  share: Share;
  topics: { id: string; title: string }[];
};

type TeacherHome = { classes: number; stuck: number; review: number };

function useStudentHome(enabled: boolean) {
  const [data, setData] = useState<StudentHome | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (!enabled) return;
    let live = true;
    (async () => {
      const me = await today();
      const sid = me.student_id || studentId();
      const { chapters } = await getChapters(sid);
      const live_ = chapters.filter((c) => c.live);
      const chapter = live_.find((c) => c.recommended) ?? live_[0];
      let skill: string | undefined;
      let due = 0;
      for (const c of live_) {
        const body = await getChapterSkills(sid, c.id);
        due += body.skills.filter((s) => s.status === "review_due").length;
        if (c.id === chapter?.id) skill = body.skills.find((s) => s.current)?.title;
      }
      const started = live_.some((c) => c.status !== "not_started");
      if (live) setData({ resume: me.resume ?? null, minutesLeft: me.remaining_active_minutes ?? null, current: chapter ? { chapter, skill } : null, started, due, share: progressShare(live_), topics: live_.map((c) => ({ id: c.id, title: c.title })) });
    })().catch(() => live && setFailed(true));
    return () => {
      live = false;
    };
  }, [enabled]);
  return { data, failed };
}

function useTeacherHome(enabled: boolean) {
  const [data, setData] = useState<TeacherHome | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (!enabled) return;
    let live = true;
    (async () => {
      const { classes } = (await teacherClasses()) as { classes: { id: string }[] };
      let stuck = 0;
      for (const c of classes) stuck += ((await classView(c.id, "stuck")) as { students: unknown[] }).students.length;
      const queue = (await reviewQueue()) as { items: unknown[] };
      if (live) setData({ classes: classes.length, stuck, review: queue.items.length });
    })().catch(() => live && setFailed(true));
    return () => {
      live = false;
    };
  }, [enabled]);
  return { data, failed };
}

function Row({ children, two = false }: { children: React.ReactNode; two?: boolean }) {
  return (
    <div
      className={`grid w-full max-w-3xl grid-cols-1 gap-3 ${two ? "@2xl:grid-cols-2" : "@2xl:grid-cols-3"}`}
      data-testid="home-cards"
    >
      {children}
    </div>
  );
}

/** Three suggestion cards for whoever is looking at the home: the cards follow the role. */
export function HomeCards() {
  const { role, copy, dispatch, openWorkspace, startMode, tryOneQuestion, busy, identityReady, ctx, contextError } = useChatApi();
  const student = useStudentHome(role === "student" || role === "guest");
  const teacher = useTeacherHome(role === "teacher");

  if (!identityReady) {
    return (
      <Row>
        <SuggestionCardSkeleton />
        <SuggestionCardSkeleton />
        <SuggestionCardSkeleton />
      </Row>
    );
  }

  if (role === "visitor") {
    // The setup questions come from the registry: wait for it, never start with nothing to ask.
    if (!ctx) {
      return contextError ? (
        <p role="alert" className="m-0 text-sm text-danger" data-testid="context-error">
          {copy.chatCouldNotLoad}
        </p>
      ) : (
        <Row>
          <SuggestionCardSkeleton />
          <SuggestionCardSkeleton />
          <SuggestionCardSkeleton />
        </Row>
      );
    }
    return (
      <div className="flex w-full max-w-3xl flex-col gap-3">
        <Row two>
          <button type="button" disabled={busy} onClick={() => void tryOneQuestion()} data-testid="card-try-question" className="flex min-h-[11rem] w-full cursor-pointer flex-col items-start gap-1.5 rounded-[1.5rem] border border-warning/30 bg-warning-soft p-5 text-left text-ink shadow-[var(--shadow-card)] disabled:opacity-60">
            <span className="text-lg font-semibold">{copy.chatCardTryQuestion}</span>
            <span className="text-sm font-normal text-muted">{copy.chatCardTryQuestionHint}</span>
            <span className="mt-auto inline-flex min-h-11 items-center rounded-xl border border-ink px-4 text-sm font-semibold">{copy.chatPlanStart}</span>
          </button>
          <button type="button" onClick={() => dispatch({ type: "start_setup", intent: "lesson" })} data-testid="card-try-lesson" className="home-card flex min-h-[11rem] w-full cursor-pointer flex-col items-start gap-1.5 rounded-[1.5rem] p-5 text-left text-ink shadow-[var(--shadow-card)]">
            <span className="text-lg font-semibold">{copy.chatCardTryLesson}</span>
            <span className="text-sm font-normal text-muted">{copy.chatCardTryLessonHint}</span>
            <span className="mt-auto inline-flex min-h-11 items-center rounded-xl bg-accent px-4 text-sm font-semibold text-accent-fg">{copy.chatStartLesson}</span>
          </button>
        </Row>
        <p className="m-0 text-sm text-muted" data-testid="no-account-line">
          {copy.chatNoAccountLine}
        </p>
      </div>
    );
  }

  if (role === "student" || role === "guest") {
    if (student.failed) {
      return (
        <Row>
          <SuggestionCard tone="neutral" icon="calendar" title={copy.chatToday} onClick={() => openWorkspace("/today", copy.chatToday)} data-testid="card-today" />
        </Row>
      );
    }
    if (!student.data) {
      return (
        <Row>
          <SuggestionCardSkeleton />
          <SuggestionCardSkeleton />
          <SuggestionCardSkeleton />
        </Row>
      );
    }
    const { current, started, due, minutesLeft, resume } = student.data;
    const startCard = !started;
    const plan = planFor({ due: role === "guest" ? 0 : due, next: current?.skill });
    const startToday = () => {
      if (resume) openWorkspace(`/session/${resume.session_id}`, copy.resume);
      else if (due > 0 && role !== "guest") void startMode("revise");
      else openWorkspace(current ? `/chapters/${encodeURIComponent(current.chapter.id)}` : "/chapters", current?.chapter.title);
    };
    return (
      <>
      {student.data.topics.length > 0 ? (
        <div className="flex w-full max-w-3xl flex-wrap gap-2" role="group" aria-label={copy.chatTopics} data-testid="topic-chips">
          {student.data.topics.slice(0, 6).map((topic) => (
            <button key={topic.id} type="button" onClick={() => openWorkspace(`/chapters/${encodeURIComponent(topic.id)}`, topic.title)} className="home-card inline-flex min-h-11 w-auto cursor-pointer items-center rounded-full px-3.5 text-sm font-normal text-ink">
              {topic.title}
            </button>
          ))}
        </div>
      ) : null}
      {started || resume ? <TodayStrip share={student.data.share} plan={plan} onStart={startToday} /> : null}
      <Row>
        {resume ? (
          <SuggestionCard tone="accent" icon="play" title={copy.resume} description={current?.chapter.title} tag={copy.chatContinue} onClick={() => openWorkspace(`/session/${resume.session_id}`, copy.resume)} data-testid="card-resume" />
        ) : startCard ? (
          <SuggestionCard tone="accent" icon="play" title={copy.chatStartHere} description={current?.chapter.title} tag={copy.chatNew} onClick={() => openWorkspace(current ? `/chapters/${encodeURIComponent(current.chapter.id)}` : "/chapters", current?.chapter.title)} data-testid="card-start" />
        ) : (
          <SuggestionCard
            tone="accent"
            icon="play"
            title={copy.chatContinue}
            description={current ? `${current.chapter.skills_can_do_it}/${current.chapter.skills_total} · ${current.chapter.title}` : copy.chatContinueHint}
            onClick={() => openWorkspace(current ? `/chapters/${encodeURIComponent(current.chapter.id)}` : "/chapters", current?.chapter.title)}
            data-testid="card-continue"
          />
        )}
        <SuggestionCard
          tone={due > 0 ? "success" : "neutral"}
          icon="refresh"
          title={copy.chatReviewDue}
          tag={due > 0 ? copy.chatReviewDueN.replace("{n}", String(due)) : copy.chatNothingDue}
          disabled={due === 0 || role === "guest"}
          onClick={() => void startMode("revise")}
          data-testid="card-review"
        />
        <SuggestionCard tone="neutral" icon="calendar" title={copy.chatTodayPlan} tag={minutesLeft !== null ? copy.chatMinutesLeft.replace("{n}", String(minutesLeft)) : undefined} onClick={() => openWorkspace("/today", copy.chatToday)} data-testid="card-plan" />
      </Row>
      </>
    );
  }

  if (role === "teacher") {
    if (teacher.failed) {
      return (
        <Row>
          <SuggestionCard tone="accent" icon="grid" title={copy.chatHeatmap} onClick={() => openWorkspace("/teacher", copy.chatHeatmap)} data-testid="card-heatmap" />
        </Row>
      );
    }
    if (!teacher.data) {
      return (
        <Row>
          <SuggestionCardSkeleton />
          <SuggestionCardSkeleton />
          <SuggestionCardSkeleton />
        </Row>
      );
    }
    return (
      <Row>
        <SuggestionCard tone="accent" icon="grid" title={copy.chatHeatmap} tag={String(teacher.data.classes)} onClick={() => openWorkspace("/teacher", copy.chatHeatmap)} data-testid="card-heatmap" />
        <SuggestionCard tone={teacher.data.stuck ? "warning" : "neutral"} icon="alert" title={copy.chatStuckNow} tag={String(teacher.data.stuck)} onClick={() => openWorkspace("/teacher", copy.chatStuckNow)} data-testid="card-stuck" />
        <SuggestionCard tone="neutral" icon="inbox" title={copy.chatReviewQueue} tag={String(teacher.data.review)} onClick={() => openWorkspace("/teacher", copy.chatReviewQueue)} data-testid="card-queue" />
      </Row>
    );
  }

  return (
    <Row>
      <SuggestionCard tone="accent" icon="chart" title={copy.chatThisWeek} onClick={() => openWorkspace("/guardian", copy.chatThisWeek)} data-testid="card-week" />
      <SuggestionCard tone="success" icon="shield" title={copy.chatConsent} onClick={() => openWorkspace("/guardian", copy.chatConsent)} data-testid="card-consent" />
      <SuggestionCard tone="neutral" icon="plus" title={copy.chatAddChild} onClick={() => openWorkspace("/guardian", copy.chatAddChild)} data-testid="card-add-child" />
    </Row>
  );
}
