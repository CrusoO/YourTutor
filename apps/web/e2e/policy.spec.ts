import { expect, test, type Page } from "@playwright/test";
import { devLogin, enter } from "./shell";

/**
 * G2b at 360 px: the wheel-spinning quick check (probe), the other-way view that follows it, and
 * the calm break offer after fast answers. Screens go to test-results/screens/policy-*.png.
 * Needs the API with DEV_TOOLS=true and ALLOW_DRAFT_CONTENT=true on a seeded database.
 */
const SCREENS = "test-results/screens";
const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type Action = { type: string; item_id?: string | null; extras?: Record<string, unknown> };

async function shot(page: Page, name: string) {
  await page.screenshot({ path: `${SCREENS}/policy-${name}.png`, fullPage: true });
}

async function expectPhoneLayout(page: Page) {
  expect(page.viewportSize()?.width).toBe(360);
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow, "no horizontal scroll at 360 px").toBeLessThanOrEqual(0);
}

function trackActions(page: Page): { last: () => Action | null } {
  let latest: Action | null = null;
  page.on("response", async (res) => {
    if (!/\/sessions(\/|$)/.test(res.url()) || res.request().method() === "OPTIONS") return;
    try {
      const body = await res.json();
      if (body?.action) latest = body.action as Action;
    } catch {
      /* not JSON */
    }
  });
  return { last: () => latest };
}

async function reseed(request: import("@playwright/test").APIRequestContext, name: string, code: string) {
  const reset = await request.post(`${API}/dev/seed?only=${name}`, { timeout: 400_000 });
  expect(reset.ok(), await reset.text()).toBeTruthy();
  await expect
    .poll(
      async () =>
        (
          await request.post(`${API}/auth/student-login`, {
            data: { family_code: code, pin: "1234" },
          })
        ).status(),
      { timeout: 30_000 },
    )
    .toBe(200);
}

async function authoredAnswer(page: Page, itemId: string): Promise<string> {
  const res = await page.request.get(`${API}/dev/items/${encodeURIComponent(itemId)}/answer`);
  expect(res.ok(), await res.text()).toBeTruthy();
  return String((await res.json()).answer);
}

async function submitAndWait(page: Page, click: () => Promise<void>) {
  const [res] = await Promise.all([
    page.waitForResponse(
      (r) => /\/sessions\/[^/]+\/events/.test(r.url()) && r.request().method() === "POST",
    ),
    click(),
  ]);
  await res.finished();
  await page.waitForTimeout(150); // let the action tracker and the screen catch up
}

async function answerRight(page: Page, tracker: ReturnType<typeof trackActions>) {
  const key = await authoredAnswer(page, String(tracker.last()!.item_id));
  const box = page.getByPlaceholder(/type your answer/i);
  if (await box.isVisible()) {
    await box.fill(key);
    await submitAndWait(page, () => page.getByRole("button", { name: /^check$/i }).click());
    return;
  }
  const options = (tracker.last() as unknown as { item?: { options?: { id: string; label: string }[] } })
    .item?.options ?? [];
  const pick = options.find((o) => o.id === key);
  expect(pick, "an option to click").toBeTruthy();
  await submitAndWait(page, () =>
    page.getByRole("button", { name: pick!.label || pick!.id, exact: true }).click(),
  );
}

async function answerWrong(page: Page, tracker: ReturnType<typeof trackActions>) {
  const box = page.getByPlaceholder(/type your answer/i);
  if (await box.isVisible()) {
    await box.fill("0");
    await submitAndWait(page, () => page.getByRole("button", { name: /^check$/i }).click());
    return;
  }
  const key = await authoredAnswer(page, String(tracker.last()!.item_id));
  const options = (tracker.last() as unknown as { item?: { options?: { id: string; label: string }[] } })
    .item?.options ?? [];
  const wrong = options.find((o) => o.id !== key);
  expect(wrong, "a wrong option to click").toBeTruthy();
  await submitAndWait(page, () =>
    page.getByRole("button", { name: wrong!.label || wrong!.id, exact: true }).click(),
  );
}

test.describe("G2b policy rules at 360 px", () => {
  test.beforeEach(() => {
    test.setTimeout(420_000);
  });

  test("wheel_spinning: a third miss shows a quick check, then another way of looking at it", async ({
    page,
    request,
  }) => {
    await reseed(request, "wheel_spinning", "DEVWHL");
    const tracker = trackActions(page);
    await devLogin(page, "Wheel spinning");
    await expect(page.getByTestId("greeting")).toContainText("Wen");
    await enter(page, "panel-continue");
    await expect(page.locator(".stem").first()).toBeVisible({ timeout: 20_000 });
    // two items were already missed in this open session; the question is waiting
    await expectPhoneLayout(page);
    await shot(page, "01-resumed-after-two-misses");

    // the third miss in a row: a short check on the skill before it, not another hint
    await answerWrong(page, tracker);
    await expect(page.getByTestId("probe")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Quick check" })).toBeVisible();
    await expect(page.getByRole("button", { name: /^help$/i })).toHaveCount(0);
    await expectPhoneLayout(page);
    await shot(page, "02-quick-check");

    // a right answer: the skill is shown another way, then back to the question
    await answerRight(page, tracker);
    await expect(page.getByTestId("other-view")).toBeVisible();
    await expectPhoneLayout(page);
    await shot(page, "03-another-way");
    while (await page.getByRole("button", { name: "Show next step" }).isVisible()) {
      await page.getByRole("button", { name: "Show next step" }).click();
    }
    await page.getByRole("button", { name: /^continue$/i }).click();
    await expect(page.locator(".stem").first()).toBeVisible();
    await expect(page.getByTestId("probe")).toHaveCount(0);
    await shot(page, "04-back-to-the-question");
  });

  test("three fast answers offer a calm break; taking it saves the place", async ({
    page,
    request,
  }) => {
    await reseed(request, "slip_prone", "DEVSLP");
    const tracker = trackActions(page);
    await devLogin(page, "Slip prone");
    await enter(page, "nav-chapters");
    await page.getByTestId("chapter-bhutan_class9").click();
    await page.getByRole("button", { name: "Continue this chapter" }).click();
    await expect(page.getByPlaceholder(/type your answer/i)).toBeVisible({ timeout: 20_000 });
    let answers = 0;
    for (let i = 0; i < 30 && answers < 8; i++) {
      if (await page.getByTestId("break-or-switch").isVisible()) break;
      const next = page.getByRole("button", { name: "Continue", exact: true });
      if (await next.isVisible()) {
        await submitAndWait(page, () => next.click());
        continue;
      }
      if (await page.getByPlaceholder(/type your answer/i).isVisible()) {
        await answerRight(page, tracker); // as fast as a script can answer
        answers += 1;
      } else {
        await page.waitForTimeout(300);
      }
    }
    await expect(page.getByTestId("break-or-switch")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Want a short break?" })).toBeVisible();
    await expect(page.getByTestId("break-or-switch")).not.toContainText(/guess|rushing|careless|too fast/i);
    await expectPhoneLayout(page);
    await shot(page, "05-break-or-switch");
    await page.getByRole("button", { name: "Take a short break" }).click();
    await expect(page.getByRole("heading", { name: "Nice work" })).toBeVisible();
    await expect(page.getByText(/taking a break is a good idea/i)).toBeVisible();
    await expectPhoneLayout(page);
    await shot(page, "06-break-saved");
    await page.goto("/subjects");
    await expect(page.getByRole("button", { name: /resume/i })).toBeVisible();
  });
});
