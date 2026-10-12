import type { Setup } from "./machine";

/** What a guest chose, kept on this device only (never sent anywhere). Every access is guarded: storage can be blocked. */
const SETUP_KEY = "yt_chat_setup";
const TIP_KEY = "yt_chat_tip_dismissed";

function store(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

export function loadSetup(): Setup | null {
  try {
    const raw = store()?.getItem(SETUP_KEY);
    return raw ? (JSON.parse(raw) as Setup) : null;
  } catch {
    return null;
  }
}

export function saveSetup(setup: Setup): void {
  try {
    store()?.setItem(SETUP_KEY, JSON.stringify(setup));
  } catch {
    /* storage is optional */
  }
}

export function clearSetup(): void {
  try {
    store()?.removeItem(SETUP_KEY);
  } catch {
    /* storage is optional */
  }
}

export function tipDismissed(): boolean {
  try {
    return store()?.getItem(TIP_KEY) === "1";
  } catch {
    return false;
  }
}

export function dismissTip(): void {
  try {
    store()?.setItem(TIP_KEY, "1");
  } catch {
    /* storage is optional */
  }
}
