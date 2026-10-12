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

type StudentHome = {
  resume: { session_id: string } | null;
  minutesLeft: number | null;
  current: { chapter: ChapterCard; skill?: string } | null;
  started: boolean;
  due: number;
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
      if (live) setData({ resume: me.resume ?? null, minutesLeft: me.remaining_active_minutes ?? null, current: chapter ? { chapter, skill } : null, started, due });
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

function Row({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="grid w-full max-w-4xl auto-cols-[minmax(14rem,1fr)] grid-flow-col gap-3 overflow-x-auto pb-1 @2xl:grid-flow-row @2xl:grid-cols-3 @2xl:overflow-visible"
      data-testid="home-cards"
    >
      {children}
    </div>
  );
}

/** Three suggestion cards for whoever is looking at the home: the cards follow the role. */
export function HomeCards() {
  const { role, copy, dispatch, openWorkspace, startMode, identityReady, ctx, contextError } = useChatApi();
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
      <Row>
        <SuggestionCard tone="accent" icon="users" title={copy.chatCardPickClass} description={copy.chatCardPickClassHint} onClick={() => dispatch({ type: "start_setup", intent: null })} data-testid="card-pick-class" />
        <SuggestionCard tone="success" icon="play" title={copy.chatCardTryLesson} description={copy.chatCardTryLessonHint} tag={copy.chatNew} onClick={() => dispatch({ type: "start_setup", intent: "lesson" })} data-testid="card-try-lesson" />
        <SuggestionCard tone="neutral" icon="pencil" title={copy.chatCardPractise} description={copy.chatCardPractiseHint} onClick={() => dispatch({ type: "start_setup", intent: "practice" })} data-testid="card-practise" />
      </Row>
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
    return (
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
