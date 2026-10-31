"use client";

import { useSyncExternalStore } from "react";

/**
 * Theme and Comfort settings (UI-2b). They live on the device only (localStorage), are applied to <html> as
 * data attributes and take effect without a reload. An inline script in app/layout.tsx applies the saved
 * values before first paint so the wrong theme never flashes.
 */
export type ThemeChoice = "auto" | "light" | "dark";
export type TextSize = "s" | "m" | "l";
export type Spacing = "normal" | "relaxed";
export type Motion = "auto" | "reduce";
export type Paper = "plain" | "grid";
/** Visual effects: "auto" shows glass and glow shapes unless the device asks for less (data saver, very low memory). */
export type Effects = "auto" | "reduce";
export type Comfort = { theme: ThemeChoice; text: TextSize; spacing: Spacing; motion: Motion; paper: Paper; effects: Effects };

export const COMFORT_KEY = "yt.comfort";
export const DEFAULT_COMFORT: Comfort = { theme: "auto", text: "m", spacing: "normal", motion: "auto", paper: "plain", effects: "auto" };

const pick = <T extends string>(value: unknown, allowed: readonly T[], fallback: T): T =>
  allowed.includes(value as T) ? (value as T) : fallback;

/** Parse the stored JSON; anything unknown or damaged falls back to the default for that field. */
export function parseComfort(raw: string | null): Comfort {
  let data: Record<string, unknown> = {};
  try {
    const parsed = raw ? JSON.parse(raw) : {};
    if (parsed && typeof parsed === "object") data = parsed as Record<string, unknown>;
  } catch {
    /* damaged value: use defaults */
  }
  return {
    theme: pick(data.theme, ["auto", "light", "dark"], DEFAULT_COMFORT.theme),
    text: pick(data.text, ["s", "m", "l"], DEFAULT_COMFORT.text),
    spacing: pick(data.spacing, ["normal", "relaxed"], DEFAULT_COMFORT.spacing),
    motion: pick(data.motion, ["auto", "reduce"], DEFAULT_COMFORT.motion),
    paper: pick(data.paper, ["plain", "grid"], DEFAULT_COMFORT.paper),
    effects: pick(data.effects, ["auto", "reduce"], DEFAULT_COMFORT.effects),
  };
}

export function readComfort(): Comfort {
  try {
    return parseComfort(window.localStorage.getItem(COMFORT_KEY));
  } catch {
    return DEFAULT_COMFORT;
  }
}

/** Low-power hints from the browser: the data-saver flag, or 1 GB of memory or less. Missing hints mean "no". */
export function deviceWantsReducedEffects(nav: { connection?: { saveData?: boolean }; deviceMemory?: number } | undefined): boolean {
  if (!nav) return false;
  return nav.connection?.saveData === true || (typeof nav.deviceMemory === "number" && nav.deviceMemory <= 1);
}

/** Put the settings on <html>. Auto means "no attribute": the CSS follows the device. */
export function applyComfort(c: Comfort, root: HTMLElement = document.documentElement): void {
  const set = (name: string, value: string | null) => (value === null ? root.removeAttribute(name) : root.setAttribute(name, value));
  set("data-theme", c.theme === "auto" ? null : c.theme);
  set("data-text", c.text === "m" ? null : c.text);
  set("data-spacing", c.spacing === "normal" ? null : c.spacing);
  set("data-motion", c.motion === "auto" ? null : c.motion);
  set("data-paper", c.paper === "plain" ? null : c.paper);
  const reduced = c.effects === "reduce" || (typeof navigator !== "undefined" && deviceWantsReducedEffects(navigator as never));
  set("data-effects", reduced ? "reduce" : null);
}

export function saveComfort(c: Comfort): void {
  try {
    window.localStorage.setItem(COMFORT_KEY, JSON.stringify(c));
  } catch {
    /* storage can be blocked: the choice still applies for this visit */
  }
}

/**
 * Runs in <head> before the page paints. Keep it tiny and free of dependencies. It also sets the document language
 * from the saved choice (so the right type rules apply on the first paint) and preloads only the Latin font files
 * used above the fold; a Hindi reader skips them (the Devanagari faces load later, see components/FontLoader).
 */
export const COMFORT_INIT_SCRIPT = `(function(){var d=document.documentElement;try{var c=JSON.parse(localStorage.getItem("${COMFORT_KEY}")||"{}");if(c.theme==="light"||c.theme==="dark")d.setAttribute("data-theme",c.theme);if(c.text==="s"||c.text==="l")d.setAttribute("data-text",c.text);if(c.spacing==="relaxed")d.setAttribute("data-spacing","relaxed");if(c.motion==="reduce")d.setAttribute("data-motion","reduce");if(c.paper==="grid")d.setAttribute("data-paper","grid");var n=navigator,k=n.connection;if(c.effects==="reduce"||(k&&k.saveData===true)||(typeof n.deviceMemory==="number"&&n.deviceMemory<=1))d.setAttribute("data-effects","reduce")}catch(e){}try{var l=localStorage.getItem("yt_locale");if(l==="hi")d.lang="hi";else{["geist-latin-300","geist-latin-400","geist-latin-500"].forEach(function(f){var a=document.createElement("link");a.rel="preload";a.setAttribute("as","font");a.type="font/woff2";a.setAttribute("crossorigin","anonymous");a.href="/fonts/"+f+".woff2";document.head.appendChild(a)})}}catch(e){}})();`;

// One store for the whole page: every control (sidebar switch, Settings dialog) reads and writes the same
// value, so changing one setting never undoes another.
let store: Comfort = DEFAULT_COMFORT;
let loaded = false;
const listeners = new Set<() => void>();

function ensureLoaded() {
  if (!loaded && typeof window !== "undefined") {
    loaded = true;
    store = readComfort();
  }
}

export function updateComfort(patch: Partial<Comfort>): void {
  ensureLoaded();
  store = { ...store, ...patch };
  applyComfort(store);
  saveComfort(store);
  listeners.forEach((listener) => listener());
}

/** Forget the cached value (tests only). */
export function resetComfortStore(): void {
  store = DEFAULT_COMFORT;
  loaded = false;
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void) {
  ensureLoaded();
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useComfort(): [Comfort, (patch: Partial<Comfort>) => void] {
  const comfort = useSyncExternalStore(subscribe, () => (ensureLoaded(), store), () => DEFAULT_COMFORT);
  return [comfort, updateComfort];
}
