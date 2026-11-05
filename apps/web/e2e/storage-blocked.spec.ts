import { expect, test } from "@playwright/test";

/**
 * P0-B: with localStorage and sessionStorage both blocked (private mode, blocked site data) the guest
 * start still works and the page says sign-in lasts only for this tab. Needs the API on a migrated,
 * content-loaded database (docs/UI_PREVIEW.md).
 */
test("guest start works with all browser storage disabled", async ({ page }) => {
  await page.addInitScript(() => {
    for (const name of ["localStorage", "sessionStorage"] as const) {
      Object.defineProperty(window, name, {
        configurable: true,
        get() {
          throw new DOMException("The operation is insecure.", "SecurityError");
        },
      });
    }
  });
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));

  await page.goto("/start");
  await expect(page.getByTestId("storage-notice")).toHaveText(
    "Private mode: you'll stay signed in only in this tab.",
  );
  await page.getByLabel("Curriculum").selectOption("bhutan");
  await page.getByLabel("Grade").selectOption("9");
  await page.getByLabel("Subject").selectOption("math");
  await page.getByRole("button", { name: "Start" }).click();
  await expect(page).toHaveURL(/\/subjects/, { timeout: 30_000 });
  expect(errors, "no uncaught errors from storage").toEqual([]);
});
