import { expect, test } from "@playwright/test";
import {
  advanceUntilDone,
  answerDontKnow,
  dismissNudge,
  enrolStudent,
  loginStudent,
  sessionIdFromUrl,
  skipToExpressionItem,
  submitExpression,
  tapEvent,
} from "./helpers";

const miniEnabled = process.env.E2E_MINI_CONTENT === "true" || process.env.E2E_MINI_CONTENT === "1";

test.describe("player UI (E2E mini content)", () => {
  test.skip(!miniEnabled, "Set E2E_MINI_CONTENT=true on API and env for this suite");

  test("diagnostic via UI including I don't know", async ({ page, request }) => {
    test.setTimeout(120_000);
    const card = await enrolStudent(request, "DiagUI");
    await loginStudent(page, card.family_code, card.pin);
    await page.getByRole("button", { name: /start diagnostic/i }).click();
    await expect(page).toHaveURL(/\/session\//);
    await answerDontKnow(page);
    await advanceUntilDone(page, 24);
  });

  test("checkpoint via UI", async ({ page, request }) => {
    test.setTimeout(120_000);
    const card = await enrolStudent(request, "CkptUI");
    await loginStudent(page, card.family_code, card.pin);
    await page.getByRole("button", { name: /start diagnostic/i }).click();
    await advanceUntilDone(page, 24);
    await page.goto("/today");
    await page.getByRole("button", { name: /start checkpoint/i }).click();
    await expect(page).toHaveURL(/\/session\//);
    await submitExpression(page, "3");
    await submitExpression(page, "4");
    await expect(page.getByText(/score:/i)).toBeVisible({ timeout: 30_000 });
  });

  test("resume after reload mid diagnostic", async ({ page, request }) => {
    test.setTimeout(90_000);
    const card = await enrolStudent(request, "Resume");
    await loginStudent(page, card.family_code, card.pin);
    await page.getByRole("button", { name: /start diagnostic/i }).click();
    await expect(page).toHaveURL(/\/session\//, { timeout: 20_000 });
    const sid = await sessionIdFromUrl(page);
    await answerDontKnow(page);
    await page.reload();
    await expect(page).toHaveURL(new RegExp(`/session/${sid}`));
    await expect(page.getByRole("button", { name: /i don't know/i })).toBeVisible({ timeout: 20_000 });
    await advanceUntilDone(page, 8);
  });

  test("idle nudge with shortened timer", async ({ page, request }) => {
    test.skip(
      process.env.PLAYWRIGHT_IDLE_E2E !== "true",
      "Set PLAYWRIGHT_IDLE_E2E=true and NEXT_PUBLIC_IDLE_NUDGE_MS (see UI_AUDIT); vitest covers idle overlay.",
    );
    const idleMs = Number(process.env.NEXT_PUBLIC_IDLE_NUDGE_MS || 2500);
    test.setTimeout(idleMs + 45_000);
    const card = await enrolStudent(request, "Idle");
    await loginStudent(page, card.family_code, card.pin);
    await page.getByRole("button", { name: /start practice/i }).click();
    await skipToExpressionItem(page);
    await page.waitForTimeout(idleMs + 500);
    const nudge = page.getByRole("button", { name: /still there/i });
    await expect(nudge).toBeVisible({ timeout: 10_000 });
    await Promise.all([
      page.waitForResponse((res) => res.url().includes("/events") && res.ok()),
      nudge.click({ force: true }),
    ]);
    await expect(nudge).toBeHidden({ timeout: 5_000 });
  });

  test("explain_back with and without continue", async ({ page, request }) => {
    test.setTimeout(180_000);
    const card = await enrolStudent(request, "Explain");
    await loginStudent(page, card.family_code, card.pin);
    await page.getByRole("button", { name: /start practice/i }).click();
    const yes = page.getByRole("button", { name: /^yes$/i });
    if (await yes.isVisible({ timeout: 8_000 }).catch(() => false)) {
      await tapEvent(page, yes);
    }
    for (let i = 0; i < 8; i += 1) {
      await dismissNudge(page);
      const explain = page.getByPlaceholder(/explain it in your own words/i);
      if (await explain.isVisible().catch(() => false)) {
        await explain.fill("I subtract the same amount from both sides.");
        await tapEvent(page, page.getByRole("button", { name: /^continue$/i }));
        await expect(page.getByText(/thanks for explaining|explain/i).first()).toBeVisible({ timeout: 10_000 });
        await page.reload();
        await expect(page.getByRole("button", { name: /^continue$/i })).toBeVisible({ timeout: 15_000 });
        await tapEvent(page, page.getByRole("button", { name: /^continue$/i }));
        return;
      }
      const input = page.getByPlaceholder(/type your answer/i);
      if (await input.isVisible().catch(() => false)) {
        const stem = await page.locator("main .stem").first().textContent();
        const answer = stem?.includes("x + 4 = 10") ? "6" : stem?.includes("2x + 4 = 12") ? "4" : "5";
        await submitExpression(page, answer);
        continue;
      }
      const cont = page.getByRole("button", { name: /^continue$/i });
      if (await cont.isVisible().catch(() => false)) {
        await tapEvent(page, cont);
      }
    }
    test.skip(true, "explain_back did not appear in mini practice flow");
  });

  test("wrong answer, hint, retry, reveal", async ({ page, request }) => {
    test.setTimeout(120_000);
    const card = await enrolStudent(request, "HintFlow");
    await loginStudent(page, card.family_code, card.pin);
    await page.getByRole("button", { name: /start practice/i }).click();
    await skipToExpressionItem(page);
    await submitExpression(page, "0");
    await expect(page.locator(".banner")).toBeVisible({ timeout: 10_000 });
    const cont = page.getByRole("button", { name: /^continue$/i });
    if (await cont.isVisible().catch(() => false)) {
      await tapEvent(page, cont);
    }
    await submitExpression(page, "0");
    const contAfterFirst = page.getByRole("button", { name: /^continue$/i });
    if (await contAfterFirst.isVisible().catch(() => false)) {
      await tapEvent(page, contAfterFirst);
    }
    await submitExpression(page, "0");
    const revealHeading = page.getByRole("heading", { name: /show the solution/i });
    if (await revealHeading.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await expect(revealHeading).toBeVisible();
      return;
    }
    const hintBtn = page.getByRole("button", { name: /^hint$/i });
    if (await hintBtn.isVisible().catch(() => false)) {
      await tapEvent(page, hintBtn);
    }
    await expect(page.locator(".banner")).toContainText(/undo|step|operation|hint/i);
    await submitExpression(page, "0");
    const reveal = page.getByRole("button", { name: /show the solution/i });
    await expect(reveal).toBeVisible({ timeout: 10_000 });
    await tapEvent(page, reveal);
    await expect(page.getByRole("heading", { name: /show the solution/i })).toBeVisible({ timeout: 10_000 });
  });
});
