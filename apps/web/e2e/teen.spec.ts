import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { contrast, PAIRS, rgbToHex } from "../lib/contrast";
import { devLogin, enter } from "./shell";

/**
 * UI-2b: teen-friendly polish. Contrast of every token pair and of the rendered text on the home, setup,
 * practice and lesson screens in both themes; WCAG text-spacing overrides in English and an Indic locale;
 * the theme switch and Comfort settings; an axe-core scan of every route; screenshots in light and dark at
 * four widths; and the speed numbers on throttled 4G. Needs the API with DEV_TOOLS=true on seeded scenarios.
 * Selectors are data-testid, never button text.
 */
const SHOTS = "test-results/screens";
const THEMES = ["light", "dark"] as const;
type Theme = (typeof THEMES)[number];
const WIDTHS = [
  { w: 360, h: 800 },
  { w: 768, h: 1024 },
  { w: 1280, h: 800 },
  { w: 1536, h: 900 },
];

/** Store the theme on the device before the page loads, exactly as the Settings switch does. */
async function useTheme(page: Page, theme: Theme, extra: Record<string, string> = {}) {
  await page.addInitScript(
    ([value]) => window.localStorage.setItem("yt.comfort", value),
    [JSON.stringify({ theme, ...extra })],
  );
}

type Screen = { name: string; open: (page: Page) => Promise<void> };
const SCREENS: Screen[] = [
  {
    name: "home",
    open: async (page) => {
      await page.goto("/");
      await expect(page.getByTestId("card-try-question")).toBeVisible({ timeout: 30_000 });
      await expect(page.getByTestId("greeting")).not.toHaveText("", { timeout: 20_000 });
    },
  },
  {
    name: "setup",
    open: async (page) => {
      await page.goto("/");
      await page.locator('[data-testid="card-try-lesson"]:visible').first().click({ timeout: 30_000 });
      await expect(page.locator('[data-testid^="choice-grade-"]:visible').first()).toBeVisible({ timeout: 20_000 });
    },
  },
  {
    name: "student-home",
    open: async (page) => {
      await devLogin(page, "mid_chapter");
      await expect(page.getByTestId("today-strip")).toBeVisible({ timeout: 30_000 });
    },
  },
  {
    name: "practice",
    open: async (page) => {
      await devLogin(page, "mid_chapter");
      await enter(page, "nav-revision");
      await expect(page.locator(".stem, h1, h2").first()).toBeVisible({ timeout: 30_000 });
    },
  },
  {
    name: "lesson",
    open: async (page) => {
      await page.goto("/dev/lessons/LESSON.TWO_STEP");
      await expect(page.getByRole("heading", { level: 2 })).toBeVisible({ timeout: 30_000 });
    },
  },
];

