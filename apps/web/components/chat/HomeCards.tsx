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
import { useChatApi } from "./ChatProvider";
import { TopicMastery } from "./TopicMastery";
import { RightPanel } from "./RightPanel";

export type StudentHome = {
  resume: { session_id: string } | null;
  minutesLeft: number | null;
  current: { chapter: ChapterCard; skill?: string } | null;
  started: boolean;
  due: number;
  topics: { id: string; title: string; percent: number | null }[];
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
      if (live) {
        setData({
          resume: me.resume ?? null,
          minutesLeft: me.remaining_active_minutes ?? null,
          current: chapter ? { chapter, skill } : null,
          started,
          due,
          topics: live_.map((c) => ({
            id: c.id,
            title: c.title,
            percent: c.skills_total > 0 ? Math.round((c.skills_can_do_it / c.skills_total) * 100) : null,
          })),
        });
      }
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

function Row({ children }: { children: React.ReactNode; two?: boolean }) {
  return (
    <div
      className="grid w-full grid-cols-1 gap-3 @xl:grid-cols-2"
      data-testid="home-cards"
    >
      {children}
    </div>
  );
}

/** Home actions follow the role; learner progress is shown only when backed by API data. */
export function HomeCards() {
  const { role, copy, dispatch, openWorkspace, startMode, tryOneQuestion, busy, identityReady, ctx, contextError } = useChatApi();
  const student = useStudentHome(role === "student" || role === "guest");
  const teacher = useTeacherHome(role === "teacher");

  if (!identityReady) {
    return null;
  }

  if (role === "visitor") {
    // The setup questions come from the registry: wait for it, never start with nothing to ask.
    if (!ctx) {
      return contextError ? (
        <p role="alert" className="m-0 text-sm text-danger" data-testid="context-error">
          {copy.chatCouldNotLoad}
        </p>
      ) : null;
    }
    return (
      <div className="flex w-full flex-col gap-3">
        <Row two>
          <button type="button" disabled={busy} onClick={() => void tryOneQuestion()} data-testid="card-try-question" className="home-card flex min-h-[8.5rem] w-full cursor-pointer flex-col items-start gap-1 rounded-2xl p-4 text-left text-ink hover:border-warning disabled:opacity-60">
            <span className="text-[0.9375rem] font-medium">{copy.chatCardTryQuestion}</span>
            <span className="text-[0.75rem] font-normal text-muted">{copy.chatCardTryQuestionHint}</span>
            <span className="mt-auto inline-flex min-h-9 items-center rounded-full border border-input-line px-4 text-[0.75rem] font-medium">{copy.chatPlanStart}</span>
          </button>
          <button type="button" onClick={() => dispatch({ type: "start_setup", intent: "lesson" })} data-testid="card-try-lesson" className="home-card flex min-h-[8.5rem] w-full cursor-pointer flex-col items-start gap-1 rounded-2xl p-4 text-left text-ink hover:border-accent">
            <span className="text-[0.9375rem] font-medium">{copy.chatCardTryLesson}</span>
            <span className="text-[0.75rem] font-normal text-muted">{copy.chatCardTryLessonHint}</span>
            <span className="mt-auto inline-flex min-h-9 items-center rounded-full bg-accent px-4 text-[0.75rem] font-medium text-accent-fg">{copy.chatStartLesson}</span>
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
      return <p role="alert" className="m-0 text-sm text-danger">{copy.chatCouldNotLoad}</p>;
    }
    if (!student.data) return null;
    const { current, started, due, resume } = student.data;
    const hasProgress = started || Boolean(resume);
    return (
      <>
        <div className={`grid w-full grid-cols-1 items-start gap-4 ${hasProgress ? "xl:grid-cols-[minmax(0,1fr)_15rem]" : ""}`}>
          <div className="flex min-w-0 flex-col gap-4">
            {started && student.data.topics.some((topic) => topic.percent !== null) ? (
              <TopicMastery topics={student.data.topics.filter((topic): topic is typeof topic & { percent: number } => topic.percent !== null)} />
            ) : null}
            {student.data.topics.length > 0 ? (
              <div className="flex w-full flex-wrap gap-2" role="group" aria-label={copy.chatTopics} data-testid="topic-chips">
                {student.data.topics.slice(0, 6).map((topic) => (
                  <button key={topic.id} type="button" onClick={() => openWorkspace(`/chapters/${encodeURIComponent(topic.id)}`, topic.title)} className="home-card inline-flex min-h-11 w-auto cursor-pointer items-center rounded-full px-3.5 text-sm font-normal text-ink">
                    {topic.title}
                  </button>
                ))}
              </div>
            ) : null}
          </div>
          {hasProgress ? (
            <RightPanel
              student={student.data}
              reviewEnabled={role !== "guest"}
              onContinue={() => {
                if (resume) openWorkspace(`/session/${resume.session_id}`, copy.resume);
                else openWorkspace(current ? `/chapters/${encodeURIComponent(current.chapter.id)}` : "/chapters", current?.chapter.title);
              }}
              onReview={() => void startMode("revise")}
              onToday={() => openWorkspace("/today", copy.chatToday)}
            />
          ) : null}
        </div>
        {!hasProgress ? (
          <Row>
          <SuggestionCard tone="accent" icon="play" title={copy.chatStartHere} description={current?.chapter.title} tag={copy.chatNew} onClick={() => openWorkspace(current ? `/chapters/${encodeURIComponent(current.chapter.id)}` : "/chapters", current?.chapter.title)} data-testid="card-start" />
          </Row>
        ) : null}
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
