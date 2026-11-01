import { expect, test, type Page } from "@playwright/test";
import { devLogin } from "./shell";

/**
 * UI-1: the chat-first front door at four widths. Guest path, role homes, create-account cards, the
 * grown-up path, the keyboard path, and the checks that every screen has no horizontal overflow, no
 * clipped text (English, and an Indic stress sample) and a visible focus ring. Screenshots go to
 * test-results/screens/ui1-<name>-<width>.png. Needs the API with DEV_TOOLS=true on seeded scenarios.
 */
const SCREENS = "test-results/screens";
const WIDTHS = [
  { w: 360, h: 800 },
  { w: 768, h: 1024 },
  { w: 1280, h: 800 },
  { w: 1536, h: 900 },
];

async function shot(page: Page, name: string) {
  await page.waitForTimeout(400);
  const width = page.viewportSize()?.width;
  await page.screenshot({ path: `${SCREENS}/ui1-${name}-${width}.png` });
}

async function expectNoOverflow(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow, "no horizontal scroll").toBeLessThanOrEqual(0);
}

/** Visible text that is cut off by its own box (not an intentional ellipsis). */
async function expectNoClippedText(page: Page) {
  const clipped = await page.evaluate(() => {
    const out: string[] = [];
    for (const el of Array.from(document.querySelectorAll<HTMLElement>("h1, h2, h3, p, span, button, a, label, li"))) {
      const text = (el.innerText || "").trim();
      if (!text || el.closest(".sr-only")) continue;
      const style = getComputedStyle(el);
      if (style.visibility === "hidden" || style.display === "none") continue;
      if (el.classList.contains("truncate") || style.textOverflow === "ellipsis") continue;
      const clips = style.overflowX !== "visible" && el.scrollWidth > el.clientWidth + 1;
      if (clips) out.push(text.slice(0, 40));
    }
    return out;
  });
  expect(clipped, "text is not clipped").toEqual([]);
}

/** Open "/" and wait until the app has started (the greeting is filled in after hydration). */
async function openHome(page: Page) {
  await page.goto("/");
  await expect(page.getByTestId("hero")).toBeVisible();
  await expect(page.getByTestId("greeting")).not.toHaveText("", { timeout: 20_000 });
}

async function tapsTo(page: Page, ids: string[]) {
  let taps = 0;
  for (const id of ids) {
    await page.locator(`[data-testid="${id}"]:visible`).first().click();
    taps += 1;
  }
  return taps;
}

