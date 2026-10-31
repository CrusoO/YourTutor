"use client";

import { useEffect } from "react";
import { useLocale } from "@/lib/locale";

const SHEET_ID = "yt-devanagari-fonts";

/**
 * Loads Noto Sans Devanagari (public/fonts/devanagari.css) only when the active language is Hindi, and only after
 * first paint, so it never competes with the first view. English readers never download it. The page shows the
 * system Devanagari font until the faces arrive (font-display: swap), so nothing waits on the network.
 */
export default function FontLoader() {
  const locale = useLocale();
  useEffect(() => {
    if (locale !== "hi" || document.getElementById(SHEET_ID)) return;
    const add = () => {
      if (document.getElementById(SHEET_ID)) return;
      const link = document.createElement("link");
      link.id = SHEET_ID;
      link.rel = "stylesheet";
      link.href = "/fonts/devanagari.css";
      document.head.appendChild(link);
    };
    const idle = (window as unknown as { requestIdleCallback?: (fn: () => void, o?: { timeout: number }) => number }).requestIdleCallback;
    const run = () => (idle ? idle(add, { timeout: 1500 }) : window.setTimeout(add, 200));
    if (document.readyState === "complete") run();
    else window.addEventListener("load", run, { once: true });
    return () => window.removeEventListener("load", run);
  }, [locale]);
  return null;
}
