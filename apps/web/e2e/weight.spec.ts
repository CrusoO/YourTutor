import { expect, test } from "@playwright/test";

/**
 * Page-weight budget for a lesson screen (PLAN G5 accept). Run against a production build:
 *   npm run build && npx next start -p 3002
 *   PLAYWRIGHT_NO_WEB=true PLAYWRIGHT_BASE_URL=http://127.0.0.1:3002 npx playwright test e2e/weight.spec.ts
 * It adds up the bytes that cross the network (compressed) while the lesson preview loads and
 * checks them against the budget below. Lighthouse itself is not used: this is the same budget
 * as a number that can be checked in CI without a separate Chrome setup.
 */
const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
export const BUDGET = { totalKB: 200, scriptKB: 150, styleKB: 20, imageKB: 0, fontKB: 0 }; // measured 2026-10-10: 130 KB total, 118 KB script

test("a lesson screen stays inside the page-weight budget", async ({ page }) => {
  test.skip(!process.env.PLAYWRIGHT_NO_WEB, "needs a production build: see the comment at the top");
  const lessons = await (await page.request.get(`${API}/dev/lessons`)).json();
  const id = lessons.lessons.find((l: { id: string }) => l.id === "LESSON.TWO_STEP")?.id;
  expect(id, "the two-step lesson is loaded").toBeTruthy();

  const bytes: Record<string, number> = { script: 0, stylesheet: 0, image: 0, font: 0, document: 0, other: 0 };
  const pending: Promise<void>[] = [];
  page.on("requestfinished", (request) => {
    pending.push(
      request.sizes().then((sizes) => {
        const kind = request.resourceType();
        bytes[kind in bytes ? kind : "other"] += sizes.responseBodySize + sizes.responseHeadersSize;
      }),
    );
  });
  await page.goto(`/dev/lessons/${id}`, { waitUntil: "networkidle" });
  await expect(page.locator(".lp")).toBeVisible();
  await Promise.all(pending);

  const kb = (n: number) => Math.round((n / 1024) * 10) / 10;
  const total = Object.values(bytes).reduce((a, b) => a + b, 0);
  console.log(`WEIGHT total ${kb(total)} KB`, JSON.stringify(Object.fromEntries(Object.entries(bytes).map(([k, v]) => [k, kb(v)]))));
  expect(kb(total), "total transferred").toBeLessThanOrEqual(BUDGET.totalKB);
  expect(kb(bytes.script), "scripts").toBeLessThanOrEqual(BUDGET.scriptKB);
  expect(kb(bytes.stylesheet), "styles").toBeLessThanOrEqual(BUDGET.styleKB);
  expect(kb(bytes.image), "images").toBeLessThanOrEqual(BUDGET.imageKB);
  expect(kb(bytes.font), "fonts").toBeLessThanOrEqual(BUDGET.fontKB);
});
