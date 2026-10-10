import { expect, test, type Page } from "@playwright/test";

/**
 * G5 guest onboarding at 360 px: Login -> "Try it without an account" -> pick curriculum, grade,
 * subject -> first-run card (no session yet) -> "Start from the beginning" -> lesson -> practice
 * (wrong answers, hints, the reveal, a similar question) -> Done. Screens go to
 * test-results/screens/guest-*.png. Needs the API with DEV_TOOLS=true and ALLOW_DRAFT_CONTENT=true
 * on a migrated, content-loaded database (docs/UI_PREVIEW.md).
 */
const SCREENS = "test-results/screens";
const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type Option = { id: string; label: string };
type Action = {
  type: string;
  item_id?: string | null;
  item?: { type?: string; options?: Option[] } | null;
};

async function shot(page: Page, name: string) {
  await page.screenshot({ path: `${SCREENS}/guest-${name}.png`, fullPage: true });
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

/** Answer at a human pace: very fast answers are read as disengagement and offer a break. */
async function answer(
  page: Page,
  tracker: ReturnType<typeof trackActions>,
  right: boolean,
  reportLongSilence = false,
) {
  await page.waitForTimeout(6500);
  const keepGoing = page.getByRole("button", { name: "Keep going", exact: true });
  if (await keepGoing.isVisible().catch(() => false)) {
    await keepGoing.click();
    await expect(page.locator(".stem").first()).toBeVisible({ timeout: 20_000 });
    await page.waitForTimeout(1500);
  }
  if (reportLongSilence) {
    // the server decides when a session ends; the spec only reports a long silence with this answer
    await page.route("**/sessions/*/events", async (route) => {
      const body = route.request().postDataJSON();
      body.payload = { ...(body.payload ?? {}), idle_ms: 60 * 60 * 1000 };
      await route.continue({ postData: JSON.stringify(body) });
    });
  }
  const action = tracker.last();
  expect(action?.item_id, "an item is on screen").toBeTruthy();
  const key = await authoredAnswer(page, String(action!.item_id));
  const box = page.getByPlaceholder(/type your answer/i);
  if (await box.isVisible()) {
    await box.fill(right ? key : "999999");
    await page.getByRole("button", { name: /^check$/i }).click();
    return;
  }
  const options = action!.item?.options ?? [];
  const pick = right ? options.find((o) => o.id === key) : options.find((o) => o.id !== key);
  expect(pick, "an option to click").toBeTruthy();
  await page.getByRole("button", { name: pick!.label || pick!.id, exact: true }).click();
}

test.describe("G5 guest onboarding at 360 px", () => {
  test("guest start, first run, lesson, practice with help, reveal, similar item, done", async ({
    page,
  }) => {
    test.setTimeout(300_000);
    const tracker = trackActions(page);

    // Login page offers a way in without an account
    await page.goto("/login");
    await expectPhoneLayout(page);
    await page.getByTestId("try-guest").click();
    await expect(page).toHaveURL(/\/start/);
    await expect(page.getByRole("heading", { name: "Let's get started" })).toBeVisible();
    await expect(page.getByLabel(/name|email|phone|school/i)).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Start" })).toBeDisabled();
    await expectPhoneLayout(page);
    await shot(page, "01-start");

    // Context picker: curriculum -> grade -> subject
    await page.getByLabel("Curriculum").selectOption("bhutan");
    await page.getByLabel("Grade").selectOption("9");
    await page.getByLabel("Subject").selectOption("math");
    await shot(page, "02-start-chosen");
    await page.getByRole("button", { name: "Start" }).click();
    await expect(page).toHaveURL(/\/subjects/);

    // First run: a choice, not a test. Nothing has started and no session exists yet.
    const card = page.getByTestId("first-run");
    await expect(card).toBeVisible();
    await expect(card).not.toContainText(/\btest\b|marks|score/i);
    await expect(card.getByRole("button", { name: "Quick warm-up to find where to start" })).toBeVisible();
    await expectPhoneLayout(page);
    await shot(page, "03-first-run");
    const token = await page.evaluate(() => localStorage.getItem("yt_token"));
    const todayRes = await page.request.get(`${API}/students/me/today`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const today = await todayRes.json();
    expect(today.resume, "no session before the student chooses").toBeNull();
    expect(today.offer).toBe("first_run");

    // Skip the warm-up: practice starts on the first skill still to learn, with its lesson
    await card.getByRole("button", { name: "Start from the beginning" }).click();
    await expect(page).toHaveURL(/\/session\//);
    await expect(page.locator(".lp")).toBeVisible({ timeout: 20_000 });
    await expectPhoneLayout(page);
    await shot(page, "04-lesson-first-beat");
    for (let i = 0; i < 12; i++) {
      const start = page.getByRole("button", { name: "Start practice" });
      if (await start.isVisible()) break;
      while (await page.getByRole("button", { name: "Next step", exact: true }).isVisible()) {
        await page.getByRole("button", { name: "Next step", exact: true }).click();
      }
      await page.getByRole("button", { name: "Continue", exact: true }).click();
    }
    await shot(page, "05-lesson-last-beat");
    await page.getByRole("button", { name: "Start practice" }).click();

    // Practice: wrong answers climb the help ladder until the solution can be shown
    await expect(page.locator(".stem").first()).toBeVisible({ timeout: 20_000 });
    await shot(page, "06-practice-item");
    let revealed = false;
    for (let attempt = 0; attempt < 8 && !revealed; attempt++) {
      await answer(page, tracker, false);
      const reveal = page.getByRole("button", { name: "Show the solution" });
      await expect(
        page.getByTestId("check-your-work").or(page.locator(".banner")).or(reveal).first(),
      ).toBeVisible({ timeout: 20_000 });
      if (attempt === 0) await shot(page, "07-first-wrong");
      if (await reveal.isVisible()) {
        await reveal.click();
        revealed = true;
      }
    }
    expect(revealed, "the solution became available after repeated misses").toBeTruthy();
    await expect(page.getByRole("heading", { name: "Show the solution" })).toBeVisible();
    await expectPhoneLayout(page);
    await shot(page, "08-reveal");

    // A similar question follows; answer it right
    await page.getByRole("button", { name: "Try a similar one" }).click();
    await expect(page.locator(".stem").first()).toBeVisible({ timeout: 20_000 });
    await shot(page, "09-similar-item");
    await Promise.all([
      page.waitForResponse((r) => r.url().includes("/events") && r.request().method() === "POST"),
      answer(page, tracker, true),
    ]);

    // End the session the way an idle student would, then read the Done screen
    await expect(page.locator(".stem").first()).toBeVisible({ timeout: 20_000 });
    await answer(page, tracker, true, true);
    await expect(page.getByRole("heading", { name: "Nice work" })).toBeVisible({ timeout: 20_000 });
    await expectPhoneLayout(page);
    await shot(page, "10-done");
  });
});
