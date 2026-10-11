export type BandUi = {
  band_id: string;
  read_aloud_default: boolean;
  target_size: "normal" | "large";
  choice: string;
};

const READ_ALOUD_KEY = "yt.readAloud";

/** Body classes for the student's grade band: `band-<id>` and `target-<size>`. */
export function bodyClasses(ui: BandUi | undefined): string[] {
  return ui ? [`band-${ui.band_id}`, `target-${ui.target_size}`] : [];
}

/** Read aloud follows the band default until the student chooses on or off. */
export function readAloudOn(ui: BandUi | undefined, stored: string | null): boolean {
  if (stored === "on") return true;
  if (stored === "off") return false;
  return Boolean(ui?.read_aloud_default);
}

export function storedReadAloud(): string | null {
  try {
    return window.localStorage.getItem(READ_ALOUD_KEY);
  } catch {
    return null;
  }
}

export function storeReadAloud(on: boolean): void {
  try {
    window.localStorage.setItem(READ_ALOUD_KEY, on ? "on" : "off");
  } catch {
    /* private mode: the choice just lasts this page */
  }
}

/** Speak the text in the student's language. False when speech is unavailable or there is no text. */
export function speak(text: string, lang: string, synth: SpeechSynthesis | undefined): boolean {
  if (!synth || !text.trim() || typeof SpeechSynthesisUtterance === "undefined") return false;
  synth.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang;
  synth.speak(utterance);
  return true;
}

const UI_KEY = "yt.ui";

export function saveUi(ui: BandUi | undefined): void {
  try {
    if (ui) window.sessionStorage.setItem(UI_KEY, JSON.stringify(ui));
  } catch {
    /* storage blocked: pages fall back to the normal style */
  }
}

export function loadUi(): BandUi | undefined {
  try {
    const raw = window.sessionStorage.getItem(UI_KEY);
    return raw ? (JSON.parse(raw) as BandUi) : undefined;
  } catch {
    return undefined;
  }
}

/** Put the band classes on <body>, replacing any earlier band or target class. */
export function applyBodyClasses(ui: BandUi | undefined): void {
  const body = document.body;
  Array.from(body.classList)
    .filter((c) => c.startsWith("band-") || c.startsWith("target-"))
    .forEach((c) => body.classList.remove(c));
  bodyClasses(ui).forEach((c) => body.classList.add(c));
}
