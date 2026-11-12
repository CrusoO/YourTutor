"use client";

import { Choice } from "@/components/ui/choice";
import { prettify } from "@/lib/chat/labels";
import { introCopy, liveSubjects } from "@/lib/chat/intro";
import { useChatApi } from "./ChatProvider";

/**
 * The first thing a signed-in person sees on the chat home: who they are signed in as, what they can ask, and a few
 * starter buttons that fit their role and the content that really exists. Buttons open pages or start the same
 * modes the rest of the home does; nothing typed is sent anywhere.
 */
export function SignedInIntro({
  role,
  hasProgress = false,
  chapterPath,
  chapterTitle,
  topics = [],
}: {
  role: "student" | "teacher" | "parent";
  hasProgress?: boolean;
  chapterPath?: string;
  chapterTitle?: string;
  /** Titles of the chapters that are live for this learner right now. */
  topics?: string[];
}) {
  const { copy, ctx, identity, openWorkspace, startMode } = useChatApi();
  const c = introCopy;
  const subjects = liveSubjects(ctx, (n) => copy.chatClassN.replace("{n}", String(n)), (id) => (id === "math" ? "Maths" : prettify(id)));
  const name = identity?.name?.trim();

  const who =
    role === "teacher" ? c.teacher : role === "parent" ? c.guardian : name ? c.signedInAs.replace("{name}", name) : c.signedInStudent;
  const can =
    role === "teacher"
      ? c.teacherHelp
      : role === "parent"
        ? c.guardianHelp
        : topics.length > 0
          ? c.canAsk.replace("{topics}", topics.slice(0, 3).join(", "))
          : subjects.length > 0
            ? c.notYet.replace("{subjects}", subjects.join(", "))
            : c.none;

  const chips: { id: string; label: string; go: () => void }[] = [];
  if (role === "student") {
    if (topics.length > 0) {
      chips.push({ id: "start", label: c.chipStart.replace("{topic}", chapterTitle ?? topics[0]), go: () => openWorkspace(chapterPath ?? "/chapters", chapterTitle) });
      if (hasProgress) chips.push({ id: "revise", label: c.chipRevise, go: () => void startMode("revise") });
    }
    if (topics.length > 0 || subjects.length > 0) {
      chips.push({ id: "chapters", label: c.chipChapters, go: () => openWorkspace("/chapters", copy.chatChapters) });
    }
  } else if (role === "teacher") {
    chips.push({ id: "classes", label: c.chipClasses, go: () => openWorkspace("/teacher", copy.chatHeatmap) });
    chips.push({ id: "stuck", label: c.chipStuck, go: () => openWorkspace("/teacher", copy.chatStuckNow) });
  } else {
    chips.push({ id: "child", label: c.chipChild, go: () => openWorkspace("/guardian", copy.chatThisWeek) });
    chips.push({ id: "add", label: c.chipAdd, go: () => openWorkspace("/guardian", copy.chatAddChild) });
  }

  return (
    <section className="flex w-full flex-col gap-3" aria-label={who} data-testid="signed-in-intro">
      <p className="m-0 text-base font-semibold text-ink" data-testid="intro-who">{who}</p>
      <p className="m-0 text-base text-muted" data-testid="intro-can">
        {can} {role === "student" ? c.soon : ""}
      </p>
      {chips.length > 0 ? (
        <div className="flex flex-wrap gap-2" role="group" aria-label={who} data-testid="intro-chips">
          {chips.map((chip) => (
            <Choice key={chip.id} onClick={chip.go} data-testid={`intro-chip-${chip.id}`}>
              {chip.label}
            </Choice>
          ))}
        </div>
      ) : null}
    </section>
  );
}
