import { expect, test, type Page } from "@playwright/test";
import { devLogin, enter } from "./shell";

/**
 * UI-5: the new identity (sky-glass light, violet dark) and the launch languages (English and Hindi).
 *  - Hindi type: conjunct-heavy headline and a mixed line at 360, 390 and 1280 px in both themes; fails on a
 *    clipped matra, overlapping lines, uppercase, negative tracking, a monospace face or a synthesised bold/italic.
 *  - The language switch keeps the student on the same screen and the choice survives a reload.
 *  - Screenshots of home, setup, lesson and practice in English and Hindi, light and dark: test-results/screens/id-*.
 *  - Blur budget (at most four blurred surfaces) and Reduce effects.
 * Preview server needs NEXT_PUBLIC_SHOW_DRAFT_LOCALES=true so the draft Hindi strings show (playwright.config sets it).
 */
const SHOTS = "test-results/screens";
const THEMES = ["light", "dark"] as const;
const LANGS = ["en", "hi"] as const;
type Theme = (typeof THEMES)[number];
type Lang = (typeof LANGS)[number];

/** Seed the device: theme (and extras) and, unless `lang` is null, the language. A switch test passes null so a
 *  reload keeps what the student chose instead of being reset by this script. */
async function prefs(page: Page, theme: Theme, lang: Lang | null, extra: Record<string, string> = {}) {
  await page.addInitScript(
    ([comfort, language]) => {
      window.localStorage.setItem("yt.comfort", comfort!);
      if (language) window.localStorage.setItem("yt_locale", language);
    },
    [JSON.stringify({ theme, ...extra }), lang ?? ""],
  );
}

async function fontsReady(page: Page) {
  await page.evaluate(() => document.fonts.ready.then(() => undefined));
  await page.waitForTimeout(300);
}

/** Ink height of a string in its own face, from canvas metrics, against the line box the CSS gives it. */
async function inkVersusLine(page: Page, testid: string) {
  return page.evaluate((id) => {
    const el = document.querySelector<HTMLElement>(`[data-testid="${id}"]`)!;
    const style = getComputedStyle(el);
    const size = parseFloat(style.fontSize);
    const lineHeight = style.lineHeight === "normal" ? size * 1.2 : parseFloat(style.lineHeight);
    const ctx = document.createElement("canvas").getContext("2d")!;
    ctx.font = `${style.fontWeight} ${size}px ${style.fontFamily}`;
    const text = (el.textContent ?? "").trim();
    const ink = ctx.measureText(text);
    // Lines of text in the element, by the rectangles of each word.
    const range = document.createRange();
    range.selectNodeContents(el);
    const tops = Array.from(new Set(Array.from(range.getClientRects()).map((r) => Math.round(r.top / 4)))).length;
    return {
      size,
      lineHeight,
      inkHeight: ink.actualBoundingBoxAscent + ink.actualBoundingBoxDescent,
      overflowsBox: el.scrollHeight > el.clientHeight + 1,
      lines: tops,
      transform: style.textTransform,
      letterSpacing: style.letterSpacing,
      wordSpacing: style.wordSpacing,
      fontFamily: style.fontFamily,
      weight: Number(style.fontWeight),
      fontStyle: style.fontStyle,
      synthesis: style.fontSynthesis,
    };
  }, testid);
}