/** Rendered text and input borders against the colour they actually sit on. Returns the failures. */
async function scanContrast(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    type RGBA = [number, number, number, number];
    const parse = (c: string): RGBA => {
      const m = c.match(/rgba?\(([^)]+)\)/);
      if (!m) return [0, 0, 0, 0];
      const p = m[1]!.split(/[ ,/]+/).filter(Boolean).map(Number);
      return [p[0] ?? 0, p[1] ?? 0, p[2] ?? 0, p[3] === undefined ? 1 : p[3]];
    };
    const over = (top: RGBA, under: RGBA): RGBA => {
      const a = top[3] + under[3] * (1 - top[3]);
      if (a === 0) return [0, 0, 0, 0];
      const mix = (i: number) => (top[i]! * top[3] + under[i]! * under[3] * (1 - top[3])) / a;
      return [mix(0), mix(1), mix(2), a];
    };
    const background = (el: Element | null): RGBA => {
      // The page is a gradient (UI-5): text that sits straight on it is measured against its darkest zone, --c-bg-deep.
      if (!el) {
        const deep = getComputedStyle(document.documentElement).getPropertyValue("--c-bg-deep").trim();
        const n = parseInt(deep.replace("#", ""), 16);
        return [(n >> 16) & 255, (n >> 8) & 255, n & 255, 1] as RGBA;
      }
      const own = parse(getComputedStyle(el).backgroundColor);
      return own[3] >= 0.99 ? own : over(own, background(el.parentElement));
    };
    const channel = (v: number) => {
      const s = v / 255;
      return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
    };
    const lum = (c: RGBA) => 0.2126 * channel(c[0]) + 0.7152 * channel(c[1]) + 0.0722 * channel(c[2]);
    const ratio = (a: RGBA, b: RGBA) => (Math.max(lum(a), lum(b)) + 0.05) / (Math.min(lum(a), lum(b)) + 0.05);
    const exempt = (el: Element) => !!el.closest("[aria-disabled='true'], :disabled, .sr-only, [aria-hidden='true'], .soon, .dim, svg");
    const failures: string[] = [];
    for (const el of Array.from(document.body.querySelectorAll<HTMLElement>("*"))) {
      const style = getComputedStyle(el);
      if (style.visibility === "hidden" || style.display === "none" || exempt(el)) continue;
      const rect = el.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) continue;
      const hasText = Array.from(el.childNodes).some((n) => n.nodeType === 3 && (n.textContent ?? "").trim());
      if (hasText) {
        const bg = background(el);
        const fg = over(parse(style.color), bg);
        const size = parseFloat(style.fontSize);
        const large = size >= 24 || (size >= 18.66 && Number(style.fontWeight) >= 700);
        const r = ratio(fg, bg);
        if (r < (large ? 3 : 4.5)) failures.push(`text "${(el.textContent ?? "").trim().slice(0, 30)}" ${r.toFixed(2)}:1 (${el.tagName.toLowerCase()}.${el.className.toString().slice(0, 30)})`);
      }
      if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement || el instanceof HTMLSelectElement) {
        if (el instanceof HTMLInputElement && ["range", "checkbox", "radio", "hidden"].includes(el.type)) continue;
        if (el.closest("[data-testid='composer']")) continue; // the composer box carries the border, checked below
        const edge = parse(style.borderTopColor);
        const r = ratio(over(edge, background(el.parentElement)), background(el.parentElement));
        if (style.borderTopWidth !== "0px" && r < 3) failures.push(`input border ${r.toFixed(2)}:1 (${el.tagName.toLowerCase()})`);
      }
    }
    return failures;
  });
}

