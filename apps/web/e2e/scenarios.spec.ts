import { expect, test, type Page } from "@playwright/test";
import { devLogin, enter } from "./shell";

/**
 * Preview scenarios (python -m app.dev seed_scenarios). One spec per scenario; every screen is
 * saved at 360 px to test-results/screens/. Needs the API started with DEV_TOOLS=true and
 * ALLOW_DRAFT_CONTENT=true against a seeded database (docs/UI_PREVIEW.md).
 */
const SCREENS = "test-results/screens";

type Action = { type: string; item_id?: string; skill_id?: string };

async function shot(page: Page, scenario: string, step: string) {
  await page.screenshot({ path: `${SCREENS}/${scenario}-${step}.png`, fullPage: true });
}

async function expectPhoneLayout(page: Page) {
  expect(page.viewportSize()?.width).toBe(360);
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow, "no horizontal scroll at 360 px").toBeLessThanOrEqual(0);
}

/** The session page shows "…" until the action loads; wait for real content before a screenshot. */
async function waitForSessionScreen(page: Page) {
  await expect(page).toHaveURL(/\/session\//);
  await page.locator(".stem, h1").first().waitFor({ state: "visible", timeout: 20_000 });
}

// UI-1: a scenario login lands on the role home ("/"); the flows open their screen from there.
async function logInAs(page: Page, title: string) {
  await devLogin(page, title);
}

/** Today (minutes left, Resume, raw session types) still exists; S1b's flow starts at Subjects. */
async function openToday(page: Page) {
  await enter(page, "nav-today");
  await expect(page.getByRole("heading", { name: /today/i })).toBeVisible();
}

async function startPractice(page: Page): Promise<Action> {
  const [response] = await Promise.all([
    page.waitForResponse(
      (res) => /\/sessions$/.test(res.url()) && res.request().method() === "POST",
    ),
    page.getByRole("button", { name: /start practice/i }).click(),
  ]);
  await waitForSessionScreen(page);
  return (await response.json()).action as Action;
}

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

test.describe("preview scenarios at 360 px", () => {
  // The specs start sessions, so every run begins from freshly seeded scenarios.
  test.beforeAll(async ({ request }) => {
    test.setTimeout(300_000);
    const reset = await request.post(`${API}/dev/seed`, { timeout: 280_000 });
    expect(reset.ok(), await reset.text()).toBeTruthy();
  });

  test("dev page lists every scenario", async ({ page }) => {
    await page.goto("/dev");
    for (const title of [
      "New student",
      "Mid chapter",
      "Skill at level 4",
      "Review due",
      "All skills level 4",
      "Slip prone",
    ]) {
      await expect(page.getByRole("button", { name: `Log in as ${title}` })).toBeVisible();
    }
    await expect(page.getByText(/not seeded/i)).toHaveCount(0);
    await expectPhoneLayout(page);
    await shot(page, "dev", "01-scenarios");
  });

  test("new_student: first run starts with the prediction", async ({ page }) => {
    await logInAs(page, "New student");
    await expect(page.getByTestId("greeting")).toContainText("Nima");
    await openToday(page);
    await expect(page.getByText("Nima")).toBeVisible();
    await expect(page.getByRole("button", { name: /resume/i })).toHaveCount(0);
    await expectPhoneLayout(page);
    await shot(page, "new_student", "01-today");
    const action = await startPractice(page);
    expect(action.type).toBe("predict");
    await expectPhoneLayout(page);
    await shot(page, "new_student", "02-first-screen");
  });

  test("mid_chapter: resume the open session", async ({ page }) => {
    await logInAs(page, "Mid chapter");
    await expect(page.getByTestId("greeting")).toContainText("Mina");
    await expect(page.getByTestId("card-resume")).toBeVisible();
    await expectPhoneLayout(page);
    await shot(page, "mid_chapter", "01-today");
    await enter(page, "card-resume");
    await waitForSessionScreen(page);
    await expectPhoneLayout(page);
    await shot(page, "mid_chapter", "02-resumed");
  });

  test("skill_at_level_4: resume the open session", async ({ page }) => {
    await logInAs(page, "Skill at level 4");
    await expect(page.getByTestId("greeting")).toContainText("Lena");
    await expect(page.getByTestId("card-resume")).toBeVisible();
    await expectPhoneLayout(page);
    await shot(page, "skill_at_level_4", "01-today");
    await enter(page, "card-resume");
    await waitForSessionScreen(page);
    await expectPhoneLayout(page);
    await shot(page, "skill_at_level_4", "02-resumed");
  });

  test("review_due: the next session opens with a warm-up", async ({ page }) => {
    await logInAs(page, "Review due");
    await expect(page.getByTestId("greeting")).toContainText("Rhea");
    await openToday(page);
    await expect(page.getByText("Rhea")).toBeVisible();
    await expect(page.getByRole("button", { name: /resume/i })).toHaveCount(0);
    await expectPhoneLayout(page);
    await shot(page, "review_due", "01-today");
    const action = await startPractice(page);
    expect(action.type).toBe("warmup_item");
    await expect(page.locator(".stem")).toBeVisible();
    await expectPhoneLayout(page);
    await shot(page, "review_due", "02-warmup-item");
  });

  test("all_skills_level_4: starts extension practice, not a lesson", async ({ page }) => {
    await logInAs(page, "All skills level 4");
    await expect(page.getByTestId("greeting")).toContainText("Alma");
    await openToday(page);
    await expect(page.getByText("Alma")).toBeVisible();
    await expectPhoneLayout(page);
    await shot(page, "all_skills_level_4", "01-today");
    const action = await startPractice(page);
    expect(["show_item", "warmup_item"]).toContain(action.type);
    await expect(page.locator(".stem")).toBeVisible();
    await expectPhoneLayout(page);
    await shot(page, "all_skills_level_4", "02-first-item");
  });
});
