"use client";

import { Brand } from "@/components/ui/brand";
import { Button } from "@/components/ui/button";
import { Icon, type IconName } from "@/components/ui/icons";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { locale } from "@/lib/api";
import { messageText } from "@/lib/chat/labels";
import { useState } from "react";
import { ComfortDialog, ThemeSwitch } from "./ComfortSettings";
import { useChatApi } from "./ChatProvider";

type Item = { icon: IconName; label: string; onClick?: () => void; soon?: boolean; testid: string; keepOpen?: boolean };

function NavItem({ item, onDone }: { item: Item; onDone?: () => void }) {
  const { copy } = useChatApi();
  return (
    <li>
      <button
        type="button"
        disabled={item.soon}
        onClick={() => {
          item.onClick?.();
          if (!item.keepOpen) onDone?.();
        }}
        data-testid={item.testid}
        className="flex min-h-12 w-full cursor-pointer items-center gap-3 rounded-xl border-0 bg-transparent px-3 text-left text-base font-medium text-ink hover:bg-surface-2 disabled:cursor-not-allowed disabled:opacity-60"
      >
        <Icon name={item.icon} />
        <span className="flex-1">{item.label}</span>
        {item.soon ? <span className="rounded-full bg-neutral-soft px-2 py-0.5 text-xs font-semibold text-muted">{copy.chatSoon}</span> : null}
      </button>
    </li>
  );
}

/** The navigation for the current role. Everything opens in the workspace panel; the chat stays as home. */
export function SidebarContent({ onDone }: { onDone?: () => void }) {
  const { copy, role, identity, newChat, openWorkspace, startMode, dispatch, signOut, chat, ctx } = useChatApi();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const summaries = chat.messages.filter((m) => m.key === "summary").slice(-5).reverse();

  const items: Item[] = [{ icon: "chat", label: copy.chatNewChat, onClick: newChat, testid: "nav-new-chat" }];
  if (role === "student" || role === "guest") {
    items.push(
      { icon: "calendar", label: copy.chatToday, onClick: () => openWorkspace("/today", copy.chatToday), testid: "nav-today" },
      { icon: "book", label: copy.chatChapters, onClick: () => openWorkspace("/chapters", copy.chatChapters), testid: "nav-chapters" },
      { icon: "refresh", label: copy.chatRevision, onClick: () => void startMode("revise"), testid: "nav-revision" },
      { icon: "pencil", label: copy.chatNotes, soon: true, testid: "nav-notes" },
    );
  } else if (role === "teacher") {
    const open = (title: string) => () => openWorkspace("/teacher", title);
    items.push(
      { icon: "users", label: copy.chatClasses, onClick: open(copy.chatClasses), testid: "nav-classes" },
      { icon: "grid", label: copy.chatHeatmap, onClick: open(copy.chatHeatmap), testid: "nav-heatmap" },
      { icon: "alert", label: copy.chatStuckNow, onClick: open(copy.chatStuckNow), testid: "nav-stuck" },
      { icon: "inbox", label: copy.chatReviewQueue, onClick: open(copy.chatReviewQueue), testid: "nav-queue" },
      { icon: "chart", label: copy.chatReports, onClick: open(copy.chatReports), testid: "nav-reports" },
    );
  } else if (role === "parent") {
    const open = (title: string) => () => openWorkspace("/guardian", title);
    items.push(
      { icon: "users", label: copy.chatChildren, onClick: open(copy.chatChildren), testid: "nav-children" },
      { icon: "chart", label: copy.chatWeeklyReport, onClick: open(copy.chatWeeklyReport), testid: "nav-weekly" },
      { icon: "shield", label: copy.chatConsent, onClick: open(copy.chatConsent), testid: "nav-consent" },
      { icon: "lock", label: copy.chatMyData, onClick: open(copy.chatMyData), testid: "nav-data" },
    );
  }

  items.push({ icon: "settings", label: copy.chatSettings, onClick: () => setSettingsOpen(true), testid: "nav-settings", keepOpen: true });

  const initial = (identity?.name ?? "").trim().charAt(0).toUpperCase();

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 p-3">
      <div className="px-2 pt-1">
        <Brand />
      </div>
      <nav aria-label={copy.appName} className="min-h-0 flex-1">
        <ScrollArea className="h-full">
          <ul className="m-0 flex list-none flex-col gap-1 p-0" data-testid="sidebar-nav">
            {items.map((item) => (
              <NavItem key={item.testid} item={item} onDone={onDone} />
            ))}
          </ul>
          {role === "student" || role === "guest" ? (
            <section className="mt-5 px-3" aria-label={copy.chatRecent}>
              <h2 className="m-0 mb-2 text-xs font-semibold uppercase tracking-wide text-muted">{copy.chatRecent}</h2>
              {summaries.length ? (
                <ul className="m-0 flex list-none flex-col gap-1 p-0 text-sm" data-testid="recent">
                  {summaries.map((m) => (
                    <li key={m.id} className="truncate text-ink">{messageText(copy, ctx, m, locale())}</li>
                  ))}
                </ul>
              ) : (
                <p className="m-0 text-sm text-muted">{copy.chatNoRecent}</p>
              )}
            </section>
          ) : null}
        </ScrollArea>
      </nav>
      <div className="border-t border-line pt-3">
        <div className="mb-3 px-2" data-testid="sidebar-theme">
          <ThemeSwitch />
        </div>
        {identity ? (
          <div className="flex items-center gap-3 px-2">
            <Avatar>
              <AvatarFallback>{initial || <Icon name="user" size={16} />}</AvatarFallback>
            </Avatar>
            <div className="min-w-0 flex-1">
              <p className="m-0 truncate text-sm font-semibold" data-testid="who">
                {identity.name ??
                  (identity.role === "teacher"
                    ? copy.chatRoleTeacher
                    : identity.role === "parent"
                      ? copy.chatRoleParent
                      : copy.chatGuestName)}
              </p>
            </div>
            <Button variant="ghost" size="sm" onClick={() => { signOut(); onDone?.(); }} data-testid="sign-out">
              {copy.chatSignOut}
            </Button>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            <Button variant="outline" onClick={() => { dispatch({ type: "identity", view: "choices" }); onDone?.(); }} data-testid="nav-sign-in">
              {copy.chatSignIn}
            </Button>
            <Button onClick={() => { dispatch({ type: "identity", view: "create_account" }); onDone?.(); }} data-testid="nav-create-account">
              {copy.chatCreateAccount}
            </Button>
          </div>
        )}
      </div>
      <ComfortDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
    </div>
  );
}
