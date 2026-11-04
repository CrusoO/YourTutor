"use client";

import { useReveal } from "@/lib/chat/reveal";

/**
 * Brownie's newest reply, appearing word by word. While it appears, a screen reader gets the whole reply once (not
 * a stream of single words) and the animated copy is hidden from assistive technology; when it is done the reply is
 * just plain text.
 */
export function Reveal({ text }: { text: string }) {
  const { shown, done } = useReveal(text, true);
  if (done) return <>{text}</>;
  return (
    <>
      <span className="sr-only">{text}</span>
      <span aria-hidden="true">{shown}</span>
    </>
  );
}
