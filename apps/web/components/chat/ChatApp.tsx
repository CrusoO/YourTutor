"use client";

import { AssistantRuntimeProvider, useExternalStoreRuntime, type ThreadMessageLike } from "@assistant-ui/react";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/icons";
import { Brand } from "@/components/ui/brand";
import { LanguageSwitch } from "@/components/ui/language-switch";
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet";
import { locale } from "@/lib/api";
import { dismissTip, tipDismissed } from "@/lib/chat/device";
import { greeting } from "@/lib/chat/greeting";
import { messageText } from "@/lib/chat/labels";
import { ChatProvider, useChatApi } from "./ChatProvider";
import { Composer } from "./Composer";
import { HomeCards } from "./HomeCards";
import dynamic from "next/dynamic";
import { LatestSummary, Replies } from "./Bubbles";
// The conversation (setup chips, sign-in forms) loads only when there is one: the first screen is the hero.
const Thread = dynamic(() => import("./Thread").then((m) => m.Thread), { ssr: false });
import { SidebarContent } from "./Sidebar";
import { WorkspacePanel } from "./WorkspacePanel";

/** A visitor with nothing set up yet, or someone on their home: greeting, composer and cards, centred. */
function Hero() {
  const { copy, hour, identity, identityReady, error, role } = useChatApi();
  const [tipOpen, setTipOpen] = useState(() => !tipDismissed());
  const name = identity?.name;
  const adult = identity?.role === "teacher" || identity?.role === "parent";
  const line = hour === null || !identityReady ? "" : greeting(copy, hour, name, adult);
  return (
    <div className="mx-auto flex min-h-0 w-full max-w-4xl flex-1 flex-col items-center gap-6 overflow-y-auto px-4 py-8 [&>:first-child]:mt-auto [&>:last-child]:mb-auto" data-testid="hero">
      {identity?.role === "guest" && tipOpen ? (
        <div className="glass-flat flex w-full max-w-3xl items-center justify-between gap-3 rounded-2xl px-4 py-2 text-sm" role="note" data-testid="tip">
          <span>{copy.chatTipGuest}</span>
          <Button variant="ghost" size="sm" onClick={() => { dismissTip(); setTipOpen(false); }}>
            {copy.chatTipDismiss}
          </Button>
        </div>
      ) : null}
      <div className="flex w-full max-w-3xl flex-col gap-3" data-testid="hero-frame">
        <h1 className="home-title m-0 min-h-[1lh] text-ink" data-testid="greeting">
          {line}
        </h1>
        <p className="m-0 text-base text-muted">{role === "visitor" ? copy.homeSubtitle : copy.chatPrompt}</p>
      </div>
      <Composer />
      <div className="w-full max-w-3xl">
        <Replies />
        <LatestSummary />
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
      <div className="ui-root home-flat flex h-dvh w-full overflow-hidden" data-testid="app-shell">
        <a href="#chat-main" className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-50 focus:rounded-lg focus:bg-surface focus:p-3">
          {copy.chatBackToChat}
        </a>
        {!collapsed ? (
          <aside className="glass-flat hidden w-72 shrink-0 border-0 border-r border-line lg:flex" aria-label={copy.appName} data-testid="sidebar">
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
            <Button variant="ghost" size="icon" className="size-11 min-h-11 min-w-11 text-muted lg:hidden" onClick={() => setDrawer(true)} aria-label={copy.chatOpenMenu} title={copy.chatOpenMenu} data-testid="menu-open">
              <Icon name="menu" />
            </Button>
            <Button variant="ghost" size="icon" className="hidden size-11 min-h-11 min-w-11 text-muted lg:inline-flex" onClick={() => setCollapsed((v) => !v)} aria-expanded={!collapsed} aria-label={collapsed ? copy.chatOpenMenu : copy.chatCollapse} title={collapsed ? copy.chatOpenMenu : copy.chatCollapse} data-testid="sidebar-toggle">
              <Icon name="menu" />
            </Button>
            <span className="lg:hidden">
              <Brand />
            </span>
            <span className="ml-auto">
              <LanguageSwitch />
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