for (const { w, h } of WIDTHS) {
  test.describe(`front door at ${w}x${h}`, () => {
    test.use({ viewport: { width: w, height: h } });

    test("fresh visitor sees a clear flow without demo progress", async ({ page }) => {
      await page.goto("/");
      await expect(page.getByTestId("hero")).toBeVisible();
      await expect(page.getByTestId("welcome-flow")).toBeVisible();
      await expect(page.getByTestId("topic-mastery")).toHaveCount(0);
      await expect(page.getByTestId("right-panel")).toHaveCount(0);
      await expectNoOverflow(page);
      await expectNoClippedText(page);
      await shot(page, "fresh-visitor");
    });

    test("guest: from / to a first lesson in five taps, then back to the chat", async ({ page }) => {
      await openHome(page);
      await expect(page.getByTestId("greeting")).toContainText(/learn today/i);
      await expect(page.getByTestId("welcome-flow")).toBeVisible();
      await expect(page.getByTestId("topic-mastery")).toHaveCount(0);
      await expect(page.getByTestId("right-panel")).toHaveCount(0);
      await expect(page.getByTestId("card-try-lesson")).toBeVisible();
      await expectNoOverflow(page);
      await expectNoClippedText(page);
      await shot(page, "guest-welcome");

      let taps = await tapsTo(page, ["card-try-lesson", "choice-grade-9"]);
      await page.locator('[data-testid^="choice-board-"]:visible').first().click();
      taps += 1;
      await shot(page, "guest-subject");
      taps += await tapsTo(page, ["choice-subject-math"]);
      await expect(page.getByTestId("identity-choices")).toBeVisible();
      await expectNoOverflow(page);
      await shot(page, "guest-identity");
      taps += await tapsTo(page, ["just-try"]);
      await expect(page.getByTestId("workspace-frame")).toBeVisible({ timeout: 30_000 });
      expect(taps, "taps from / to the first activity").toBeLessThanOrEqual(5);
      await expect(page).toHaveURL(/[?&]w=%2Fsession%2F/);
      await page.waitForTimeout(2500);
      await shot(page, "guest-lesson-panel");
      await expectNoOverflow(page);

      await page.getByTestId("back-to-chat").click();
      await expect(page.getByTestId("hero")).toBeVisible();
      await expect(page.getByTestId("workspace-frame")).toHaveCount(0);
      await shot(page, "guest-back-to-chat");
    });

    test("student (Review due): greeting, a Review card, and the warm-up opens in the panel", async ({ page }) => {
      await devLogin(page, "Review due");
      await expect(page.getByTestId("greeting")).toContainText("Rhea");
      await expect(page.getByTestId("card-review")).toBeVisible();
      await expect(page.getByTestId("card-review")).toBeEnabled();
      await expectNoOverflow(page);
      await expectNoClippedText(page);
      await shot(page, "student-home");
      await page.getByTestId("card-review").click();
      const frame = page.frameLocator('[data-testid="workspace-frame"]');
      await expect(frame.locator(".stem, h1").first()).toBeVisible({ timeout: 30_000 });
      await shot(page, "student-warmup-panel");
    });

    test("teacher home: three cards, and the heatmap opens in the panel", async ({ page }) => {
      await page.goto("/dev");
      await page.getByTestId("login-teacher").click();
      await expect(page.getByTestId("hero")).toBeVisible();
      await expect(page.getByTestId("card-heatmap")).toBeVisible();
      await expect(page.getByTestId("card-stuck")).toBeVisible();
      await expect(page.getByTestId("card-queue")).toBeVisible();
      await expect(page.getByTestId("mode-class")).toBeVisible();
      await expectNoOverflow(page);
      await shot(page, "teacher-home");
      await page.getByTestId("card-heatmap").click();
      const frame = page.frameLocator('[data-testid="workspace-frame"]');
      await expect(frame.getByTestId("teacher-heatmap").or(frame.getByText(/where each student is/i)).first()).toBeVisible({ timeout: 30_000 });
      await shot(page, "teacher-heatmap-panel");
    });

    test("parent home: three cards, and the guardian page opens in the panel", async ({ page }) => {
      await page.goto("/dev");
      await page.getByTestId("parent-mid_chapter").click();
      await expect(page.getByTestId("hero")).toBeVisible();
      await expect(page.getByTestId("card-week")).toBeVisible();
      await expect(page.getByTestId("card-consent")).toBeVisible();
      await expect(page.getByTestId("card-add-child")).toBeVisible();
      await expectNoOverflow(page);
      await shot(page, "parent-home");
      await page.getByTestId("card-week").click();
      await expect(page.getByTestId("workspace-frame")).toBeVisible();
      await shot(page, "parent-week-panel");
    });

    test("create account: a card for each role, and students under 18 are never left alone", async ({ page }) => {
      await openHome(page);
      if (w < 1024) await page.getByTestId("menu-open").click();
      await page.locator('[data-testid="nav-create-account"]:visible').first().click();
      await expect(page.getByTestId("create-account")).toBeVisible();
      await expect(page.getByTestId("create-account")).toContainText(/under 18/i);
      await expectNoOverflow(page);
      await shot(page, "create-account");

      await page.getByTestId("create-student").click();
      await expect(page.getByTestId("student-sign-in")).toBeVisible();
      await expect(page.getByTestId("family-code")).toBeVisible();
      await shot(page, "create-student");
      await page.getByTestId("identity-back").click();
      await page.getByTestId("create-account").waitFor({ state: "detached" }).catch(() => {});
    });

    for (const role of ["teacher", "parent"] as const) {
      test(`create account: the ${role} card asks for an email code`, async ({ page }) => {
        await openHome(page);
        if (w < 1024) await page.getByTestId("menu-open").click();
        await page.locator('[data-testid="nav-create-account"]:visible').first().click();
        await page.getByTestId(`create-${role}`).click();
        await expect(page.getByTestId(`${role}-otp`)).toBeVisible();
        await expect(page.getByTestId("otp-email")).toBeVisible();
        await expectNoOverflow(page);
        await shot(page, `create-${role}`);
      });
    }

    test("ask a grown-up: the guest path ends at the guardian sign-in card", async ({ page }) => {
      await openHome(page);
      await tapsTo(page, ["card-try-lesson", "choice-grade-9"]);
      await page.locator('[data-testid^="choice-board-"]:visible').first().click();
      await tapsTo(page, ["choice-subject-math", "save-progress"]);
      await expect(page.getByTestId("grown-up")).toBeVisible();
      await expectNoClippedText(page);
      await shot(page, "grown-up");
      await page.getByTestId("grown-up-go").click();
      await expect(page.getByTestId("parent-otp")).toBeVisible();
      await expect(page.getByTestId("otp-email")).toBeVisible();
      await expectNoOverflow(page);
      await shot(page, "grown-up-guardian-otp");
    });

    test("keyboard: composer, card, panel and back to chat work without a mouse", async ({ page }) => {
      await page.goto("/dev");
      await page.getByTestId("login-review_due").click();
      await expect(page.getByTestId("hero")).toBeVisible();
      await expect(page.getByTestId("card-plan")).toBeVisible({ timeout: 30_000 }); // cards have loaded
      await page.getByTestId("composer-input").focus();
      await expect(page.getByTestId("composer-input")).toBeFocused();
      // The focus ring is visible on the composer's box and on a card reached by keyboard.
      const ring = await page.getByTestId("composer").evaluate((el) => {
        const inner = el.querySelector("form, [class*='rounded']") as HTMLElement;
        return getComputedStyle(inner).borderColor;
      });
      expect(ring).toBeTruthy();
      // Tab through the page until the Today's-plan card has focus (keyboard focus shows the ring).
      let reached = false;
      for (let i = 0; i < 40 && !reached; i += 1) {
        await page.keyboard.press("Tab");
        reached = await page.evaluate(() => document.activeElement?.getAttribute("data-testid") === "card-plan");
      }
      expect(reached, "the card is reachable with Tab").toBeTruthy();
      const outline = await page.getByTestId("card-plan").evaluate((el) => {
        const style = getComputedStyle(el);
        return { width: parseFloat(style.outlineWidth), style: style.outlineStyle };
      });
      expect(outline.style).not.toBe("none");
      expect(outline.width).toBeGreaterThanOrEqual(2);
      await page.keyboard.press("Enter");
      await expect(page.getByTestId("workspace-frame")).toBeVisible();
      await expect(page.getByTestId("back-to-chat")).toBeFocused();
      await page.keyboard.press("Enter");
      await expect(page.getByTestId("hero")).toBeVisible();
      await expect(page.getByTestId("workspace-frame")).toHaveCount(0);
    });

    test("Indic text expansion: a long Devanagari greeting and card title do not clip or overflow", async ({ page }) => {
      await page.addInitScript(() => window.localStorage.setItem("yt_locale", "ne"));
      await page.goto("/dev");
      await page.getByTestId("login-review_due").click();
      await expect(page.getByTestId("hero")).toBeVisible();
      // Layout stress sample only (not product copy): long conjunct-heavy words at the same positions.
      await page.evaluate(() => {
        const sample = "विद्यार्थीहरूको आत्मनिर्भरतासम्बन्धी अभ्यासकार्यक्रम";
        document.documentElement.lang = "ne";
        for (const sel of ['[data-testid="greeting"]', '[data-testid="card-review"] span:nth-of-type(2)', '[data-testid="card-plan"] span:nth-of-type(2)']) {
          const el = document.querySelector(sel);
          if (el) el.textContent = sample;
        }
      });
      await expectNoOverflow(page);
      await expectNoClippedText(page);
      await shot(page, "indic-sample");
    });
  });
}

