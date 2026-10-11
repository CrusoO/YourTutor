"use client";

import { ThreadPrimitive, type ThreadMessage } from "@assistant-ui/react";
import { Brand } from "@/components/ui/brand";
import { Choice } from "@/components/ui/choice";
import { locale } from "@/lib/api";
import { messageText } from "@/lib/chat/labels";
import type { Msg } from "@/lib/chat/machine";
import { EditableAnswers, SetupChips } from "./SetupChips";
import { IdentityBlock } from "./IdentityBlock";
import { useChatApi } from "./ChatProvider";

type Custom = { msg?: Msg };

function Bubble({ from, text }: { from: "tutor" | "user"; text: string }) {
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

function ChatMessage({ message }: { message: ThreadMessage }) {
  const { chat, ctx, copy } = useChatApi();
  const msg = (message.metadata?.custom as Custom | undefined)?.msg;
  if (!msg) return null;
  const text = messageText(copy, ctx, msg, locale());
  const isLast = chat.messages.at(-1)?.id === msg.id;
  return (
    <div className="flex flex-col gap-3" data-testid={`message-${msg.key}`}>
      <Bubble from={msg.from === "user" ? "user" : "tutor"} text={text} />
      {isLast && (msg.key.startsWith("ask_") ? <SetupChips /> : null)}
      {isLast && msg.key === "identity_intro" ? (
        <>
          <EditableAnswers />
          <IdentityBlock />
        </>
      ) : null}
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

/** The conversation: assistant-ui's viewport and message list, with our own bubbles and cards inside. */
export function Thread() {
  return (
    <ThreadPrimitive.Root className="flex min-h-0 flex-1 flex-col">
      <ThreadPrimitive.Viewport className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 py-6 md:px-8" data-testid="thread">
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
          <ThreadPrimitive.Messages>{({ message }) => <ChatMessage message={message as ThreadMessage} />}</ThreadPrimitive.Messages>
          <Replies />
        </div>
      </ThreadPrimitive.Viewport>
    </ThreadPrimitive.Root>
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
