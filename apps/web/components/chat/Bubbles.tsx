"use client";

import { Brand } from "@/components/ui/brand";
import { Choice } from "@/components/ui/choice";
import { locale } from "@/lib/api";
import { messageText } from "@/lib/chat/labels";
import { useChatApi } from "./ChatProvider";

/** The small pieces the first screen needs (a chat bubble, finder replies, the last summary). The conversation
    itself lives in Thread.tsx, which loads only once there is a conversation to show. */
export function Bubble({ from, text }: { from: "tutor" | "user"; text: string }) {
  const { copy } = useChatApi();
  if (!text) return null;
  if (from === "user") {
    return (
      <div className="flex justify-end">
        <p className="m-0 max-w-[80%] rounded-2xl rounded-br-md bg-accent-soft px-4 py-2.5 text-base text-ink" data-testid="msg-user">
          <span className="sr-only">{copy.chatYou}: </span>
          {text}
        </p>
      </div>
    );
  }
  return (
    <div className="flex items-start gap-3">
      <span className="mt-0.5 shrink-0">
        <Brand showName={false} />
      </span>
      <p className="m-0 max-w-[85%] rounded-2xl rounded-tl-md bg-surface px-4 py-2.5 text-base text-ink shadow-[var(--shadow-card)]" data-testid="msg-tutor">
        <span className="sr-only">{copy.chatTutor}: </span>
        {text}
      </p>
    </div>
  );
}

/** Replies from the finder: Did you mean chips, "not in your syllabus yet", and gentle notices. */
export function Replies() {
  const { replies, copy, pickTopic, mode } = useChatApi();
  if (!replies.length) return null;
  return (
    <div className="flex flex-col gap-3" aria-live="polite" data-testid="replies">
      {replies.map((reply) => {
        const text =
          reply.kind === "matches"
            ? copy.chatFinderDidYouMean
            : reply.kind === "none"
              ? copy.chatFinderNone
              : reply.kind === "blocked"
                ? copy.chatFinderBlocked
                : reply.kind === "distress"
                  ? copy.chatFinderDistress
                  : reply.kind === "pick_class"
                    ? copy.chatFinderPickClass
                    : reply.kind === "too_long"
                      ? copy.chatFinderTooLong
                      : copy.chatFinderOff;
        return (
          <div key={reply.id} className="flex flex-col gap-3" data-testid={`reply-${reply.kind}`}>
            <Bubble from="tutor" text={text} />
            {reply.piiRemoved ? <p className="m-0 pl-11 text-sm text-muted">{copy.chatFinderPii}</p> : null}
            {reply.topics?.length ? (
              <div className="flex flex-wrap gap-2 pl-11">
                {reply.topics.map((topic) => (
                  <Choice key={topic.id} onClick={() => void pickTopic(topic, reply.mode ?? mode)} data-testid={`topic-${topic.id}`}>
                    {topic.title}
                  </Choice>
                ))}
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

/** The most recent finished workflow, as a short note under the composer (a summary, never a transcript). */
export function LatestSummary() {
  const { chat, ctx, copy } = useChatApi();
  const last = [...chat.messages].reverse().find((m) => m.key === "summary");
  if (!last) return null;
  return (
    <div aria-live="polite" data-testid="summary">
      <Bubble from="tutor" text={messageText(copy, ctx, last, locale())} />
    </div>
  );
}
