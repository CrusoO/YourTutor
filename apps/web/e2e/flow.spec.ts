import { expect, test, type Page } from "@playwright/test";

/**
 * S1b student flow at 360 px: login -> Subjects -> Chapter map -> Chapter page -> lesson ->
 * practice (wrong -> hint -> retry) -> Done, plus Skip ahead. Screens go to
 * test-results/screens/flow-*.png. Needs the API with DEV_TOOLS=true and ALLOW_DRAFT_CONTENT=true
 * on a seeded database (docs/UI_PREVIEW.md).
 */
const SCREENS = "test-results/screens";
const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type Option = { id: string; label: string };
type Action = {
  type: string;
  item_id?: string | null;
  item?: { type?: string; options?: Option[] } | null;
  lesson?: { id: string } | null;
  extras?: Record<string, unknown>;
};

async function shot(page: Page, name: string) {
  await page.screenshot({ path: `${SCREENS}/flow-${name}.png`, fullPage: true });
}

async function expectPhoneLayout(page: Page) {
  expect(page.viewportSize()?.width).toBe(360);
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow, "no horizontal scroll at 360 px").toBeLessThanOrEqual(0);
}

/** Remember the latest action the server sent, so the spec can look up the authored answer. */
function trackActions(page: Page): { last: () => Action | null } {
  let latest: Action | null = null;
  page.on("response", async (res) => {
    const url = res.url();
    if (!/\/sessions(\/|$)|skip-ahead/.test(url) || res.request().method() === "OPTIONS") return;
    try {
      const body = await res.json();
      if (body?.action) latest = body.action as Action;
    } catch {
      /* not JSON */
    }
  });
  return { last: () => latest };
}

async function logInAs(page: Page, title: string) {
  await page.goto("/dev");
  await page.getByRole("button", { name: `Log in as ${title}` }).click();
  await expect(page).toHaveURL(/\/subjects/);
  await expect(page.getByRole("heading", { name: /what do you want to learn/i })).toBeVisible();
}

async function openChapter(page: Page, testId: string) {
  await page.getByTestId("subject-math").click();
  await expect(page).toHaveURL(/\/chapters$/);
  await expect(page.getByTestId(testId)).toBeVisible();
}

async function authoredAnswer(page: Page, itemId: string): Promise<string> {
  const res = await page.request.get(`${API}/dev/items/${encodeURIComponent(itemId)}/answer`);
  expect(res.ok(), await res.text()).toBeTruthy();
  return String((await res.json()).answer);
}

/** Answer the item on screen: the right answer, or a wrong one. */
async function answer(page: Page, tracker: ReturnType<typeof trackActions>, right: boolean) {
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
  const correct = options.find((o) => o.id === key);
  const pick = right ? correct : options.find((o) => o.id !== key);
  expect(pick, "an option to click").toBeTruthy();
  await page.getByRole("button", { name: pick!.label || pick!.id, exact: true }).click();
}