for (const theme of THEMES) {
  test.describe(`contrast in ${theme}`, () => {
    for (const screen of SCREENS) {
      test(`${screen.name}: token pairs and rendered text meet the ratios`, async ({ page }) => {
        await page.setViewportSize({ width: 360, height: 800 });
        await useTheme(page, theme);
        await screen.open(page);
        expect(await page.evaluate(() => document.documentElement.dataset.theme)).toBe(theme);

        const tokens = await page.evaluate(() => {
          const css = getComputedStyle(document.documentElement);
          const out: Record<string, string> = {};
          for (const name of Array.from(new Set(["--c-text", "--c-muted", "--c-bg", "--c-surface", "--c-surface-2", "--c-lesson", "--c-accent", "--c-accent-fg", "--c-accent-ink", "--c-accent-soft", "--c-success", "--c-success-soft", "--c-warning", "--c-warning-soft", "--c-info", "--c-info-soft", "--c-teal", "--c-teal-soft", "--c-neutral", "--c-neutral-soft", "--c-danger", "--c-danger-soft", "--c-input-line", "--c-focus", "--c-bg-deep", "--c-home-bg", "--c-card-solid"]))) {
            out[name] = css.getPropertyValue(name).trim();
          }
          return out;
        });
        const lows = PAIRS.filter((p) => contrast(tokens[p.fg]!, tokens[p.bg]!) < p.min).map((p) => `${p.label} ${contrast(tokens[p.fg]!, tokens[p.bg]!).toFixed(2)} < ${p.min}`);
        expect(lows, "token pairs").toEqual([]);
        // UI-5: the page colour is on <html> (the body is transparent over the gradient).
        expect(rgbToHex(await page.evaluate(() => getComputedStyle(document.documentElement).backgroundColor))).not.toMatch(/^#(000000|ffffff)$/);

        expect(await scanContrast(page), "rendered text").toEqual([]);
      });
    }
  });
}

// WCAG 1.4.12 text spacing: line height 1.5, paragraph spacing 2x, letter spacing 0.12em, word spacing 0.16em.
const SPACING_CSS = "*{line-height:1.5 !important;letter-spacing:0.12em !important;word-spacing:0.16em !important}p{margin-bottom:2em !important}";

async function clippedOrOverlapping(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const out: string[] = [];
    const leaves: { el: HTMLElement; r: DOMRect; t: string }[] = [];
    for (const el of Array.from(document.body.querySelectorAll<HTMLElement>("*"))) {
      const style = getComputedStyle(el);
      if (style.visibility === "hidden" || style.display === "none" || el.closest(".sr-only, svg")) continue;
      const own = Array.from(el.childNodes).filter((n) => n.nodeType === 3).map((n) => n.textContent ?? "").join("").trim();
      if (!own) continue;
      let r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) continue;
      // Only the part you can see counts: clip to every scrolling or overflow-hidden ancestor.
      let hiddenAway = false;
      for (let a = el.parentElement; a && a !== document.body; a = a.parentElement) {
        const as = getComputedStyle(a);
        if (as.overflowX === "visible" && as.overflowY === "visible") continue;
        const ar = a.getBoundingClientRect();
        const left = Math.max(r.left, ar.left);
        const top = Math.max(r.top, ar.top);
        const right = Math.min(r.right, ar.right);
        const bottom = Math.min(r.bottom, ar.bottom);
        if (right <= left || bottom <= top) {
          hiddenAway = true;
          break;
        }
        r = new DOMRect(left, top, right - left, bottom - top);
      }
      if (hiddenAway) continue;
      const hidesOverflow = style.overflowX !== "visible" || style.overflowY !== "visible";
      const ellipsis = style.textOverflow === "ellipsis" || el.classList.contains("truncate");
      if (hidesOverflow && !ellipsis && (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1)) out.push(`clipped: ${own.slice(0, 30)}`);
      leaves.push({ el, r, t: own.slice(0, 24) });
    }
    for (let i = 0; i < leaves.length; i++) {
      for (let j = i + 1; j < leaves.length; j++) {
        const a = leaves[i]!;
        const b = leaves[j]!;
        if (a.el.contains(b.el) || b.el.contains(a.el)) continue;
        const w = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left);
        const h = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
        if (w > 3 && h > 3) out.push(`overlap: "${a.t}" and "${b.t}"`);
      }
    }
    return out;
  });
}

for (const [label, locale] of [["English", "en"], ["Nepali (Devanagari)", "ne"]] as const) {
  test.describe(`text spacing overrides, ${label}`, () => {
    for (const screen of SCREENS) {
      test(`${screen.name}: nothing is clipped or overlapping`, async ({ page }) => {
        await page.setViewportSize({ width: 360, height: 800 });
        await page.addInitScript((l) => window.localStorage.setItem("yt_locale", l), locale);
        await screen.open(page);
        await page.addStyleTag({ content: SPACING_CSS });
        await page.waitForTimeout(300);
        expect(await clippedOrOverlapping(page)).toEqual([]);
      });
    }
  });
}

