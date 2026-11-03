"use client";

import { useEffect, useRef } from "react";
import { topicFromSearch } from "./share";

type Ready = {
  /** Who is using the page; only a visitor or a guest is taken straight into a lesson. */
  role: string;
  identityReady: boolean;
  /** The choices the chat needs before it can start a lesson (loaded from the API); null until then. */
  contextReady: unknown;
  /** A lesson is already open. */
  lessonOpen: boolean;
  submitText: (text: string) => Promise<void> | void;
};

/**
 * A shared link (`/brownie-chat?topic=...`) opens straight into a lesson on that question, once. It goes through
 * the same submit path, and so the same safety checks, as typing the question. The address is cleaned right
 * afterwards so reloading, or coming back later, does not start it again.
 */
export function useLinkStart({ role, identityReady, contextReady, lessonOpen, submitText }: Ready) {
  const started = useRef(false);
  useEffect(() => {
    if (started.current || !identityReady || !contextReady || lessonOpen) return;
    if (role !== "visitor" && role !== "guest") return;
    const topic = topicFromSearch(window.location.search);
    if (!topic) return;
    started.current = true;
    window.history.replaceState(window.history.state, "", window.location.pathname);
    void submitText(topic);
  }, [identityReady, contextReady, lessonOpen, role, submitText]);
}