test.describe("S1b student flow at 360 px", () => {
  test.beforeAll(async ({ request }) => {
    test.setTimeout(300_000);
    const reset = await request.post(`${API}/dev/seed`, { timeout: 280_000 });
    expect(reset.ok(), await reset.text()).toBeTruthy();
  });

  test("new_student: map, skip ahead, lesson, practice (wrong, hint, retry), done", async ({
    page,
  }) => {
    const tracker = trackActions(page);
    await logInAs(page, "New student");
    await expect(page.getByText("Hi Nima")).toBeVisible();
    await expectPhoneLayout(page);
    await shot(page, "01-subjects");

    // Chapter map: one recommended chapter, one coming-soon card
    await openChapter(page, "chapter-bhutan_class9");
    await expect(page.getByText("Start here")).toHaveCount(1);
    await expect(page.getByTestId("chapter-bhutan_class9_quadratics")).toContainText("Coming soon");
    await expect(page.getByTestId("chapter-bhutan_class9_quadratics")).not.toHaveAttribute("href", /.*/);
    await expectPhoneLayout(page);
    await shot(page, "02-chapter-map");

    // Chapter page: skill path
    await page.getByTestId("chapter-bhutan_class9").click();
    await expect(page.getByRole("heading", { name: "Linear equations" })).toBeVisible();
    await expect(page.locator(".skill.current")).toHaveCount(1);
    await expectPhoneLayout(page);
    await shot(page, "03-skill-path");

    // Skip ahead on the first skill: two hard questions, no hints
    await page.locator(".skill.current").getByRole("button", { name: "Skip ahead" }).click();
    await expect(page.getByRole("heading", { name: "Show what you know" })).toBeVisible();
    await expect(page.getByText("Question 1 of 2")).toBeVisible();
    await expect(page.getByRole("button", { name: /^hint$/i })).toHaveCount(0);
    await expectPhoneLayout(page);
    await shot(page, "04-skip-ahead-question");
    await answer(page, tracker, true);
    await expect(page.getByText("Question 2 of 2")).toBeVisible();
    await answer(page, tracker, true);
    await expect(page.getByTestId("test-out-result")).toHaveAttribute("data-passed", "true");
    await expectPhoneLayout(page);
    await shot(page, "05-skip-ahead-passed");

    // Back on the path the first skill says Can do it and the next one is up
    await page.getByRole("button", { name: "Back to chapters" }).click();
    await page.getByTestId("chapter-bhutan_class9").click();
    await expect(page.getByTestId("skill-MATH.ARITH.INTEGERS.OPERATIONS")).toContainText("Can do it");
    await expect(page.locator(".skill.current")).toContainText("Lesson, then practice");
    await shot(page, "06-path-after-skip");

    // Start: the next skill is new, so it opens with its lesson
    await page.getByRole("button", { name: "Continue this chapter" }).click();
    await expect(page).toHaveURL(/\/session\//);
    await expect(page.locator(".lp")).toBeVisible({ timeout: 20_000 });
    await expectPhoneLayout(page);
    await shot(page, "07-lesson-first-beat");
    for (let i = 0; i < 12; i++) {
      const start = page.getByRole("button", { name: "Start practice" });
      if (await start.isVisible()) break;
      while (await page.getByRole("button", { name: "Next step", exact: true }).isVisible()) {
        await page.getByRole("button", { name: "Next step", exact: true }).click();
      }
      await page.getByRole("button", { name: "Continue", exact: true }).click();
    }
    await shot(page, "08-lesson-last-beat");
    await page.getByRole("button", { name: "Start practice" }).click();

    // Practice: wrong answer, hint, retry
    await expect(page.locator(".stem")).toBeVisible({ timeout: 20_000 });
    await expectPhoneLayout(page);
    await shot(page, "09-practice-item");
    await answer(page, tracker, false);
    await expect(page.locator(".banner")).toBeVisible();
    await expectPhoneLayout(page);
    await shot(page, "10-practice-hint");
    const stemBefore = await page.locator(".stem").first().textContent();
    await answer(page, tracker, true);
    // a correct retry moves straight on to the next question
    await expect(page.locator(".stem").first()).not.toHaveText(stemBefore ?? "");
    await expectPhoneLayout(page);
    await shot(page, "11-practice-next-item");

    // End the session the way an idle student would (the server decides; the spec only reports
    // a long silence with the next answer) and read the Done screen
    await page.route("**/sessions/*/events", async (route) => {
      const body = route.request().postDataJSON();
      body.payload = { ...(body.payload ?? {}), idle_ms: 60 * 60 * 1000 };
      await route.continue({ postData: JSON.stringify(body) });
    });
    await answer(page, tracker, true);
    await expect(page.getByRole("heading", { name: "Nice work" })).toBeVisible();
    await expect(page.getByText(/you were away for a while/i)).toBeVisible();
    await expect(page.getByText(/active minutes left today/i)).toBeVisible();
    await expect(page.locator("main")).not.toContainText(/streak|rank|score|points/i);
    await expect(page.locator("main")).not.toContainText(/\bidle\b|soft_cap|hard_cap/i);
    await expectPhoneLayout(page);
    await shot(page, "12-done");
    await page.getByRole("button", { name: "Keep going" }).click();
    await expect(page).toHaveURL(/\/chapters\/bhutan_class9/);
  });

  test("mid_chapter: statuses on the map and the path, resume, skip ahead missed", async ({
    page,
  }) => {
    const tracker = trackActions(page);
    await logInAs(page, "Mid chapter");
    await expect(page.getByText("Hi Mina")).toBeVisible();
    await expect(page.getByRole("button", { name: /resume/i })).toBeVisible();
    await shot(page, "20-mid-subjects");
    await openChapter(page, "chapter-bhutan_class9");
    // chapter status is the weakest skill (ARCHITECTURE 11.3); the card also counts what is done
    await expect(page.getByTestId("chapter-bhutan_class9")).toContainText(/[1-9]\d*\/12 skills you can do/);
    await expectPhoneLayout(page);
    await shot(page, "21-mid-chapter-map");
    await page.getByTestId("chapter-bhutan_class9").click();
    await expect(page.locator(".chip-can_do_it").first()).toBeVisible();
    await expect(page.locator(".skill[data-unlocked='false']").first()).toBeVisible();
    await expectPhoneLayout(page);
    await shot(page, "22-mid-skill-path");

    // A missed skip ahead returns to the path with no penalty wording
    await page.locator(".skill.current").getByRole("button", { name: "Skip ahead" }).click();
    await expect(page.getByText("Question 1 of 2")).toBeVisible();
    await answer(page, tracker, false);
    await expect(page.getByText("Question 2 of 2")).toBeVisible();
    await answer(page, tracker, false);
    const result = page.getByTestId("test-out-result");
    await expect(result).toHaveAttribute("data-passed", "false");
    await expect(result).toContainText("Let's practise it together");
    await expect(result).not.toContainText(/fail|wrong|lost|penalt|score/i);
    await expectPhoneLayout(page);
    await shot(page, "23-mid-skip-missed");
    await page.getByRole("button", { name: "Back to chapters" }).click();
    await expect(page).toHaveURL(/\/chapters$/);
  });
});
