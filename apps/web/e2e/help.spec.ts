import { expect, test, type Page } from "@playwright/test";
import { devLogin, enter } from "./shell";

/**
 * G2a at 360 px: the stuck-point picker (ask before telling) and Check your work after a slip.
 * Uses the slip_prone scenario (every skill at level 4, so questions are application items).
 * Screens go to test-results/screens/help-*.png. Needs the API with DEV_TOOLS=true and
 * ALLOW_DRAFT_CONTENT=true on a seeded database (docs/UI_PREVIEW.md).
 */
const SCREENS = "test-results/screens";
const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type Action = { type: string; item_id?: string | null; item?: { type?: string; options?: { id: string; label: string }[] } | null };

async function shot(page: Page, name: string) {
  await page.screenshot({ path: `${SCREENS}/help-${name}.png`, fullPage: true });
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

async function authoredAnswer(page: Page, itemId: string): Promise<string> {
  const res = await page.request.get(`${API}/dev/items/${encodeURIComponent(itemId)}/answer`);
  expect(res.ok(), await res.text()).toBeTruthy();
  return String((await res.json()).answer);
}

/** Click through lesson-free interruptions until a question with an answer box is on screen. */
async function untilQuestion(page: Page, tracker: ReturnType<typeof trackActions>) {
  for (let i = 0; i < 6; i++) {
    if (await page.getByPlaceholder(/type your answer/i).isVisible()) return;
    const next = page.getByRole("button", { name: "Continue", exact: true });
    if (await next.isVisible()) {
      await next.click();
    } else {
      await page.waitForTimeout(500);
    }
  }
  expect(tracker.last()?.type).toBeTruthy();
  await expect(page.getByPlaceholder(/type your answer/i)).toBeVisible();
}

async function typeAnswer(page: Page, value: string) {
  await page.getByPlaceholder(/type your answer/i).fill(value);
  await page.getByRole("button", { name: /^check$/i }).click();
}

async function openFirstQuestion(page: Page, tracker: ReturnType<typeof trackActions>) {
  await devLogin(page, "Slip prone");
  await enter(page, "nav-chapters");
  await page.getByTestId("chapter-bhutan_class9").click();
  await page.getByRole("button", { name: "Continue this chapter" }).click();
  await expect(page).toHaveURL(/\/session\//);
  await untilQuestion(page, tracker);
}

test.describe("G2a help and slips at 360 px", () => {
  // Every test starts from a freshly seeded student: the picker is offered once per item, so a
  // resumed session would skip it.
  test.beforeEach(async ({ request }) => {
    test.setTimeout(420_000);
    const reset = await request.post(`${API}/dev/seed?only=slip_prone`, { timeout: 400_000 });
    expect(reset.ok(), await reset.text()).toBeTruthy();
    // the new student must be able to log in before the browser tries
    await expect
      .poll(
        async () =>
          (
            await request.post(`${API}/auth/student-login`, {
              data: { family_code: "DEVSLP", pin: "1234" },
            })
          ).status(),
        { timeout: 30_000 },
      )
      .toBe(200);
  });

  test("slip_prone: picker, step hint, restate, check your work, ladder hints", async ({ page }) => {
    const tracker = trackActions(page);
    await openFirstQuestion(page, tracker);

    // Question 1: Help opens the picker instead of a hint
    await expectPhoneLayout(page);
    await shot(page, "01-question-with-help");
    await page.getByTestId("help-button").click();
    await expect(page.getByRole("heading", { name: "Where are you stuck?" })).toBeVisible();
    for (const label of [
      "I don't know how to start",
      "I'm stuck at a step",
      "I don't understand the question",
      "I think my answer might be right",
    ]) {
      await expect(page.getByRole("button", { name: label })).toBeVisible();
    }
    await expectPhoneLayout(page);
    await shot(page, "02-stuck-picker");

    // "I'm stuck at a step" lists numbered steps only, then gives that step's hint
    await page.getByRole("button", { name: "I'm stuck at a step" }).click();
    await expect(page.getByRole("heading", { name: "Which step are you on?" })).toBeVisible();
    await expect(page.getByRole("button", { name: /^Step 1$/ })).toBeVisible();
    await expectPhoneLayout(page);
    await shot(page, "03-which-step");
    await page.getByRole("button", { name: /^Step 1$/ }).click();
    await expect(page.getByText("A hint for that step")).toBeVisible();
    await expect(page.getByTestId("hint-text")).toBeVisible();
    await shot(page, "04-step-hint");

    // A slip (wrong sign) on the first answer: Check your work, no hint level used
    const first = tracker.last();
    const key = await authoredAnswer(page, String(first!.item_id));
    const numeric = Number.isFinite(Number(key));
    test.skip(!numeric, "the served item has a non-numeric answer, so no slip pattern applies");
    await typeAnswer(page, key.startsWith("-") ? key.slice(1) : `-${key}`);
    await expect(page.getByTestId("check-your-work")).toBeVisible();
    await expect(page.getByTestId("check-your-work")).toContainText(/signs in each line/i);
    await expect(page.getByTestId("check-your-work")).not.toContainText(key.startsWith("-") ? key.slice(1) : key);
    await expectPhoneLayout(page);
    await shot(page, "05-check-your-work");

    // A second wrong answer goes to the normal hint ladder
    await typeAnswer(page, "123456");
    await expect(page.getByTestId("hint-text")).toBeVisible();
    await shot(page, "06-second-wrong-hint");

    // Then the right answer moves on
    await typeAnswer(page, key);
    await expect(page.locator(".stem").first()).toBeVisible();
  });

  test("slip_prone: 'I don't understand the question' restates it; a second Help is a ladder hint", async ({
    page,
  }) => {
    const tracker = trackActions(page);
    await openFirstQuestion(page, tracker);
    await page.getByTestId("help-button").click();
    await page.getByRole("button", { name: "I don't understand the question" }).click();
    await expect(page.getByText("The question again", { exact: true })).toBeVisible();
    await expect(page.getByTestId("hint-text")).toContainText(/read the question again/i);
    await expectPhoneLayout(page);
    await shot(page, "07-restated-question");
    await page.getByTestId("help-button").click();
    await expect(page.getByTestId("hint-text")).not.toContainText(/read the question again/i);
    await expect(page.getByText("The question again", { exact: true })).toHaveCount(0);
    await shot(page, "07b-second-help-ladder-hint");
  });

  test("slip_prone: 'I think my answer might be right' asks to submit", async ({ page }) => {
    const tracker = trackActions(page);
    await openFirstQuestion(page, tracker);
    await page.getByTestId("help-button").click();
    await page.getByRole("button", { name: "I think my answer might be right" }).click();
    await expect(page.getByText(/go ahead and type your answer/i)).toBeVisible();
    await expectPhoneLayout(page);
    await shot(page, "08-might-be-right");
    await page.getByTestId("help-button").click();
    await expect(page.getByTestId("hint-text")).toBeVisible(); // the picker is offered once per item
    await shot(page, "09-second-help-is-a-hint");
  });
});
