"use client";

import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet";
import { useChatApi } from "./ChatProvider";
import { SidebarContent } from "./Sidebar";

/** The phone menu. Loaded the first time the menu button is pressed, so the dialog code is not in the first view. */
export default function MobileDrawer({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const { copy } = useChatApi();
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="left" className="p-0">
        <SheetTitle className="sr-only">{copy.appName}</SheetTitle>
        <SheetDescription className="sr-only">{copy.appName}</SheetDescription>
        <SidebarContent onDone={() => onOpenChange(false)} />
      </SheetContent>
    </Sheet>
  );
}
