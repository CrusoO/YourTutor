"use client";

import { useSyncExternalStore } from "react";
import localeRegistry from "../../../packages/shared/generated/locales.json";
import { t, type Messages } from "./messages";

/**
 * The language of the interface (UI-5: English and Hindi are the launch languages). The choice lives on the device
 * only (localStorage "yt_locale"), takes effect without a reload and never moves the student off the screen they
 * are on. Locales that the registry does not mark `active` ("coming soon") can be shown but never selected.
 */
export const LOCALE_KEY = "yt_locale";

export type LocaleRow = (typeof localeRegistry.locales)[number];

/** Each live language in its own script, so a student who cannot read the current language can still find theirs. */
const NATIVE_NAME: Record<string, string> = { en: "English", hi: "हिन्दी" };

export const LIVE_LOCALES: string[] = localeRegistry.locales.filter((row) => row.status === "active").map((row) => row.code);
export const DEFAULT_LOCALE: string = localeRegistry.default;

export function isLiveLocale(code: unknown): code is string {
  return typeof code === "string" && LIVE_LOCALES.includes(code);
}

export function nativeName(code: string): string {
  return NATIVE_NAME[code] ?? localeRegistry.locales.find((row) => row.code === code)?.name ?? code;
}

function read(): string {
  try {
    const stored = window.localStorage.getItem(LOCALE_KEY);
    return isLiveLocale(stored) ? stored : DEFAULT_LOCALE;
  } catch {
    return DEFAULT_LOCALE;
  }
}

let current: string = DEFAULT_LOCALE;
let loaded = false;
const listeners = new Set<() => void>();

function ensureLoaded() {
  if (!loaded && typeof window !== "undefined") {
    loaded = true;
    current = read();
  }
}

/** The active interface language (always a live one). Safe to call from event handlers and effects. */
export function currentLocale(): string {
  ensureLoaded();
  return current;
}

/** Change the language. Anything that is not a live locale is ignored. */
export function setLocale(code: string): void {
  if (!isLiveLocale(code)) return;
  ensureLoaded();
  current = code;
  try {
    window.localStorage.setItem(LOCALE_KEY, code);
  } catch {
    /* storage can be blocked: the choice still applies for this visit */
  }
  if (typeof document !== "undefined") document.documentElement.lang = code;
  listeners.forEach((fn) => fn());
}

/** Another tab, or the workspace frame beside the chat, changed the language: follow it. */
function onStorage(event: StorageEvent) {
  if (event.key !== LOCALE_KEY) return;
  current = read();
  if (typeof document !== "undefined") document.documentElement.lang = current;
  listeners.forEach((fn) => fn());
}

function subscribe(fn: () => void) {
  if (listeners.size === 0 && typeof window !== "undefined") window.addEventListener("storage", onStorage);
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
    if (listeners.size === 0 && typeof window !== "undefined") window.removeEventListener("storage", onStorage);
  };
}

/** Reactive language. The server render and the first client render are English, then the saved choice applies. */
export function useLocale(): string {
  return useSyncExternalStore(subscribe, currentLocale, () => DEFAULT_LOCALE);
}

/** The interface strings for the active language (English wherever a Hindi string is missing or unreviewed). */
export function useCopy(): Messages {
  return t(useLocale());
}
