import { expect, test, type Page } from "@playwright/test";
import { rgbToHex } from "../lib/contrast";
import { devLogin, enter } from "./shell";

/**
 * UI-4: plain paper. Lessons, practice and widget areas use plain surfaces (white in light, the dark background in
 * dark), never a graph-paper texture. The grid is an opt-in Comfort setting for the graph widget only.
 * Screenshots go to test-results/screens/paper-<screen>-<theme>-<width>.png.
 */
const SHOTS = "test-results/screens";
const THEMES = ["light", "dark"] as const;
const SIZES = [
  { w: 360, h: 800 },
  { w: 1280, h: 800 },
];

async function useTheme(page: Page, theme: (typeof THEMES)[number], extra: Record<string, string> = {}) {
  await page.addInitScript(([value]) => window.localStorage.setItem("yt.comfort", value), [JSON.stringify({ theme, ...extra })]);
}

/** The computed background-image of every surface a student reads on. All must be "none". */
async function backgroundImages(page: Page): Promise<Record<string, string>> {
  return page.evaluate(() => {
    const out: Record<string, string> = {};
    for (const sel of ["html", "body", ".phone", ".lp", ".lp-panel", ".lp-board", ".lp-ask", ".lp-bar"]) {
      for (const [i, el] of Array.from(document.querySelectorAll(sel)).entries()) out[`${sel}#${i}`] = getComputedStyle(el).backgroundImage;
    }
    return out;
  });
}

for (const theme of THEMES) {
  for (const { w, h } of SIZES) {
    test.describe(`plain paper, ${theme} at ${w}x${h}`, () => {
      test.use({ viewport: { width: w, height: h } });

      test("lesson: plain surface, no background image anywhere", async ({ page }) => {
        await useTheme(page, theme);
        await page.goto("/dev/lessons/LESSON.TWO_STEP");
        await expect(page.getByRole("heading", { level: 2 })).toBeVisible({ timeout: 30_000 });
        const images = await backgroundImages(page);
        expect(Object.keys(images).some((k) => k.startsWith(".lp#"))).toBe(true);
        for (const [where, image] of Object.entries(images)) expect(image, where).toBe("none");
        const surface = rgbToHex(await page.locator(".lp").first().evaluate((el) => getComputedStyle(el).backgroundColor));
        expect(surface).toBe(theme === "light" ? "#ffffff" : "#0b041a");
        await page.waitForTimeout(400);
        await page.screenshot({ path: `${SHOTS}/paper-lesson-${theme}-${w}.png` });
      });

      test("practice: plain surface, no background image", async ({ page }) => {
        await useTheme(page, theme);
        await devLogin(page, "mid_chapter");
        await enter(page, "nav-revision");
        await expect(page.locator(".stem, h1, h2").first()).toBeVisible({ timeout: 30_000 });
        for (const [where, image] of Object.entries(await backgroundImages(page))) expect(image, where).toBe("none");
        const surface = rgbToHex(await page.locator(".phone").first().evaluate((el) => getComputedStyle(el).backgroundColor));
        expect(surface).toBe(theme === "light" ? "#ffffff" : "#0b041a");
        await page.waitForTimeout(400);
        await page.screenshot({ path: `${SHOTS}/paper-practice-${theme}-${w}.png` });
      });
    });
  }
}

test.describe("board paper setting", () => {
  test.use({ viewport: { width: 360, height: 800 } });

  // A grid line as the graph widget draws it, placed inside the real lesson surface, so the real CSS decides.
  async function gridLineVisibility(page: Page) {
    return page.evaluate(() => {
      const ns = "http://www.w3.org/2000/svg";
      const svg = document.createElementNS(ns, "svg");
      const line = document.createElementNS(ns, "line");
      line.setAttribute("class", "lp-g");
      svg.appendChild(line);
      document.querySelector(".lp")!.appendChild(svg);
      return getComputedStyle(line).visibility;
    });
  }

  test("plain by default: the widget grid is hidden", async ({ page }) => {
    await page.goto("/dev/lessons/LESSON.TWO_STEP");
    await expect(page.getByRole("heading", { level: 2 })).toBeVisible({ timeout: 30_000 });
    expect(await page.evaluate(() => document.documentElement.hasAttribute("data-paper"))).toBe(false);
    expect(await gridLineVisibility(page)).toBe("hidden");
  });

  test("Light grid is opt-in from Settings, persists, and never puts an image behind the lesson", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto("/");
    await page.locator('[data-testid="nav-settings"]:visible').first().click();
    await expect(page.getByTestId("comfort-dialog")).toBeVisible();
    await expect(page.getByTestId("paper-plain")).toHaveAttribute("aria-pressed", "true");
    await page.getByTestId("paper-grid").click();
    await expect(page.locator("html")).toHaveAttribute("data-paper", "grid");
    await page.goto("/dev/lessons/LESSON.TWO_STEP");
    await expect(page.getByRole("heading", { level: 2 })).toBeVisible({ timeout: 30_000 });
    expect(await gridLineVisibility(page)).toBe("visible");
    for (const [where, image] of Object.entries(await backgroundImages(page))) expect(image, where).toBe("none");
  });
});
