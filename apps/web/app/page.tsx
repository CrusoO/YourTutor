import { Suspense } from "react";
import ChatApp from "@/components/chat/ChatApp";

/** Skeleton shown while ChatApp hydrates. Matches the shell layout to minimise CLS. */
function ChatSkeleton() {
  return (
    <div
      aria-hidden
      className="flex h-dvh w-full overflow-hidden"
    >
      {/* sidebar placeholder (desktop only) */}
      <div className="hidden w-72 shrink-0 border-r border-[var(--c-line)] lg:block" />
      {/* main area */}
      <div className="flex flex-1 flex-col items-center justify-center gap-6 px-4 pb-8 pt-16">
        <div className="w-full max-w-3xl space-y-3">
          <div className="h-8 w-1/2 animate-pulse rounded-lg bg-[var(--c-surface-2)]" />
          <div className="h-4 w-1/3 animate-pulse rounded-md bg-[var(--c-surface-2)]" />
        </div>
        <div className="h-14 w-full max-w-3xl animate-pulse rounded-xl bg-[var(--c-surface-2)]" />
      </div>
    </div>
  );
}

/** The front door: a chat-style welcome with no login wall. Signing in happens inside the conversation. */
export default function HomePage() {
  return (
    <Suspense fallback={<ChatSkeleton />}>
      <ChatApp />
    </Suspense>
  );
}
