import { expect, type Page } from "@playwright/test";

/**
 * Entry points for the UI-1 front door. Every flow starts at "/" (the role home), opens its workflow
 * through a home card or a sidebar item, and then continues on the screen the workspace panel opened.
 * Selectors are data-testid, never button text.
 */
export const nameOf = (title: string) => title.toLowerCase().replace(/\s+/g, "_");

/** Sign in as a preview scenario student (the dev page button) and land on the role home. */
export async function devLogin(page: Page, title: string) {
  await page.goto("/dev");
  await page.getByTestId(`login-${nameOf(title)}`).click();
  await expect(page).toHaveURL(/\/$/, { timeout: 30_000 });
  await expect(page.getByTestId("hero")).toBeVisible();
  await expect(page.getByTestId("greeting")).not.toHaveText("", { timeout: 20_000 });
}

/**
 * Open a workflow from the home: a card (card-continue, card-resume, ...) or a sidebar item (nav-today,
 * nav-chapters, ...). Below 1024 px the sidebar lives in the menu drawer, so it is opened first. The panel
 * shows the existing screen in a frame; the flow then continues on that screen's own address, so every
 * legacy screen is still exercised exactly as before, but reached through the new entry point.
 */
export async function enter(page: Page, entry: string) {
  if (entry.startsWith("card-")) {
    // Home cards load after the page does: wait for the card, never open the menu for it.
    await expect(page.locator(`[data-testid="${entry}"]:visible`).first()).toBeVisible({ timeout: 30_000 });
  } else {
    // Sidebar items live in the menu drawer below 1024 px.
    const target = page.locator(`[data-testid="${entry}"]:visible`).first();
    if (!(await target.isVisible())) {
      const menu = page.getByTestId("menu-open");
      if (await menu.isVisible()) await menu.click();
    }
  }
  await page.locator(`[data-testid="${entry}"]:visible`).first().click();
  const frame = page.getByTestId("workspace-frame");
  await expect(frame).toBeVisible({ timeout: 20_000 });
  const src = await frame.getAttribute("src");
  expect(src, "the panel opened a screen").toBeTruthy();
  await page.goto(src!);
}
