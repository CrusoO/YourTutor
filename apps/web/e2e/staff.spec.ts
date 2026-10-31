import { expect, test, type Page } from "@playwright/test";

/**
 * G10: the guardian page and the teacher page at 360 px, on the preview scenarios. The guardian of
 * Wen sees Wen's chapter and week; the preview teacher sees only the three students whose family
 * shared (Mina, Sana, Wen), never the other scenario students. Screens: test-results/screens/staff-*.png.
 */
const SCREENS = "test-results/screens";

async function shot(page: Page, name: string) {
  await page.screenshot({ path: `${SCREENS}/staff-${name}.png`, fullPage: true });
}

async function noSideScroll(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow, "no horizontal scroll at 360 px").toBeLessThanOrEqual(0);
}

test("a guardian sees the child's chapters and week, and can change the language", async ({ page }) => {
  await page.goto("/staff/login");
  await expect(page.getByTestId("staff-login")).toBeVisible();
  await noSideScroll(page);
  await shot(page, "01-login");
  await page.getByRole("button", { name: "Guardian of Wen" }).click();
  await expect(page).toHaveURL(/\/guardian/);
  await expect(page.getByRole("heading", { name: "How Wen is doing" })).toBeVisible();
  await expect(page.getByTestId("guardian-week")).toBeVisible();
  await expect(page.getByTestId("guardian-chapters")).toContainText("Can do it");
  await noSideScroll(page);
  const text = (await page.locator("main").innerText()).toLowerCase();
  for (const word of ["rank", "percentile", "streak", "leaderboard", "behind"]) {
    expect(text, word).not.toContain(word);
  }
  await shot(page, "02-guardian");
  await page.getByLabel("Language").selectOption("hi");
  await expect(page.getByLabel("Language")).toHaveValue("hi");
  await page.getByLabel("Language").selectOption("en");
  await expect(page.getByLabel("Language")).toHaveValue("en");
});

test("a teacher sees only the students whose family shared", async ({ page }) => {
  await page.goto("/staff/login");
  await page.getByRole("button", { name: "Preview teacher" }).click();
  await expect(page).toHaveURL(/\/teacher/);
  await expect(page.getByRole("heading", { name: "Your classes" })).toBeVisible();
  const heat = page.getByTestId("teacher-heatmap");
  await expect(heat).toContainText("Wen");
  await expect(heat).toContainText("Mina");
  await expect(heat).toContainText("Sana");
  const all = await page.locator("main").innerText();
  for (const hidden of ["Nima", "Lena", "Rhea", "Alma"]) {
    expect(all, `${hidden} must not appear`).not.toContain(hidden);
  }
  // the preview history has not reached a wheel-spinning alert yet, so the calm empty state shows
  await expect(page.getByTestId("teacher-alerts")).toContainText("No open alerts");
  await expect(page.getByTestId("teacher-stuck")).toBeVisible();
  await expect(page.getByTestId("teacher-review")).toContainText("Nothing waiting");
  await noSideScroll(page);
  await shot(page, "03-teacher");
});
