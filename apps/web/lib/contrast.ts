/**
 * WCAG contrast maths and the list of colour pairs the design system promises (UI-2b). Pure functions, used by
 * the token unit test and by the Playwright computed-style test, so the rule has one definition.
 */
export const THEMES = ["light", "dark"] as const;
export type Theme = (typeof THEMES)[number];

export type Pair = { fg: string; bg: string; min: number; label: string };

/** Text 4.5:1; body and muted text 7:1; borders, focus rings and meaningful icons 3:1. */
export const PAIRS: Pair[] = [
  { fg: "--c-text", bg: "--c-bg", min: 7, label: "text on page" },
  { fg: "--c-text", bg: "--c-surface", min: 7, label: "text on card" },
  { fg: "--c-text", bg: "--c-surface-2", min: 7, label: "text on raised surface" },
  { fg: "--c-muted", bg: "--c-bg", min: 7, label: "muted text on page" },
  { fg: "--c-muted", bg: "--c-surface", min: 7, label: "muted text on card" },
  { fg: "--c-muted", bg: "--c-surface-2", min: 7, label: "muted text on raised surface" },
  { fg: "--c-text", bg: "--c-home-bg", min: 7, label: "text on the flat home page" },
  { fg: "--c-muted", bg: "--c-home-bg", min: 7, label: "muted text on the flat home page" },
  { fg: "--c-text", bg: "--c-card-solid", min: 7, label: "text on a solid home card" },
  { fg: "--c-muted", bg: "--c-card-solid", min: 7, label: "muted text on a solid home card" },
  { fg: "--c-text", bg: "--c-bg-deep", min: 7, label: "text on the darkest page zone" },
  { fg: "--c-muted", bg: "--c-bg-deep", min: 4.5, label: "muted text on the darkest page zone (6.9 measured)" },
  { fg: "--c-text", bg: "--c-lesson", min: 7, label: "text on lesson surface" },
  { fg: "--c-muted", bg: "--c-lesson", min: 7, label: "muted text on lesson surface" },
  { fg: "--c-accent-ink", bg: "--c-lesson", min: 4.5, label: "accent text on lesson surface" },
  { fg: "--c-success", bg: "--c-lesson", min: 4.5, label: "ok text on lesson surface" },
  { fg: "--c-warning", bg: "--c-lesson", min: 4.5, label: "warn text on lesson surface" },
  { fg: "--c-input-line", bg: "--c-lesson", min: 3, label: "input border on lesson surface" },
  { fg: "--c-focus", bg: "--c-lesson", min: 3, label: "focus ring on lesson surface" },
  { fg: "--c-accent-fg", bg: "--c-accent", min: 4.5, label: "button label on accent" },
  { fg: "--c-accent-ink", bg: "--c-bg", min: 4.5, label: "accent text on page" },
  { fg: "--c-accent-ink", bg: "--c-surface", min: 4.5, label: "accent text on card" },
  { fg: "--c-accent-ink", bg: "--c-accent-soft", min: 4.5, label: "accent text on tint" },
  { fg: "--c-success", bg: "--c-success-soft", min: 4.5, label: "ok text on its tint" },
  { fg: "--c-warning", bg: "--c-warning-soft", min: 4.5, label: "warn text on its tint" },
  { fg: "--c-info", bg: "--c-info-soft", min: 4.5, label: "info text on its tint" },
  { fg: "--c-teal", bg: "--c-teal-soft", min: 4.5, label: "teal text on its tint" },
  { fg: "--c-teal", bg: "--c-surface", min: 4.5, label: "teal text on card" },
  { fg: "--c-info", bg: "--c-bg", min: 4.5, label: "info text on page" },
  { fg: "--c-teal", bg: "--c-teal-soft", min: 3, label: "teal icon on its tint" },
  { fg: "--c-neutral", bg: "--c-neutral-soft", min: 4.5, label: "neutral text on its tint" },
  { fg: "--c-danger", bg: "--c-danger-soft", min: 4.5, label: "error text on its tint" },
  { fg: "--c-success", bg: "--c-surface", min: 4.5, label: "ok text on card" },
  { fg: "--c-warning", bg: "--c-surface", min: 4.5, label: "warn text on card" },
  { fg: "--c-info", bg: "--c-surface", min: 4.5, label: "info text on card" },
  { fg: "--c-danger", bg: "--c-surface", min: 4.5, label: "error text on card" },
  { fg: "--c-input-line", bg: "--c-bg", min: 3, label: "input border on page" },
  { fg: "--c-input-line", bg: "--c-surface", min: 3, label: "input border on card" },
  { fg: "--c-focus", bg: "--c-bg", min: 3, label: "focus ring on page" },
  { fg: "--c-focus", bg: "--c-surface", min: 3, label: "focus ring on card" },
  { fg: "--c-focus", bg: "--c-surface-2", min: 3, label: "focus ring on raised surface" },
  { fg: "--c-success", bg: "--c-success-soft", min: 3, label: "ok icon on its tint" },
  { fg: "--c-warning", bg: "--c-warning-soft", min: 3, label: "warn icon on its tint" },
  { fg: "--c-info", bg: "--c-info-soft", min: 3, label: "info icon on its tint" },
];

