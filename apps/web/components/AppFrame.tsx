"use client";

import { useEffect, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";

/** Routes that bring their own full-width layout (the new chat shell and the design gallery). */
const BARE = [/^\/$/, /^\/brownie(\/|$)/, /^\/dev\/ui(\/|$)/];

/**
 * The legacy phone-column wrapper for every other screen. When a screen runs inside the workspace panel
 * (a frame named "yt-embed") it fills the panel and tells the chat which page it is on, so refresh and
 * deep links return to the same place. The screens themselves are unchanged.
 */
export default function AppFrame({ children }: { children: ReactNode }) {
  const path = usePathname() ?? "/";
  const [embedded, setEmbedded] = useState(false);

  useEffect(() => {
    setEmbedded(window.name === "yt-embed" && window.parent !== window);
  }, []);

  useEffect(() => {
    if (!embedded) return;
    window.parent.postMessage({ type: "yt:nav", path }, window.location.origin);
  }, [embedded, path]);

  if (BARE.some((rule) => rule.test(path))) return <>{children}</>;
  return <div className={embedded ? "phone embed" : "phone"}>{children}</div>;
}
