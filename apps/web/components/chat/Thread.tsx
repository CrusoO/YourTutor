"use client";

import { ThreadPrimitive, type ThreadMessage } from "@assistant-ui/react";
import { locale } from "@/lib/api";
import { messageText } from "@/lib/chat/labels";
import type { Msg } from "@/lib/chat/machine";
import { Bubble, Replies } from "./Bubbles";
import { EditableAnswers, SetupChips } from "./SetupChips";
import { IdentityBlock } from "./IdentityBlock";
import { useChatApi } from "./ChatProvider";

type Custom = { msg?: Msg };

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