for (const theme of THEMES) {
  for (const width of [360, 390, 1280]) {
    test.describe(`Hindi type, ${theme} at ${width}`, () => {
      test.use({ viewport: { width, height: 800 } });

      test("headline, mixed line, label and body follow the Devanagari rules", async ({ page, context }) => {
        await prefs(page, theme, "hi");
        await page.goto("/dev/type");
        await expect(page.getByTestId("type-specimen")).toBeVisible({ timeout: 30_000 });
        // The Devanagari sheet loads after first paint, only because the language is Hindi.
        await expect.poll(() => page.evaluate(() => !!document.getElementById("yt-devanagari-fonts")), { timeout: 15_000 }).toBe(true);
        // Faces load on first use: wait until both weights (500 display, 400 body) are in, for Devanagari and Latin.
        await page.waitForFunction(
          () => {
            const loaded = Array.from(document.fonts).filter((f) => f.status === "loaded" && f.family.includes("Noto Sans Devanagari"));
            return ["400", "500"].every((w) => loaded.filter((f) => f.weight === w).length >= 2);
          },
          undefined,
          { timeout: 20_000 },
        );
        await fontsReady(page);

        for (const id of ["specimen-headline", "specimen-mixed", "specimen-label", "specimen-glow"]) {
          const m = await inkVersusLine(page, id);
          const where = `${id} ${JSON.stringify(m)}`;
          expect(m.fontFamily, where).toContain("Noto Sans Devanagari");
          expect(m.fontFamily.toLowerCase(), where).not.toContain("geist");
          expect(m.transform, where).toBe("none");
          expect(["normal", "0px"], where).toContain(m.letterSpacing);
          expect(m.wordSpacing === "normal" || m.wordSpacing === "0px", where).toBe(true);
          expect(m.weight, where).toBeLessThanOrEqual(500);
          expect(m.fontStyle, where).toBe("normal");
          expect(m.synthesis, where).toContain("none");
          // No clipped matras: the line box holds the ink, and the element does not scroll its own content.
          expect(m.lineHeight, where).toBeGreaterThanOrEqual(m.inkHeight);
          expect(m.overflowsBox, where).toBe(false);
        }
        for (const id of ["specimen-headline", "specimen-mixed"]) {
          const m = await inkVersusLine(page, id);
          expect(m.lineHeight / m.size, id).toBeGreaterThanOrEqual(1.3);
        }
        const body = await inkVersusLine(page, "specimen-body");
        expect(body.lineHeight / body.size, "body").toBeGreaterThanOrEqual(1.6);
        expect(body.lineHeight, "body").toBeGreaterThanOrEqual(body.inkHeight);

        // Latin words inside a Hindi line use the same family as the Devanagari glyphs around them.
        const client = await context.newCDPSession(page);
        await client.send("DOM.enable");
        await client.send("CSS.enable");
        const { root } = await client.send("DOM.getDocument", { depth: 0 });
        for (const id of ["specimen-mixed", "specimen-body"]) {
          const { nodeId } = await client.send("DOM.querySelector", { nodeId: root.nodeId, selector: `[data-testid="${id}"]` });
          const { fonts } = await client.send("CSS.getPlatformFontsForNode", { nodeId });
          // Chrome names the faces "Noto Sans Devanagari" and "Noto Sans Devanagari Medium": one family, two weights.
          expect(fonts.length, `${id} used fonts`).toBeGreaterThan(0);
          for (const f of fonts) expect(f.familyName, `${id} uses one family`).toMatch(/^Noto Sans Devanagari( Medium)?$/);
        }

        await page.screenshot({ path: `${SHOTS}/id-hindi-type-${theme}-${width}.png` });
      });
    });
  }
}