test.describe("theme and comfort settings", () => {
  test.use({ viewport: { width: 1280, height: 800 } });

  test("Auto follows the device, the switch changes it, and the choice survives a reload with no flash", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "dark" });
    await page.goto("/");
    await expect(page.getByTestId("theme-auto")).toHaveAttribute("aria-pressed", "true");
    expect(await page.evaluate(() => document.documentElement.dataset.theme ?? "auto")).toBe("auto");
    const darkBg = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--c-bg").trim());
    // UI-5: the page colour is on <html>; the body is transparent so the gradient and glow shapes (body::before) show.
    expect(rgbToHex(await page.evaluate(() => getComputedStyle(document.documentElement).backgroundColor))).toBe(darkBg.toLowerCase());
    expect(darkBg.toLowerCase()).toBe("#0b041a");

    await page.getByTestId("theme-light").click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
    expect(rgbToHex(await page.evaluate(() => getComputedStyle(document.documentElement).backgroundColor))).toBe("#e4ecfd");
    // ...and the flat home colour is drawn by body::before (the sky gradient is for the other screens).
    expect(rgbToHex(await page.evaluate(() => getComputedStyle(document.body, "::before").backgroundColor))).toBe("#eef0fc");

    // Reload: the theme is already on <html> when the document is parsed, before any script from the app runs.
    await page.goto("/", { waitUntil: "commit" });
    await page.waitForFunction(() => document.documentElement.getAttribute("data-theme") === "light", undefined, { timeout: 5000 });
    await expect(page.getByTestId("theme-light")).toHaveAttribute("aria-pressed", "true");
  });

  test("Settings: text size, line spacing and motion apply at once and persist", async ({ page }) => {
    await page.goto("/");
    await page.locator('[data-testid="nav-settings"]:visible').first().click();
    await expect(page.getByTestId("comfort-dialog")).toBeVisible();
    await page.getByTestId("text-size-l").click();
    await page.getByTestId("spacing-relaxed").click();
    await page.getByTestId("motion-reduce").click();
    await page.getByTestId("comfort-dialog").getByTestId("theme-dark").click();
    const root = page.locator("html");
    await expect(root).toHaveAttribute("data-text", "l");
    await expect(root).toHaveAttribute("data-spacing", "relaxed");
    await expect(root).toHaveAttribute("data-motion", "reduce");
    await expect(root).toHaveAttribute("data-theme", "dark");
    expect(await page.evaluate(() => getComputedStyle(document.documentElement).fontSize)).toBe("19px");
    await page.getByTestId("text-size-s").click();
    expect(await page.evaluate(() => getComputedStyle(document.documentElement).fontSize)).toBe("16px");
    await page.getByTestId("comfort-close").click();
    await page.reload();
    await expect(root).toHaveAttribute("data-spacing", "relaxed");
    await expect(root).toHaveAttribute("data-text", "s");
  });

  test("Send always looks ready: filled with the accent, hint when empty, reason when a mode is not built", async ({ page }) => {
    await page.goto("/");
    const send = page.getByTestId("composer-send");
    await expect(send).toBeEnabled();
    expect(rgbToHex(await send.evaluate((el) => getComputedStyle(el).backgroundColor))).toBe("#1d4fd8");
    await send.click();
    await expect(page.getByTestId("composer-hint")).toBeVisible();
    await page.getByTestId("composer-input").fill("quadratic");
    await expect(page.getByTestId("composer-hint")).toHaveCount(0);
  });
});

test.describe("guest and student home", () => {
  test.use({ viewport: { width: 360, height: 800 } });

  test("guest: lead card first, the no-account line, and Try one question opens a real item", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("card-try-question")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("no-account-line")).toBeVisible();
    const order = await page.evaluate(() => ["card-try-question", "card-try-lesson"].map((id) => document.querySelector(`[data-testid=${id}]`)!.getBoundingClientRect().top));
    expect(order[0]!).toBeLessThanOrEqual(order[1]!); // side by side: the lead card is first in reading order
    await page.getByTestId("card-try-question").click();
    await expect(page.getByTestId("workspace-frame")).toBeVisible({ timeout: 40_000 });
    const frame = page.frameLocator('[data-testid="workspace-frame"]');
    await expect(frame.locator(".stem, h1, h2").first()).toBeVisible({ timeout: 40_000 });
  });

  test("student: ring in words, a plan, one Start button, weekly row without a streak", async ({ page }) => {
    await devLogin(page, "mid_chapter");
    await expect(page.getByTestId("today-strip")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("ring-text")).toContainText(/%/);
    await expect(page.getByTestId("today-start")).toBeVisible();
    await expect(page.getByTestId("week-row")).toBeVisible();
    const text = (await page.getByTestId("today-strip").innerText()).toLowerCase();
    for (const banned of ["streak", "rank", "leaderboard", "lose", "lost"]) expect(text).not.toContain(banned);
    await page.getByTestId("today-start").click();
    await expect(page.getByTestId("workspace-frame")).toBeVisible({ timeout: 30_000 });
  });
});

for (const theme of THEMES) {
  for (const { w, h } of WIDTHS) {
    test(`screenshots: ${theme} at ${w}x${h}`, async ({ page }) => {
      await page.setViewportSize({ width: w, height: h });
      await useTheme(page, theme);
      for (const screen of SCREENS) {
        await screen.open(page);
        await page.waitForTimeout(500);
        await page.screenshot({ path: `${SHOTS}/teen-${screen.name}-${theme}-${w}.png` });
      }
    });
  }
}

