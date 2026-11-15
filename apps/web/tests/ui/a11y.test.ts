import { readFileSync } from "node:fs";
import path from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import { reducedMotion, scrollBehavior } from "../../lib/motion";

const read = (rel: string) => readFileSync(path.resolve(__dirname, "../..", rel), "utf-8").split(String.fromCharCode(13)).join("");
const A11Y = read("app/a11y.css");

describe("reduced motion helper", () => {
  afterEach(() => {
    document.documentElement.removeAttribute("data-motion");
    vi.unstubAllGlobals();
  });
  const media = (matches: boolean) => vi.stubGlobal("matchMedia", () => ({ matches }));

  it("is false by default", () => {
    media(false);
    expect(reducedMotion()).toBe(false);
    expect(scrollBehavior()).toBe("smooth");
  });
  it("follows the device preference", () => {
    media(true);
    expect(reducedMotion()).toBe(true);
    expect(scrollBehavior()).toBe("auto");
  });
  it("follows the Comfort choice even when the device does not ask", () => {
    media(false);
    document.documentElement.setAttribute("data-motion", "reduce");
    expect(reducedMotion()).toBe(true);
  });
  it("the calm audience motion is not reduced motion", () => {
    media(false);
    document.documentElement.setAttribute("data-motion", "calm");
    expect(reducedMotion()).toBe(false);
  });
});

describe("accessibility stylesheet", () => {
  it("gives every interactive element a 3 px focus ring from the focus token", () => {
    expect(A11Y).toMatch(/:focus-visible\s*\{\s*outline:\s*3px solid var\(--s-focus-ring\)/);
    expect(A11Y).toContain("button");
    expect(A11Y).toContain("textarea");
  });
  it("stops looping animation under reduced motion (device and Comfort)", () => {
    expect(A11Y).toMatch(/@media \(prefers-reduced-motion: reduce\)[\s\S]*animation-iteration-count: 1 !important/);
    expect(A11Y).toMatch(/html\[data-motion="reduce"\][\s\S]*animation-iteration-count: 1 !important/);
  });
  it("uses a line height of at least 1.8 for every Indic language and never a forced Latin face", () => {
    expect(A11Y).toMatch(/:lang\(hi\), :lang\(ne\), :lang\(mr\), :lang\(bn\), :lang\(as\)\) \{\s*--lh-body: 1\.8/);
    expect(A11Y).toMatch(/"Noto Sans Devanagari"/);
    expect(A11Y).toMatch(/"Noto Sans Bengali"/);
    expect(A11Y).not.toMatch(/font-family:[^;]*(Inter|Geist|Georgia|Instrument)/);
    expect(A11Y).not.toMatch(/@font-face/); // no new web-font download
  });
});

describe("touch targets and type floor on the main screens", () => {
  const home = read("components/chat/ChatHome.module.css");

  it("the composer, chips, header buttons and panel buttons are at least the 44 px control size", () => {
    for (const cls of ["headerButton", "modeButton", "sendButton", "panelReview", "panelToday", "continueButton"]) {
      const block = new RegExp(String.raw`\.${cls}\s*\{[^}]*\}`).exec(home)?.[0] ?? "";
      expect(block, `.${cls}`).toMatch(/var\(--s-control-min\)/);
    }
    expect(home).toMatch(/button\[data-testid\^="language-"\]\)\s*\{[^}]*var\(--s-control-min\)/);
  });
  it("no label on the chat home is smaller than 12 px (0.75rem)", () => {
    for (const m of home.matchAll(/font-size:\s*(0?\.\d+)rem/g)) expect(Number(m[1]), m[0]).toBeGreaterThanOrEqual(0.75);
    for (const file of ["components/chat/Composer.tsx", "components/chat/RightPanel.tsx", "components/chat/IconSidebar.tsx", "components/ui/suggestion-card.tsx"]) {
      for (const m of read(file).matchAll(/text-\[(0\.\d+)rem\]/g)) expect(Number(m[1]), `${file} ${m[0]}`).toBeGreaterThanOrEqual(0.75);
    }
  });
  it("the icon rail controls are 44 px (size-11)", () => {
    const rail = read("components/chat/IconSidebar.tsx");
    expect(rail).not.toMatch(/\bsize-(7|8)\b[^"]*(cursor-pointer|place-items-center rounded-\[10px\])/);
  });
  it("announces async status: the thread is a polite log and a video job status is a status region", () => {
    expect(read("components/chat/Thread.tsx")).toMatch(/role="log" aria-live="polite"/);
    expect(read("components/chat/JobCard.tsx")).toMatch(/role="status"[^>]*>\{statusLabel\(job\)\}/);
  });
});