/** The headline of the hero in Hindi must not collide with the line below it, at every width. */
for (const width of [360, 390, 1280]) {
  test(`hero in Hindi: headline and the line under it do not overlap at ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 });
    await prefs(page, "light", "hi");
    await page.goto("/brownie-chat");
    await expect(page.getByTestId("greeting")).not.toHaveText("", { timeout: 20_000 });
    await fontsReady(page);
    const boxes = await page.evaluate(() => {
      const h = document.querySelector('[data-testid="greeting"]')!.getBoundingClientRect();
      const frame = document.querySelector('[data-testid="hero-frame"]')!;
      const p = frame.querySelector("p")!.getBoundingClientRect();
      return { headBottom: h.bottom, nextTop: p.top };
    });
    expect(boxes.headBottom).toBeLessThanOrEqual(boxes.nextTop + 1);
  });
}

test.describe("language switch", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("keeps the student on the same screen, changes the words, and is remembered on the device", async ({ page }) => {
    await prefs(page, "light", null);
    await devLogin(page, "mid_chapter");
    const url = page.url();
    const englishHeading = await page.getByTestId("greeting").innerText();
    await expect(page.getByTestId("language-en")).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByTestId("language-hi")).toContainText("हिन्दी");

    await page.getByTestId("language-hi").click();
    expect(page.url()).toBe(url);
    await expect(page.getByTestId("hero")).toBeVisible();
    await expect(page.locator("html")).toHaveAttribute("lang", "hi");
    await expect(page.getByTestId("composer-send")).toHaveAccessibleName("भेजें");
    expect(await page.getByTestId("greeting").innerText()).not.toBe(englishHeading);
    await expect(page.getByTestId("language-hi")).toHaveAttribute("aria-pressed", "true");

    // Remembered: a reload keeps Hindi, and the first paint already has lang=hi.
    await page.reload();
    await expect(page.getByTestId("hero")).toBeVisible();
    await expect(page.locator("html")).toHaveAttribute("lang", "hi");
    await expect(page.getByTestId("composer-send")).toHaveAccessibleName("भेजें");
    expect(await page.evaluate(() => localStorage.getItem("yt_locale"))).toBe("hi");

    // Back to English from the same place.
    await page.getByTestId("language-en").click();
    await expect(page.locator("html")).toHaveAttribute("lang", "en");
    await expect(page.getByTestId("composer-send")).toHaveAccessibleName("Send");
  });

  test("the setup question stays open when the language changes", async ({ page }) => {
    await prefs(page, "light", null);
    await page.goto("/brownie-chat");
    await expect(page.getByTestId("card-try-lesson")).toBeVisible({ timeout: 30_000 });
    await page.getByTestId("card-try-lesson").click();
    await expect(page.getByTestId("setup-grade")).toBeVisible({ timeout: 20_000 });
    await page.getByTestId("language-hi").click();
    await expect(page.getByTestId("setup-grade")).toBeVisible();
    await expect(page.getByTestId("setup-grade")).toHaveAttribute("aria-label", "आप किस कक्षा में हैं?");
  });

  test("only English and Hindi can be chosen; the others are listed as coming soon in Settings", async ({ page }) => {
    await prefs(page, "light", "en");
    await page.goto("/brownie-chat");
    await expect(page.getByTestId("hero")).toBeVisible();
    await expect(page.getByTestId("language-switch").getByRole("button")).toHaveCount(2);
    await page.getByRole("button", { name: /^menu|open menu/i }).first().click();
    await page.getByRole("button", { name: /settings/i }).first().click();
    await expect(page.getByTestId("comfort-dialog")).toBeVisible();
    await expect(page.getByTestId("language-soon")).toContainText(/Nepali|Assamese/);
    await expect(page.getByTestId("comfort-dialog").getByTestId("language-switch").getByRole("button")).toHaveCount(2);
  });

  test("the class dropdown lists classes 5 to 12 (classes without content are disabled) and starts setup at the next question", async ({ page }) => {
    await prefs(page, "light", "en");
    await page.goto("/brownie-chat");
    const select = page.getByTestId("class-select");
    await expect(select).toBeVisible({ timeout: 30_000 });
    const options = await select.locator("option").evaluateAll((els) => els.map((o) => ({ value: (o as HTMLOptionElement).value, disabled: (o as HTMLOptionElement).disabled })));
    const classes = options.filter((o) => o.value).map((o) => Number(o.value));
    expect(Math.min(...classes)).toBe(5);
    expect(Math.max(...classes)).toBe(12);
    expect(options.filter((o) => o.value && !o.disabled).length).toBeGreaterThan(0);
    await select.selectOption({ index: options.findIndex((o) => o.value && !o.disabled) });
    await expect(page.locator('[data-testid^="choice-board-"], [data-testid^="choice-subject-"]').first()).toBeVisible({ timeout: 20_000 });
  });

  test("Try one question opens the work in a full-window sheet over the sidebar, and Back to chat returns", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await prefs(page, "light", "en");
    await page.goto("/brownie-chat");
    await page.getByTestId("card-try-question").click({ timeout: 30_000 });
    const panel = page.getByTestId("workspace-panel");
    await expect(panel).toBeVisible({ timeout: 40_000 });
    const box = (await panel.boundingBox())!;
    expect(box.width).toBeGreaterThanOrEqual(1279);
    expect(box.height).toBeGreaterThanOrEqual(799);
    await expect(page.getByTestId("workspace-frame")).toBeVisible();
    await page.screenshot({ path: `${SHOTS}/id-workspace-full-window-1280.png` });
    await page.getByTestId("back-to-chat").click();
    await expect(panel).toBeHidden();
    await expect(page.getByTestId("hero")).toBeVisible();
  });

  test("the sidebar button is a small icon with an accessible name", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await prefs(page, "light", "en");
    await page.goto("/brownie-chat");
    const toggle = page.getByTestId("sidebar-toggle");
    await expect(toggle).toBeVisible();
    await expect(toggle).toHaveAccessibleName(/menu|sidebar/i);
    expect((await toggle.boundingBox())!.width).toBeLessThanOrEqual(48);
  });

  test("a stored language that is not live falls back to English", async ({ page }) => {
    await page.addInitScript(() => window.localStorage.setItem("yt_locale", "ne"));
    await page.goto("/brownie-chat");
    await expect(page.getByTestId("hero")).toBeVisible();
    await expect(page.getByTestId("composer-send")).toHaveAccessibleName("Send");
  });
});

/** Screenshots of the four screens in both languages and themes. */
type Screen = { name: string; open: (page: Page) => Promise<void> };
const SCREENS: Screen[] = [
  {
    name: "home",
    open: async (page) => {
      await page.goto("/brownie-chat");
      await expect(page.getByTestId("greeting")).not.toHaveText("", { timeout: 20_000 });
      await expect(page.getByTestId("card-try-lesson")).toBeVisible({ timeout: 30_000 });
    },
  },
  {
    name: "home-student",
    open: async (page) => {
      await devLogin(page, "mid_chapter");
      await expect(page.getByTestId("today-strip")).toBeVisible({ timeout: 30_000 });
    },
  },
  {
    name: "setup",
    open: async (page) => {
      await page.goto("/brownie-chat");
      await expect(page.getByTestId("card-try-lesson")).toBeVisible({ timeout: 30_000 });
      await page.getByTestId("card-try-lesson").click();
      await expect(page.getByTestId("setup-grade")).toBeVisible({ timeout: 20_000 });
    },
  },
  {
    name: "lesson",
    open: async (page) => {
      await page.goto("/dev/lessons/LESSON.TWO_STEP");
      await expect(page.getByRole("heading", { level: 2 })).toBeVisible({ timeout: 30_000 });
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
];

for (const lang of LANGS) {
  for (const theme of THEMES) {
    for (const { w, h } of [
      { w: 390, h: 844 },
      { w: 1280, h: 800 },
    ]) {
      test.describe(`screens in ${lang}, ${theme}, ${w}x${h}`, () => {
        test.use({ viewport: { width: w, height: h } });
        for (const screen of SCREENS) {
          test(`${screen.name}: no sideways scroll, text inside its box, screenshot`, async ({ page }) => {
            await prefs(page, theme, lang);
            await screen.open(page);
            await fontsReady(page);
            expect(await page.evaluate(() => document.documentElement.lang)).toBe(lang);
            const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
            expect(overflow, "horizontal scroll").toBeLessThanOrEqual(1);
            await page.screenshot({ path: `${SHOTS}/id-${screen.name}-${lang}-${theme}-${w}.png` });
          });
        }
      });
    }
  }
}

/** The full device range for the home, English, both themes (UI-5 item 8). */
for (const theme of THEMES) {
  for (const [w, h] of [
    [360, 800],
    [390, 844],
    [768, 1024],
    [1280, 800],
    [1536, 900],
  ] as const) {
    test(`home at ${w}x${h}, ${theme}: screenshot and no sideways scroll`, async ({ page }) => {
      await page.setViewportSize({ width: w, height: h });
      await prefs(page, theme, "en");
      await page.goto("/brownie-chat");
      await expect(page.getByTestId("card-try-lesson")).toBeVisible({ timeout: 30_000 });
      await fontsReady(page);
      expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
      await page.screenshot({ path: `${SHOTS}/id-home-range-${theme}-${w}.png` });
    });
  }
}

test.describe("glass limits and Reduce effects", () => {
  test.use({ viewport: { width: 1280, height: 900 } });

  const blurred = (page: Page) =>
    page.evaluate(() => {
      const seen: string[] = [];
      for (const el of Array.from(document.body.querySelectorAll<HTMLElement>("*"))) {
        const style = getComputedStyle(el);
        const filter = style.backdropFilter || style.getPropertyValue("-webkit-backdrop-filter");
        if (!filter || filter === "none") continue;
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0 || r.bottom < 0 || r.top > window.innerHeight) continue;
        seen.push(`${el.tagName.toLowerCase()}[${el.getAttribute("data-testid") ?? el.className.toString().slice(0, 20)}]`);
      }
      return seen;
    });

  test("light theme: at most four blurred surfaces are visible, on the guest home and the student home", async ({ page }) => {
    await prefs(page, "light", "en");
    await SCREENS[0]!.open(page);
    const guest = await blurred(page);
    expect(guest.length, guest.join(", ")).toBeLessThanOrEqual(4);
    await SCREENS[1]!.open(page);
    const student = await blurred(page);
    expect(student.length, student.join(", ")).toBeLessThanOrEqual(4);
  });

  test("dark theme uses solid surfaces: no backdrop blur anywhere", async ({ page }) => {
    await prefs(page, "dark", "en");
    await SCREENS[0]!.open(page);
    expect(await blurred(page)).toEqual([]);
  });

  test("Reduce effects: solid surfaces, no glow shapes, no animation, chosen in Settings and remembered", async ({ page }) => {
    await prefs(page, "light", "en", { effects: "reduce" });
    await SCREENS[0]!.open(page);
    await expect(page.locator("html")).toHaveAttribute("data-effects", "reduce");
    expect(await blurred(page)).toEqual([]);
    const shapes = await page.evaluate(() => getComputedStyle(document.body, "::before").backgroundImage);
    expect(shapes, "no gradient or glow shapes").toBe("none");
    const duration = await page.evaluate(() => getComputedStyle(document.querySelector('[data-testid="card-try-lesson"]')!).transitionDuration);
    expect(parseFloat(duration)).toBeLessThan(0.01);
    await page.screenshot({ path: `${SHOTS}/id-home-reduce-effects-light-1280.png` });
  });

  test("Reduce effects turns on by itself for a data-saver device", async ({ page }) => {
    await page.addInitScript(() => Object.defineProperty(navigator, "connection", { value: { saveData: true }, configurable: true }));
    await page.goto("/brownie-chat");
    await expect(page.locator("html")).toHaveAttribute("data-effects", "reduce");
  });

  test("the glass has a solid fallback under prefers-contrast: more", async ({ page }) => {
    await page.emulateMedia({ contrast: "more" });
    await prefs(page, "light", "en");
    await SCREENS[0]!.open(page);
    expect(await blurred(page)).toEqual([]);
  });
});

test("fonts: English never fetches Devanagari; Hindi never fetches the Latin faces it does not use", async ({ page }) => {
  const fetched: string[] = [];
  page.on("request", (req) => {
    if (/\/fonts\//.test(req.url())) fetched.push(req.url().split("/fonts/")[1]!);
  });
  await prefs(page, "light", "en");
  await page.goto("/brownie-chat");
  await expect(page.getByTestId("greeting")).not.toHaveText("", { timeout: 20_000 });
  await fontsReady(page);
  await page.waitForTimeout(1500);
  expect(fetched.filter((f) => f.includes("devanagari")), "English fetched Devanagari").toEqual([]);
  expect(fetched.some((f) => f.startsWith("inter-latin-400"))).toBe(true);
  expect(fetched.some((f) => f.startsWith("geist-mono-latin-300"))).toBe(true);

  fetched.length = 0;
  const hindi = await page.context().newPage();
  hindi.on("request", (req) => {
    if (/\/fonts\//.test(req.url())) fetched.push(req.url().split("/fonts/")[1]!);
  });
  await hindi.addInitScript(() => window.localStorage.setItem("yt_locale", "hi"));
  await hindi.goto("/brownie-chat");
  await expect(hindi.getByTestId("greeting")).not.toHaveText("", { timeout: 20_000 });
  await hindi.waitForTimeout(2500);
  expect(fetched.some((f) => f.startsWith("noto-sans-devanagari-deva-400"))).toBe(true);
  expect(fetched.filter((f) => f.startsWith("geist-mono") || f.startsWith("inter")), "Hindi fetched Latin faces").toEqual([]);
});
