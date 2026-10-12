"use client";

import { useCallback, useEffect, useState } from "react";

/**
 * Theme and Comfort settings (UI-2b). They live on the device only (localStorage), are applied to <html> as
 * data attributes and take effect without a reload. An inline script in app/layout.tsx applies the saved
 * values before first paint so the wrong theme never flashes.
 */
export type ThemeChoice = "auto" | "light" | "dark";
export type TextSize = "s" | "m" | "l";
export type Spacing = "normal" | "relaxed";
export type Motion = "auto" | "reduce";
export type Comfort = { theme: ThemeChoice; text: TextSize; spacing: Spacing; motion: Motion };

export const COMFORT_KEY = "yt.comfort";
export const DEFAULT_COMFORT: Comfort = { theme: "auto", text: "m", spacing: "normal", motion: "auto" };

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
  };
}

export function readComfort(): Comfort {
  try {
    return parseComfort(window.localStorage.getItem(COMFORT_KEY));
  } catch {
    return DEFAULT_COMFORT;
  }
}

/** Put the settings on <html>. Auto means "no attribute": the CSS follows the device. */
export function applyComfort(c: Comfort, root: HTMLElement = document.documentElement): void {
  const set = (name: string, value: string | null) => (value === null ? root.removeAttribute(name) : root.setAttribute(name, value));
  set("data-theme", c.theme === "auto" ? null : c.theme);
  set("data-text", c.text === "m" ? null : c.text);
  set("data-spacing", c.spacing === "normal" ? null : c.spacing);
  set("data-motion", c.motion === "auto" ? null : c.motion);
}

export function saveComfort(c: Comfort): void {
  try {
    window.localStorage.setItem(COMFORT_KEY, JSON.stringify(c));
  } catch {
    /* storage can be blocked: the choice still applies for this visit */
  }
}

/** Runs in <head> before the page paints. Keep it tiny and free of dependencies. */
export const COMFORT_INIT_SCRIPT = `(function(){try{var c=JSON.parse(localStorage.getItem("${COMFORT_KEY}")||"{}");var d=document.documentElement;if(c.theme==="light"||c.theme==="dark")d.setAttribute("data-theme",c.theme);if(c.text==="s"||c.text==="l")d.setAttribute("data-text",c.text);if(c.spacing==="relaxed")d.setAttribute("data-spacing","relaxed");if(c.motion==="reduce")d.setAttribute("data-motion","reduce")}catch(e){}})();`;

export function useComfort(): [Comfort, (patch: Partial<Comfort>) => void] {
  const [comfort, setComfort] = useState<Comfort>(DEFAULT_COMFORT);
  useEffect(() => setComfort(readComfort()), []);
  const update = useCallback((patch: Partial<Comfort>) => {
    setComfort((current) => {
      const next = { ...current, ...patch };
      applyComfort(next);
      saveComfort(next);
      return next;
    });
  }, []);
  return [comfort, update];
}
