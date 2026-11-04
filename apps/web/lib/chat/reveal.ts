"use client";

import { useEffect, useState } from "react";

/** How long each word takes to appear. Fast enough not to make anyone wait, slow enough to read along. */
export const WORD_MS = 40;

/** The first `count` words of `text`, with the original spacing between them. Pure. */
export function revealedPrefix(text: string, count: number): string {
  if (count <= 0) return "";
  const parts = text.split(/(\s+)/);
  let words = 0;
  let out = "";
  for (const part of parts) {
    if (part === "") continue;
    if (/^\s+$/.test(part)) {
      if (words > 0 && words < count) out += part;
      continue;
    }
    if (words >= count) break;
    out += part;
    words += 1;
  }
  return out;
}

export function wordCount(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}

const reducedMotion = () =>
  typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/**
 * A reply that appears word by word, like someone talking it through. Nothing is delayed for someone who asks
 * their device for reduced motion: they get the whole reply at once.
 */
export function useReveal(text: string, animate: boolean): { shown: string; done: boolean } {
  const total = wordCount(text);
  const instant = !animate || reducedMotion();
  const [count, setCount] = useState(instant ? total : 0);
  useEffect(() => {
    if (instant) {
      setCount(total);
      return;
    }
    setCount(0);
    const timer = window.setInterval(() => {
      setCount((n) => {
        if (n + 1 >= total) window.clearInterval(timer);
        return Math.min(n + 1, total);
      });
    }, WORD_MS);
    return () => window.clearInterval(timer);
  }, [text, instant, total]);
  return { shown: instant ? text : revealedPrefix(text, count), done: instant || count >= total };
}
