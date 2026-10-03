import { expect, type APIRequestContext, type Page } from "@playwright/test";

export const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
export const PILOT_KEY = process.env.NEXT_PUBLIC_PILOT_KEY || "dev-pilot";

export async function dismissNudge(page: Page) {
  const nudge = page.getByRole("button", { name: /still there/i });
  if (await nudge.isVisible().catch(() => false)) {
    await nudge.click({ force: true });
  }
}

export async function tapEvent(page: Page, locator: ReturnType<Page["getByRole"]>) {
  await dismissNudge(page);
  await locator.waitFor({ state: "visible", timeout: 20_000 });
  await Promise.all([
    page.waitForResponse((res) => res.url().includes("/events") && res.ok(), { timeout: 20_000 }),
    locator.click({ force: true }),
  ]);
}

export async function enrolStudent(request: APIRequestContext, firstName = "E2E") {
  const enrol = await request.post(`${API}/admin/pilot/enrol`, {
    headers: { "X-Pilot-Key": PILOT_KEY },
    data: {
      first_name: firstName,
      grade: 9,
      board: "bhutan",
      paper_ref: "e2e-mini",
      scopes: ["tutoring", "research_pseudonymised"],
    },
  });
  expect(enrol.ok()).toBeTruthy();
  return enrol.json() as Promise<{ family_code: string; pin: string }>;
}

export async function loginStudent(page: Page, family_code: string, pin: string) {
  await page.goto("/login");
  await page.getByLabel(/family code/i).fill(family_code);
  await page.getByLabel(/^pin$/i).fill(pin);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.getByRole("heading", { name: /today/i })).toBeVisible();
}

export async function sessionIdFromUrl(page: Page): Promise<string> {
  const match = page.url().match(/\/session\/([^/?#]+)/);
  expect(match?.[1]).toBeTruthy();
  return match![1];
}

export async function answerDontKnow(page: Page) {
  await dismissNudge(page);
  const dk = page.getByRole("button", { name: /i don't know/i });
  await expect(dk).toBeVisible({ timeout: 15_000 });
  await tapEvent(page, dk);
}

export async function skipToExpressionItem(page: Page, maxSteps = 12) {
  for (let i = 0; i < maxSteps; i += 1) {
    await dismissNudge(page);
    if (await page.getByPlaceholder(/type your answer/i).isVisible().catch(() => false)) {
      return;
    }
    const yes = page.getByRole("button", { name: /^yes$/i });
    if (await yes.isVisible().catch(() => false)) {
      await tapEvent(page, yes);
      continue;
    }
    const next = page.getByRole("button", { name: /show next step/i });
    if (await next.isVisible().catch(() => false)) {
      await next.click({ force: true });
      continue;
    }
    const cont = page.getByRole("button", { name: /^continue$/i });
    if (await cont.isVisible().catch(() => false)) {
      await tapEvent(page, cont);
      continue;
    }
    await page.waitForTimeout(200);
  }
  await expect(page.getByPlaceholder(/type your answer/i)).toBeVisible({ timeout: 20_000 });
}

export async function submitExpression(page: Page, value: string) {
  await dismissNudge(page);
  const input = page.getByPlaceholder(/type your answer/i);
  await expect(input).toBeVisible({ timeout: 15_000 });
  await input.fill(value);
  await tapEvent(page, page.getByRole("button", { name: /check/i }));
}

export async function advanceUntilDone(page: Page, maxSteps = 40) {
  for (let i = 0; i < maxSteps; i += 1) {
    if (await page.getByRole("heading", { name: /done for now/i }).isVisible().catch(() => false)) {
      return;
    }
    await dismissNudge(page);
    const dk = page.getByRole("button", { name: /i don't know/i });
    if (await dk.isVisible().catch(() => false)) {
      await tapEvent(page, dk);
      continue;
    }
    const input = page.getByPlaceholder(/type your answer/i);
    if (await input.isVisible().catch(() => false)) {
      await submitExpression(page, "0");
      continue;
    }
    const yes = page.getByRole("button", { name: /^yes$/i });
    if (await yes.isVisible().catch(() => false)) {
      await tapEvent(page, yes);
      continue;
    }
    const next = page.getByRole("button", { name: /show next step/i });
    if (await next.isVisible().catch(() => false)) {
      await next.click({ force: true });
      continue;
    }
    const cont = page.getByRole("button", { name: /^continue$/i });
    if (await cont.isVisible().catch(() => false)) {
      await tapEvent(page, cont);
      continue;
    }
    const similar = page.getByRole("button", { name: /try a similar one/i });
    if (await similar.isVisible().catch(() => false)) {
      await tapEvent(page, similar);
      continue;
    }
    await page.waitForTimeout(300);
  }
  await expect(page.getByRole("heading", { name: /done for now/i })).toBeVisible({ timeout: 20_000 });
}
