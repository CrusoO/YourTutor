"use client";

import { AssistantRuntimeProvider, useExternalStoreRuntime, type ThreadMessageLike } from "@assistant-ui/react";
import { useMemo } from "react";
import { locale } from "@/lib/api";
import { messageText } from "@/lib/chat/labels";
import { useChatApi } from "./ChatProvider";
import { Thread } from "./Thread";

/**
 * The conversation screen. The chat runtime (assistant-ui) is about 100 KB of script, so it lives here, in its own
 * chunk, and loads only once a conversation exists. The hero, the composer and the lessons never need it.
 */
export default function ThreadScreen() {
  const { chat, ctx, copy, busy, submitText } = useChatApi();
  const threadMessages = useMemo<ThreadMessageLike[]>(
    () =>
      chat.messages
        .filter((m) => m.from !== "system")
        .map((m) => ({
          id: String(m.id),
          role: m.from === "user" ? ("user" as const) : ("assistant" as const),
          content: [{ type: "text" as const, text: messageText(copy, ctx, m, locale()) }],
          metadata: { custom: { msg: m } },
        })),
    [chat.messages, copy, ctx],
  );

  const runtime = useExternalStoreRuntime<ThreadMessageLike>({
    messages: threadMessages,
    isRunning: busy,
    convertMessage: (message) => message,
    // The typed text goes to the local finder and is dropped: it is never added to the thread, stored or sent.
    onNew: async (message) => {
      const text = message.content.map((part) => (part.type === "text" ? part.text : "")).join(" ");
      await submitText(text);
    },
  });

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <Thread />
    </AssistantRuntimeProvider>
  );
}
