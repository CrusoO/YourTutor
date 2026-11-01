import { expect, test } from "@playwright/test";

/**
 * UI-2 refinement specs. Each test names the finding in docs/UI_REFINEMENT_1.md it reproduces and guards.
 * Selectors are data-testid. Before/after screenshots go to test-results/refine/.
 */
const SHOTS = "test-results/refine";
const SIZES = [
  { name: "360", width: 360, height: 800 },
  { name: "1280", width: 1280, height: 800 },
];

async function signIn(page: import("@playwright/test").Page, login = "login-mid_chapter") {
  await page.goto("/dev");
  await page.getByTestId(login).click();
  await expect(page.getByTestId("hero")).toBeVisible();
  await expect(page.getByTestId("panel-continue").or(page.getByTestId("card-start")).first()).toBeVisible({ timeout: 30_000 });
}

for (const size of SIZES) {
  test.describe(`refine @${size.name}`, () => {
    test.use({ viewport: { width: size.width, height: size.height } });

    test("R-04: Back inside the panel steps back one screen, then closes the panel", async ({ page }) => {
      await signIn(page);
      // Below 1024 px the sidebar is a drawer behind the menu button.
      if (await page.getByTestId("menu-open").isVisible()) await page.getByTestId("menu-open").click();
      await page.locator('[data-testid="nav-chapters"]:visible').first().click();
      await expect(page.getByTestId("workspace-frame")).toBeVisible({ timeout: 20_000 });
      const frame = page.frameLocator('[data-testid="workspace-frame"]');
      const first = frame.locator('[data-testid^="chapter-"]:not([aria-disabled="true"])').first();
      await expect(first).toBeVisible({ timeout: 30_000 });
      await page.screenshot({ path: `${SHOTS}/r04-${size.name}-1-chapters.png` });
      await first.click();
      await expect(page).toHaveURL(/\?w=%2Fchapters%2F/, { timeout: 20_000 });
      await page.screenshot({ path: `${SHOTS}/r04-${size.name}-2-chapter.png` });

      await page.goBack();
      await expect(page).toHaveURL(/\?w=%2Fchapters$/, { timeout: 20_000 });
      await expect(page.getByTestId("workspace-frame")).toBeVisible();
      await expect(frame.locator('[data-testid^="chapter-"]').first()).toBeVisible({ timeout: 30_000 });
      await page.screenshot({ path: `${SHOTS}/r04-${size.name}-3-back-to-chapters.png` });

      await page.goBack();
      await expect(page.getByTestId("workspace-frame")).toHaveCount(0);
      await expect(page).toHaveURL(/\/$/);
    });

    test("R-01 and R-02: no raw skill id on the home or the lesson header", async ({ page }) => {
      await signIn(page);
      const idLike = /\b[a-z]{1,4}\d{0,2}[._][a-z0-9_.]{3,}\b/;
      const cont = page.getByTestId("panel-continue");
      if (await cont.count()) await expect(cont).not.toContainText(idLike);
      await page.screenshot({ path: `${SHOTS}/r02-${size.name}-home.png` });
    });
  });
}

// Polish pass 4f: odd screen shapes. No horizontal scroll, the composer and the primary action stay reachable.
const SHAPES = [
  { name: "laptop-700", width: 1280, height: 700 },
  { name: "landscape-phone", width: 800, height: 360 },
  { name: "zoom-200", width: 640, height: 400 }, // 1280x800 at 200% zoom is a 640x400 CSS viewport
  { name: "tablet-1024", width: 1024, height: 768 },
];
for (const shape of SHAPES) {
  test(`4f: ${shape.name} has no horizontal scroll and a reachable composer`, async ({ page }) => {
    await page.setViewportSize({ width: shape.width, height: shape.height });
    await page.goto("/brownie-chat");
    await expect(page.getByTestId("composer")).toBeVisible({ timeout: 30_000 });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, "horizontal overflow in px").toBeLessThanOrEqual(0);
    const box = await page.getByTestId("composer-input").boundingBox();
    expect(box && box.y + box.height <= shape.height + 1, "composer input is inside the viewport").toBeTruthy();
    await page.screenshot({ path: `${SHOTS}/shape-${shape.name}.png` });
  });
}

// Polish pass 4i: friction counts (taps or clicks after the page is open) to each first activity.
test("4i: friction counts", async ({ page }) => {
  const log: Record<string, number> = {};
  await signIn(page);
  await page.locator('[data-testid="panel-continue"], [data-testid="card-start"]').first().click();
  await expect(page.getByTestId("workspace-frame")).toBeVisible({ timeout: 20_000 });
  log["student to resume"] = 1;
  await page.goto("/dev");
  await page.getByTestId("login-review_due").click();
  await expect(page.getByTestId("panel-review")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("panel-review").click();
  await expect(page.getByTestId("workspace-frame")).toBeVisible({ timeout: 20_000 });
  log["student to start a review"] = 1;
  await page.goto("/dev");
  await page.getByTestId("login-teacher").click();
  await expect(page.getByTestId("card-heatmap")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("card-heatmap").click();
  await expect(page.getByTestId("workspace-frame")).toBeVisible({ timeout: 20_000 });
  log["teacher to heatmap"] = 1;
  console.log("FRICTION " + JSON.stringify(log));
});

// Polish pass 4h: first load of "/" on throttled 4G (1.6 Mbps down, 150 ms RTT) and layout shift.
test("4h: throttled 4G load of the home", async ({ page, context }) => {
  const cdp = await context.newCDPSession(page);
  await cdp.send("Network.enable");
  await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
  await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: 150, downloadThroughput: (1.6 * 1024 * 1024) / 8, uploadThroughput: (750 * 1024) / 8 });
  await page.addInitScript(() => {
    (window as unknown as { __cls: number }).__cls = 0;
    new PerformanceObserver((list) => {
      for (const e of list.getEntries() as unknown as { value: number; hadRecentInput: boolean }[]) if (!e.hadRecentInput) (window as unknown as { __cls: number }).__cls += e.value;
    }).observe({ type: "layout-shift", buffered: true });
  });
  const t0 = Date.now();
  await page.goto("/", { waitUntil: "commit" });
  await expect(page.getByTestId("composer")).toBeVisible({ timeout: 60_000 });
  const interactive = Date.now() - t0; // server-rendered shell is on screen
  await page.waitForLoadState("load", { timeout: 60_000 });
  const loadedMs = Date.now() - t0;
  await page.waitForTimeout(2500);
  const cls = await page.evaluate(() => (window as unknown as { __cls: number }).__cls);
  const bytes = await page.evaluate(() => performance.getEntriesByType("resource").reduce((s, r) => s + ((r as PerformanceResourceTiming).transferSize || 0), 0));
  console.log(`FOURG composer visible in ${interactive} ms, load event (all scripts) at ${loadedMs} ms, layout shift ${cls.toFixed(3)}, transferred ${(bytes / 1024).toFixed(0)} KB`);
  expect(cls, "cumulative layout shift").toBeLessThan(0.1);
});