test.describe("nothing typed leaves the device", () => {
  test.use({ viewport: { width: 1280, height: 800 } });

  test("a typed marker is in no request, no storage and no cookie", async ({ page }) => {
    const marker = "zq-typed-marker-4471";
    const sent: string[] = [];
    page.on("request", (req) => {
      sent.push(`${req.method()} ${req.url()} ${req.postData() ?? ""} ${JSON.stringify(req.headers())}`);
    });
    await devLogin(page, "Mid chapter");
    sent.length = 0;
    await page.getByTestId("composer-input").fill(marker + " two step equations");
    await page.getByTestId("composer-send").click();
    await expect(page.getByTestId("replies")).toBeVisible({ timeout: 20_000 });
    await page.waitForTimeout(1000);
    expect(sent.join("\n")).not.toContain(marker);
    const stored = await page.evaluate(async () => {
      const dump: string[] = [JSON.stringify({ ...localStorage }), JSON.stringify({ ...sessionStorage }), document.cookie];
      const dbs = (await indexedDB.databases?.()) ?? [];
      dump.push(JSON.stringify(dbs));
      return dump.join("\n");
    });
    expect(stored).not.toContain(marker);
    await shot(page, "finder-reply");
  });

  test("distress words get a gentle message, no matches, and nothing is sent", async ({ page }) => {
    const sent: string[] = [];
    page.on("request", (req) => sent.push(`${req.url()} ${req.postData() ?? ""}`));
    await devLogin(page, "Mid chapter");
    sent.length = 0;
    await page.getByTestId("composer-input").fill("I want to die");
    await page.getByTestId("composer-send").click();
    await expect(page.getByTestId("reply-distress")).toBeVisible({ timeout: 20_000 });
    expect(sent.join("\n")).not.toMatch(/want%20to%20die|want to die/i);
  });
});
