"use client";

import { AssistantRuntimeProvider, useExternalStoreRuntime, type ThreadMessageLike } from "@assistant-ui/react";
import { useMemo, useState } from "react";
import { useLocale } from "@/lib/locale";
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
import { IconSidebar } from "./IconSidebar";
import { LessonView } from "./LessonView";
import dynamic from "next/dynamic";
import { LatestSummary, Replies } from "./Bubbles";
// The conversation (setup chips, sign-in forms) loads only when there is one: the first screen is the hero.
const Thread = dynamic(() => import("./Thread").then((m) => m.Thread), { ssr: false });
import { SidebarContent } from "./Sidebar";
import { instrumentSerif, inter, notoSerifDevanagari } from "@/app/fonts";
import styles from "./ChatHome.module.css";
const WorkspacePanel = dynamic(
  () => import("./WorkspacePanel").then((m) => m.WorkspacePanel),
  { ssr: false },
);

/** A visitor with nothing set up yet, or someone on their home: greeting, composer and cards, centred. */
function Hero() {
  const { copy, hour, identity, identityReady, error } = useChatApi();
  const [tipOpen, setTipOpen] = useState(() => !tipDismissed());
  const name = identity?.name;
  const adult = identity?.role === "teacher" || identity?.role === "parent";
  const line = hour === null || !identityReady ? "" : greeting(copy, hour, name, adult);
  const lang = useLocale();
  const dateLabel = useMemo(
    () =>
      new Intl.DateTimeFormat(
        lang === "hi" ? "hi-IN" : lang,
        { weekday: "long", day: "numeric", month: "long" },
      ).format(new Date()),
    [lang],
  );
  return (
    <div className="flex min-h-0 w-full flex-1 justify-center overflow-y-auto overscroll-contain px-4 pb-[max(1.25rem,env(safe-area-inset-bottom))] pt-3 sm:px-6 lg:pt-8" data-testid="hero">
      <div className={`flex w-full min-w-0 flex-col ${styles.content}`}>
        {identity?.role === "guest" && tipOpen ? (
          <div className="glass-flat flex w-full items-center justify-between gap-3 rounded-2xl px-4 py-2 text-sm" role="note" data-testid="tip">
            <span>{copy.chatTipGuest}</span>
            <Button variant="ghost" size="sm" onClick={() => { dismissTip(); setTipOpen(false); }}>
              {copy.chatTipDismiss}
            </Button>
          </div>
        ) : null}
        <div className="mb-2 flex w-full flex-col gap-1" data-testid="hero-frame">
          <p className={styles.date} suppressHydrationWarning>{dateLabel}</p>
          <h1
            className={`home-display min-h-[1lh] ${styles.headline}`}
            data-testid="greeting"
          >
            {line === copy.chatGreetGuest ? (
              <>
                {copy.chatGreetGuestLead}{" "}
                <em className={styles.emphasis}>{copy.chatGreetGuestEmphasis}</em>
              </>
            ) : line}
          </h1>
          <p className={styles.hint} data-testid="home-chat-hint">{copy.chatHomeHint}</p>
        </div>
        <Composer />
        <div className="w-full">
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
    </div>
  );
}

function Shell() {
  const api = useChatApi();
  const { chat, ctx, copy, busy, submitText, workspace, lesson } = api;
  const [drawer, setDrawer] = useState(false);

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
      <div
        className={`${instrumentSerif.variable} ${inter.variable} ${notoSerifDevanagari.variable} ui-root home-flat flex h-dvh w-full overflow-hidden ${styles.app}`}
        data-testid="app-shell"
      >
        <a href="#chat-main" className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-50 focus:rounded-lg focus:bg-surface focus:p-3">
          {copy.chatBackToChat}
        </a>
        <IconSidebar />
        <Sheet open={drawer} onOpenChange={setDrawer}>
          <SheetContent side="left" className="p-0">
            <SheetTitle className="sr-only">{copy.appName}</SheetTitle>
            <SheetDescription className="sr-only">{copy.appName}</SheetDescription>
            <SidebarContent onDone={() => setDrawer(false)} />
          </SheetContent>
        </Sheet>

        <main id="chat-main" className="@container relative flex min-h-0 min-w-0 flex-1 flex-col" data-testid="chat-main">
          <header className={`flex items-center gap-3 px-3 py-2 ${styles.header} ${hero ? "lg:absolute lg:right-3 lg:top-2 lg:z-10 lg:p-0" : ""}`}>
            <a
              href="/"
              aria-label={copy.chatHome}
              title={copy.chatHome}
              className="grid size-11 shrink-0 place-items-center rounded-full text-muted transition-colors hover:bg-surface-2 hover:text-ink"
              data-testid="back-home"
            >
              <span aria-hidden="true">←</span>
            </a>
            <Button variant="ghost" size="icon" className="size-11 min-h-11 min-w-11 text-muted lg:hidden" onClick={() => setDrawer(true)} aria-label={copy.chatOpenMenu} title={copy.chatOpenMenu} data-testid="menu-open">
              <Icon name="menu" />
            </Button>
            <span className="lg:hidden">
              <Brand />
            </span>
            <span className="ml-auto flex items-center gap-2">
              {api.identity ? (
                <Button variant="outline" size="sm" className={styles.headerButton} onClick={api.signOut} data-testid="header-sign-out">
                  {copy.chatSignOut}
                </Button>
              ) : (
                <Button variant="outline" size="sm" className={styles.headerButton} onClick={() => api.dispatch({ type: "identity", view: "choices" })} data-testid="header-sign-in">
                  {copy.chatSignIn}
                </Button>
              )}
              <LanguageSwitch className={styles.languageSwitcher} />
            </span>
          </header>
          {lesson ? (
            <>
              <LessonView />
              <div className="mx-auto w-full max-w-[40rem] px-4 pb-[max(1rem,env(safe-area-inset-bottom))] pt-2" data-testid="docked-composer">
                <Composer docked />
              </div>
            </>
          ) : hero ? (
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