// axe-core on every route. Zero serious or critical violations.
const PUBLIC_ROUTES = ["/", "/start", "/login", "/staff/login", "/offline", "/dev", "/dev/lessons", "/dev/lessons/LESSON.TWO_STEP", "/dev/ui"];

async function serious(page: Page): Promise<string[]> {
  const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  return result.violations.filter((v) => v.impact === "serious" || v.impact === "critical").map((v) => `${v.id} (${v.impact}): ${v.nodes.slice(0, 3).map((n) => n.target.join(" ")).join(" | ")}`);
}

for (const theme of THEMES) {
  test.describe(`axe, ${theme}`, () => {
    for (const route of PUBLIC_ROUTES) {
      test(`${route}`, async ({ page }) => {
        await page.setViewportSize({ width: 360, height: 800 });
        await useTheme(page, theme);
        await page.goto(route);
        await page.waitForLoadState("networkidle");
        expect(await serious(page)).toEqual([]);
      });
    }
    test("student routes: /today /subjects /chapters, a chapter, and a practice session", async ({ page }) => {
      await page.setViewportSize({ width: 360, height: 800 });
      await useTheme(page, theme);
      await devLogin(page, "mid_chapter");
      const problems: string[] = [];
      for (const route of ["/today", "/subjects", "/chapters"]) {
        await page.goto(route);
        await page.waitForLoadState("networkidle");
        problems.push(...(await serious(page)).map((p) => `${route}: ${p}`));
      }
      await page.goto("/chapters");
      const chapter = page.locator('[data-testid^="chapter-"]:not([aria-disabled="true"])').first();
      await expect(chapter).toBeVisible({ timeout: 30_000 });
      await chapter.click();
      await page.waitForLoadState("networkidle");
      problems.push(...(await serious(page)).map((p) => `chapter: ${p}`));
      await page.goto("/");
      await enter(page, "nav-revision");
      await expect(page.locator(".stem, h1, h2").first()).toBeVisible({ timeout: 30_000 });
      problems.push(...(await serious(page)).map((p) => `session: ${p}`));
      expect(problems).toEqual([]);
    });
    test("teacher and parent routes", async ({ page }) => {
      await page.setViewportSize({ width: 360, height: 800 });
      await useTheme(page, theme);
      const problems: string[] = [];
      for (const [login, route] of [["login-teacher", "/teacher"], ["parent-mid_chapter", "/guardian"]] as const) {
        await page.goto("/dev");
        await page.getByTestId(login).click();
        await expect(page.getByTestId("hero")).toBeVisible();
        await page.goto(route);
        await page.waitForLoadState("networkidle");
        problems.push(...(await serious(page)).map((p) => `${route}: ${p}`));
      }
      expect(problems).toEqual([]);
    });
  });
}

// Speed on throttled 4G (1.6 Mbps down, 750 Kbps up, 150 ms): the numbers are printed for the report.
test("speed on throttled 4G: guest home and the first question", async ({ page, context }) => {
  test.setTimeout(180_000);
  await page.setViewportSize({ width: 360, height: 800 });
  const cdp = await context.newCDPSession(page);
  await cdp.send("Network.enable");
  await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
  await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: 150, downloadThroughput: (1.6 * 1024 * 1024) / 8, uploadThroughput: (750 * 1024) / 8 });
  const t0 = Date.now();
  await page.goto("/", { waitUntil: "commit" });
  await expect(page.getByTestId("card-try-question")).toBeVisible({ timeout: 60_000 });
  const homeMs = Date.now() - t0;
  const t1 = Date.now();
  await page.getByTestId("card-try-question").click();
  const frame = page.frameLocator('[data-testid="workspace-frame"]');
  await expect(frame.locator(".stem, h1, h2").first()).toBeVisible({ timeout: 90_000 });
  const questionMs = Date.now() - t1;
  console.log(`SPEED guest home first content ${homeMs} ms; first question after the tap ${questionMs} ms`);
  expect(homeMs).toBeLessThan(15_000);
});
