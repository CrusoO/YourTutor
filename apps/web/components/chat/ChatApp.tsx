"use client";

import { AssistantRuntimeProvider, useExternalStoreRuntime, type ThreadMessageLike } from "@assistant-ui/react";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/icons";
import { Brand } from "@/components/ui/brand";
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet";
import { Toaster } from "@/components/ui/sonner";
import { locale } from "@/lib/api";
import { dismissTip, tipDismissed } from "@/lib/chat/device";
import { greeting } from "@/lib/chat/greeting";
import { messageText } from "@/lib/chat/labels";
import { ChatProvider, useChatApi } from "./ChatProvider";
import { Composer } from "./Composer";
import { HomeCards } from "./HomeCards";
import { Replies, Thread } from "./Thread";
import { SidebarContent } from "./Sidebar";
import { WorkspacePanel } from "./WorkspacePanel";

/** A visitor with nothing set up yet, or someone on their home: greeting, composer and cards, centred. */
function Hero() {
  const { copy, hour, identity, identityReady, error } = useChatApi();
  const [tipOpen, setTipOpen] = useState(() => !tipDismissed());
  const name = identity?.name;
  const adult = identity?.role === "teacher" || identity?.role === "parent";
  const line = hour === null || !identityReady ? "" : greeting(copy, hour, name, adult);
  return (
    <div className="mx-auto flex min-h-0 w-full max-w-4xl flex-1 flex-col items-center justify-center gap-6 overflow-y-auto px-4 py-8" data-testid="hero">
      {identity?.role === "guest" && tipOpen ? (
        <div className="flex w-full max-w-3xl items-center justify-between gap-3 rounded-2xl bg-accent-soft px-4 py-2 text-sm" role="note" data-testid="tip">
          <span>{copy.chatTipGuest}</span>
          <Button variant="ghost" size="sm" onClick={() => { dismissTip(); setTipOpen(false); }}>
            {copy.chatTipDismiss}
          </Button>
        </div>
      ) : null}
      <h1 className="m-0 min-h-[3.5rem] text-center font-display text-3xl font-medium leading-tight @xl:text-5xl" data-testid="greeting">
        {line}
      </h1>
      <p className="m-0 -mt-3 text-center text-base text-muted">{copy.chatPrompt}</p>
      <Composer />
      <div className="w-full max-w-3xl">
        <Replies />
      </div>
      <HomeCards />
      {error ? (
        <p role="alert" className="m-0 text-sm text-danger">
          {error}
        </p>
      ) : null}
    </div>
  );
}

function Shell() {
  const api = useChatApi();
  const { chat, ctx, copy, busy, submitText, workspace } = api;
  const [drawer, setDrawer] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

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

  const hero = chat.phase === "welcome" || chat.phase === "home";

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <div className="ui-root flex h-dvh w-full overflow-hidden" data-testid="app-shell">
        <a href="#chat-main" className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-50 focus:rounded-lg focus:bg-surface focus:p-3">
          {copy.chatBackToChat}
        </a>
        {!collapsed ? (
          <aside className="hidden w-72 shrink-0 border-r border-line bg-surface md:flex" aria-label={copy.appName} data-testid="sidebar">
            <SidebarContent />
          </aside>
        ) : null}
        <Sheet open={drawer} onOpenChange={setDrawer}>
          <SheetContent side="left" className="p-0">
            <SheetTitle className="sr-only">{copy.appName}</SheetTitle>
            <SheetDescription className="sr-only">{copy.appName}</SheetDescription>
            <SidebarContent onDone={() => setDrawer(false)} />
          </SheetContent>
        </Sheet>

        <main id="chat-main" className="@container flex min-h-0 min-w-0 flex-1 flex-col" data-testid="chat-main">
          <header className="flex items-center gap-3 px-3 py-2">
            <Button variant="ghost" size="sm" className="md:hidden" onClick={() => setDrawer(true)} data-testid="menu-open">
              <Icon name="menu" />
              {copy.chatOpenMenu}
            </Button>
            <Button variant="ghost" size="sm" className="hidden md:inline-flex" onClick={() => setCollapsed((v) => !v)} aria-expanded={!collapsed} data-testid="sidebar-toggle">
              <Icon name="menu" />
              {copy.chatCollapse}
            </Button>
            <span className="md:hidden">
              <Brand />
            </span>
          </header>
          {hero ? (
            <Hero />
          ) : (
            <>
              <Thread />
              <div className="mx-auto w-full max-w-3xl px-4 pb-[max(1rem,env(safe-area-inset-bottom))] pt-2" data-testid="docked-composer">
                <Composer docked />
              </div>
            </>
          )}
        </main>
        {workspace ? <WorkspacePanel /> : null}
        <Toaster />
      </div>
    </AssistantRuntimeProvider>
  );
}

export default function ChatApp() {
  return (
    <ChatProvider>
      <Shell />
    </ChatProvider>
  );
}
