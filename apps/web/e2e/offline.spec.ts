import { expect, test, type Page } from "@playwright/test";

/**
 * G9: practice without a network at 360 px. A guest downloads the chapter pack while online, goes
 * offline, practises (answers marked in the browser by the same policy as the server), comes back
 * online, and the queued events are replayed by the server. Screens: test-results/screens/offline-*.png.
 */
const SCREENS = "test-results/screens";
const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

async function shot(page: Page, name: string) {
  await page.screenshot({ path: `${SCREENS}/offline-${name}.png`, fullPage: true });
}

async function authoredAnswer(page: Page, itemId: string): Promise<string> {
  const res = await page.request.get(`${API}/dev/items/${encodeURIComponent(itemId)}/answer`);
  expect(res.ok(), await res.text()).toBeTruthy();
  return String((await res.json()).answer);
}

test("download, practise offline, come back online and sync", async ({ page, context }) => {
  test.setTimeout(240_000);
  await page.goto("/login");
  await page.getByTestId("try-guest").click();
  await page.getByLabel("Curriculum").selectOption("bhutan");
  await page.getByLabel("Grade").selectOption("9");
  await page.getByLabel("Subject").selectOption("math");
  await page.getByRole("button", { name: "Start" }).click();
  await expect(page).toHaveURL(/\/subjects/);
  await page.getByTestId("offline-link").click();
  await expect(page.getByTestId("offline-page")).toBeVisible();
  await expect(page.getByTestId("offline-status")).toContainText("You are online");
  await expect(page.getByTestId("offline-status")).toContainText("Nothing is saved");
  await shot(page, "01-before-download");

  await page.getByRole("button", { name: "Download for offline" }).click();
  await expect(page.getByTestId("offline-status")).toContainText("questions saved on this device");
  await shot(page, "02-downloaded");

  await context.setOffline(true);
  await page.evaluate(() => window.dispatchEvent(new Event("offline")));
  await expect(page.getByTestId("offline-status")).toContainText("You are offline");
  await page.getByRole("button", { name: "Start practice" }).click();
  const step = page.getByTestId("offline-step");
  await expect(step).toBeVisible();
  await shot(page, "03-offline-first-step");

  let answered = 0;
  for (let i = 0; i < 30 && answered < 3; i++) {
    const kind = await step.getAttribute("data-action");
    if (kind === "end_session") break;
    const itemId = await step.getAttribute("data-item-id");
    const box = page.getByPlaceholder("Type your answer");
    if (itemId && (await box.isVisible().catch(() => false))) {
      await box.fill(await authoredAnswer(page, itemId));
      await page.getByRole("button", { name: "Check", exact: true }).click();
      answered += 1;
      if (answered === 1) await shot(page, "04-offline-after-first-answer");
    } else {
      await page.getByRole("button", { name: "Continue", exact: true }).first().click();
    }
    await page.waitForTimeout(150);
  }
  expect(answered).toBeGreaterThanOrEqual(1);
  await expect(page.getByTestId("offline-status")).toContainText("Waiting to be sent");
  await shot(page, "05-offline-queue");

  await context.setOffline(false);
  await page.evaluate(() => window.dispatchEvent(new Event("online")));
  await expect(page.getByTestId("offline-message")).toContainText("Your work is saved", {
    timeout: 30_000,
  });
  await expect(page.getByTestId("offline-status")).not.toContainText("Waiting to be sent");
  await shot(page, "06-synced");

  // the server now holds the learner state the offline session produced
  const token = await page.evaluate(() => localStorage.getItem("yt_token"));
  const res = await page.request.get(`${API}/students/me/pack`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const pack = await res.json();
  expect(Object.keys(pack.learner.mastery).length).toBeGreaterThan(0);
  expect(Object.keys(pack.learner.ladders).length).toBeGreaterThan(0);
});
