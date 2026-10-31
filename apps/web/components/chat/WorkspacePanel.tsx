"use client";

import { useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/icons";
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet";
import { useChatApi } from "./ChatProvider";

/** The existing screens run unchanged inside a frame: one source of truth, no behaviour change. */
function Frame({ src, title }: { src: string; title: string }) {
  return (
    <iframe
      key={src}
      name="yt-embed"
      title={title}
      src={src}
      className="h-full w-full flex-1 border-0 bg-white"
      data-testid="workspace-frame"
    />
  );
}

function Header({ title, onClose }: { title: string; onClose: () => void }) {
  const { copy } = useChatApi();
  const back = useRef<HTMLButtonElement>(null);
  useEffect(() => back.current?.focus(), []);
  return (
    <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-2">
      <Button ref={back} variant="ghost" size="sm" onClick={onClose} data-testid="back-to-chat">
        <Icon name="back" />
        {copy.chatBackToChat}
      </Button>
      <span className="truncate text-sm font-semibold text-muted">{title}</span>
    </div>
  );
}

/**
 * A lesson, a question or any other workspace screen opens in a full-window sheet on every screen size, over the
 * sidebar and the chat, so the student has the whole window for the work. Back to chat (and Escape) closes it and
 * puts focus back where it came from.
 */
export function WorkspacePanel() {
  const { workspace, closeWorkspace, copy } = useChatApi();
  const opener = useRef<Element | null>(null);

  useEffect(() => {
    if (workspace) opener.current = opener.current ?? document.activeElement;
    else {
      (opener.current as HTMLElement | null)?.focus?.();
      opener.current = null;
    }
  }, [workspace]);

  if (!workspace) return null;
  const title = workspace.title ?? copy.chatToday;
  const src = workspace.src;

  return (
    <Sheet open onOpenChange={(open) => (open ? undefined : closeWorkspace())}>
      <SheetContent side="full" className="p-0" data-testid="workspace-panel" onOpenAutoFocus={(e) => e.preventDefault()}>
        <SheetTitle className="sr-only">{title}</SheetTitle>
        <SheetDescription className="sr-only">{title}</SheetDescription>
        <Header title={title} onClose={closeWorkspace} />
        <Frame src={src} title={title} />
      </SheetContent>
    </Sheet>
  );
}
