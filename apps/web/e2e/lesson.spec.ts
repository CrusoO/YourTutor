import { expect, test, type Page } from "@playwright/test";

/**
 * S1a lesson player at 360 px: play LESSON.TWO_STEP beat by beat (no login, /dev/lessons/<id>) and
 * save a screenshot of each beat to test-results/screens/. Needs the API started with
 * DEV_TOOLS=true and ALLOW_DRAFT_CONTENT=true (docs/UI_PREVIEW.md).
 */
const SCREENS = "test-results/screens";
const LESSON = "LESSON.TWO_STEP";

async function shot(page: Page, step: string) {
  await page.screenshot({ path: `${SCREENS}/lesson-${step}.png`, fullPage: true });
}

async function expectPhoneLayout(page: Page) {
  expect(page.viewportSize()?.width).toBe(360);
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow, "no horizontal scroll at 360 px").toBeLessThanOrEqual(0);
}

test.use({ reducedMotion: "reduce" });

test.describe("S1a lesson at 360 px", () => {
  test("the lessons list shows every lesson", async ({ page }) => {
    await page.goto("/dev/lessons");
    await expect(page.getByRole("heading", { name: "Lessons" })).toBeVisible();
    for (const id of ["LESSON.TWO_STEP", "LESSON.ONE_STEP", "LESSON.INVERSE", "LESSON.FRACTION"]) {
      await expect(page.getByText(id, { exact: false }).first()).toBeVisible();
    }
    await expectPhoneLayout(page);
    await shot(page, "0-list");
  });

  test("plays the full lesson beat by beat", async ({ page }) => {
    await page.goto(`/dev/lessons/${LESSON}`);

    // 1. predict
    await expect(page.getByRole("heading", { level: 2 })).toHaveText("How heavy is one box?");
    await expectPhoneLayout(page);
    await shot(page, "1-predict");
    await page.getByRole("button", { name: "4 kg" }).click();
    await expect(page.getByText(/Hold on to that guess/)).toBeVisible();
    await shot(page, "1-predict-guess");
    await page.getByRole("button", { name: "Continue", exact: true }).click();

    // 2. explore: balance scale, take 3 off both sides, then split
    await expect(page.getByText("Tap weights to take them off.")).toBeVisible();
    await shot(page, "2-explore-balance-start");
    await page.getByRole("button", { name: "Take one weight off the left" }).first().click();
    await shot(page, "2-explore-balance-tilted");
    await page.getByRole("button", { name: "Take one weight off the right" }).first().click();
    for (let i = 0; i < 2; i++) {
      await page.getByRole("button", { name: "Take one weight off the left" }).first().click();
      await page.getByRole("button", { name: "Take one weight off the right" }).first().click();
    }
    await shot(page, "2-explore-balance-boxes-only");
    await page.getByRole("button", { name: /split both sides in half/i }).click();
    await expect(page.getByText(/One box balances 4 weights/).first()).toBeVisible();
    await expect(page.getByText(/Checked by the server/)).toBeVisible();
    await expectPhoneLayout(page);
    await shot(page, "2-explore-balance-solved");
    await page.getByRole("button", { name: "Continue", exact: true }).click();

    // 3. explain scene: wait for the question, get it wrong, then right
    await expect(page.getByRole("heading", { level: 2 })).toHaveText("Watch it worked out");
    await shot(page, "3-scene-drawing");
    const group = page.getByRole("group", { name: /after taking 3 off both sides/i });
    await group.waitFor({ state: "visible", timeout: 90_000 });
    await shot(page, "3-scene-question");
    await group.getByRole("button", { name: "2x = 14" }).click();
    await expect(page.getByText(/11 . 3 = 8, not 14/)).toBeVisible();
    await shot(page, "3-scene-wrong-feedback");
    await group.getByRole("button", { name: "2x = 8" }).click();
    await expect(page.getByRole("button", { name: "Play again" })).toBeVisible({ timeout: 90_000 });
    await expect(page.getByTestId("scene-caption")).toContainText("do the same to both sides");
    await expectPhoneLayout(page);
    await shot(page, "3-scene-finished");
    await page.getByRole("button", { name: "Continue", exact: true }).click();

    // 4. worked example: reveal every step
    await expect(page.locator(".lp-problem")).toBeVisible();
    await shot(page, "4-worked-example-first-step");
    while (await page.getByRole("button", { name: "Next step", exact: true }).isVisible()) {
      await page.getByRole("button", { name: "Next step", exact: true }).click();
    }
    await expectPhoneLayout(page);
    await shot(page, "4-worked-example-all-steps");
    await page.getByRole("button", { name: "Continue", exact: true }).click();

    // 5. explore: function graph
    const slider = page.getByRole("slider");
    await expect(slider).toBeVisible();
    await shot(page, "5-explore-graph-start");
    await slider.fill("6");
    await shot(page, "5-explore-graph-too-high");
    await slider.fill("4");
    await expect(page.getByText(/Checked by the server/)).toBeVisible();
    await expectPhoneLayout(page);
    await shot(page, "5-explore-graph-solved");
    await page.getByRole("button", { name: "Continue", exact: true }).click();

    // 6. check (preview mode: the real check item is the first practice question of a session)
    await expect(page.getByRole("heading", { level: 2 })).toHaveText("Your turn");
    await expect(page.getByText(/first practice item/)).toBeVisible();
    await expectPhoneLayout(page);
    await shot(page, "6-check");
  });
});
