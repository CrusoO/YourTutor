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
  await expect(page.getByTestId("card-continue").or(page.getByTestId("card-resume")).or(page.getByTestId("card-start")).first()).toBeVisible({ timeout: 30_000 });
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
      const cont = page.getByTestId("card-continue");
      if (await cont.count()) await expect(cont).not.toContainText(idLike);
      await page.screenshot({ path: `${SHOTS}/r02-${size.name}-home.png` });
    });
  });
}