function channel(v: number): number {
  const s = v / 255;
  return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
}

export function luminance(hex: string): number {
  const h = hex.replace("#", "");
  const full = h.length === 3 ? h.split("").map((c) => c + c).join("") : h;
  const n = parseInt(full, 16);
  return 0.2126 * channel((n >> 16) & 255) + 0.7152 * channel((n >> 8) & 255) + 0.0722 * channel(n & 255);
}

export function contrast(a: string, b: string): number {
  const la = luminance(a);
  const lb = luminance(b);
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
}

/** Parse `rgb(r, g, b)` or `rgba(...)` from getComputedStyle into a hex string (alpha is ignored). */
export function rgbToHex(rgb: string): string {
  const m = rgb.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
  if (!m) return "#000000";
  return "#" + [m[1], m[2], m[3]].map((x) => Number(x).toString(16).padStart(2, "0")).join("");
}

/** Read the token values of one theme out of tokens.css (the light block, or one of the two dark blocks). */
export function readTheme(css: string, theme: Theme, dark: "auto" | "forced" = "forced"): Record<string, string> {
  let block: string;
  if (theme === "light") {
    block = css.slice(css.indexOf(":root,"), css.indexOf("@media (prefers-color-scheme: dark)"));
  } else if (dark === "auto") {
    const start = css.indexOf("@media (prefers-color-scheme: dark)");
    block = css.slice(start, css.indexOf('[data-theme="dark"] {'));
  } else {
    const start = css.indexOf('[data-theme="dark"] {');
    block = css.slice(start, css.indexOf("/* Comfort settings"));
  }
  const out: Record<string, string> = {};
  for (const m of block.matchAll(/(--c-[a-z0-9-]+):\s*(#[0-9a-fA-F]{3,6})\s*;/g)) out[m[1]] = m[2].toLowerCase();
  return out;
}

/** The semantic layer (app/semantic.css): the same promises, written with the names components use. */
export const SEMANTIC_PAIRS: Pair[] = [
  { fg: "--s-text-default", bg: "--s-surface-page", min: 7, label: "text default on page" },
  { fg: "--s-text-default", bg: "--s-surface-card", min: 7, label: "text default on card" },
  { fg: "--s-text-default", bg: "--s-surface-raised", min: 7, label: "text default on raised" },
  { fg: "--s-text-subtle", bg: "--s-surface-page", min: 7, label: "text subtle on page" },
  { fg: "--s-text-subtle", bg: "--s-surface-card", min: 7, label: "text subtle on card" },
  { fg: "--s-text-subtle", bg: "--s-surface-raised", min: 7, label: "text subtle on raised" },
  { fg: "--s-text-default", bg: "--s-surface-lesson", min: 7, label: "text default on lesson" },
  { fg: "--s-text-action", bg: "--s-surface-page", min: 4.5, label: "action text on page" },
  { fg: "--s-text-action", bg: "--s-surface-card", min: 4.5, label: "action text on card" },
  { fg: "--s-text-action", bg: "--s-surface-lesson", min: 4.5, label: "action text on lesson" },
  { fg: "--s-text-action", bg: "--s-action-soft", min: 4.5, label: "action text on its tint" },
  { fg: "--s-action-primary-fg", bg: "--s-action-primary", min: 4.5, label: "primary button label" },
  { fg: "--s-border-control", bg: "--s-surface-page", min: 3, label: "control border on page" },
  { fg: "--s-border-control", bg: "--s-surface-card", min: 3, label: "control border on card" },
  { fg: "--s-focus-ring", bg: "--s-surface-page", min: 3, label: "focus ring on page" },
  { fg: "--s-focus-ring", bg: "--s-surface-card", min: 3, label: "focus ring on card" },
  { fg: "--s-focus-ring", bg: "--s-surface-raised", min: 3, label: "focus ring on raised" },
  { fg: "--s-focus-ring", bg: "--s-surface-lesson", min: 3, label: "focus ring on lesson" },
  { fg: "--s-action-primary", bg: "--s-surface-page", min: 3, label: "primary fill on page (non-text)" },
  ...(["success", "warning", "info", "danger"] as const).flatMap((k): Pair[] => [
    { fg: `--s-status-${k}-fg`, bg: `--s-status-${k}-bg`, min: 4.5, label: `${k} text on its tint` },
    { fg: `--s-status-${k}-fg`, bg: "--s-surface-card", min: 4.5, label: `${k} text on card` },
  ]),
];

/** Audience themes in app/semantic.css, in the order school (no overrides), college, work. */
export const AUDIENCE_NAMES = ["school", "college", "work"] as const;
export type AudienceName = (typeof AUDIENCE_NAMES)[number];

function declarations(block: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const m of block.matchAll(/(--[a-z0-9-]+):\s*([^;]+);/g)) out[m[1]] = m[2].trim().toLowerCase();
  return out;
}

/** The --c-* values an audience overrides for one theme, read from semantic.css. School overrides nothing. */
export function readAudienceOverrides(semanticCss: string, audience: AudienceName, theme: Theme): Record<string, string> {
  if (audience === "school") return {};
  const sel = `html[data-audience="${audience}"]`;
  const open = theme === "light" ? `${sel}:not([data-theme="dark"]) {` : `${sel}[data-theme="dark"] {`;
  const at = semanticCss.indexOf(open);
  if (at < 0) throw new Error(`semantic.css has no ${theme} block for ${audience}`);
  const body = semanticCss.slice(at + open.length, semanticCss.indexOf("}", at));
  const own = declarations(body);
  if (theme === "dark") {
    // The OS-dark copy inside the media query must hold the same values as the forced dark block.
    const auto = `@media (prefers-color-scheme: dark) {\n  ${sel}:not([data-theme="light"]) {`;
    const aAt = semanticCss.indexOf(auto);
    if (aAt < 0) throw new Error(`semantic.css has no auto-dark block for ${audience}`);
    const autoOwn = declarations(semanticCss.slice(aAt + auto.length, semanticCss.indexOf("}", aAt + auto.length)));
    if (JSON.stringify(autoOwn) !== JSON.stringify(own)) throw new Error(`${audience}: auto dark and forced dark differ`);
  }
  return own;
}

/** Every token of a theme with the semantic aliases resolved to hex. */
export function resolveTokens(base: Record<string, string>, overrides: Record<string, string>, semanticCss: string): Record<string, string> {
  const merged = { ...base, ...overrides };
  const root = semanticCss.slice(semanticCss.indexOf(":root {"), semanticCss.indexOf("}", semanticCss.indexOf(":root {")));
  for (const [name, value] of Object.entries(declarations(root))) {
    const ref = /^var\((--[a-z0-9-]+)\)$/.exec(value);
    if (ref && merged[ref[1]]) merged[name] = merged[ref[1]];
  }
  return merged;
}
