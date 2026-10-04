import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

async function dismissNudge(page: Page) {
  const nudge = page.getByRole("button", { name: /still there/i });
  if (await nudge.isVisible().catch(() => false)) {
    await nudge.click({ force: true });
  }
}

async function submitWrong(page: Page, response: string) {
  await dismissNudge(page);
  const input = page.getByPlaceholder(/type your answer/i);
  if (await input.isVisible().catch(() => false)) {
    await input.fill(response);
    await tapEvent(page, page.getByRole("button", { name: /check/i }));
    return;
  }
  await tapEvent(page, page.locator("main button.secondary").first());
}

async function tapEvent(page: Page, locator: ReturnType<Page["getByRole"]>) {
  await dismissNudge(page);
  await locator.waitFor({ state: "visible", timeout: 20_000 });
  await Promise.all([
    page.waitForResponse((res) => res.url().includes("/events") && res.ok(), { timeout: 20_000 }),
    locator.click({ force: true }),
  ]);
}

async function authToken(page: Page): Promise<string> {
  const token = await page.evaluate(() => localStorage.getItem("yt_token"));
  expect(token).toBeTruthy();
  return token as string;
}

async function sessionIdFromUrl(page: Page): Promise<string> {
  const match = page.url().match(/\/session\/([^/?#]+)/);
  expect(match?.[1]).toBeTruthy();
  return match![1];
}

async function drainSession(
  request: APIRequestContext,
  token: string,
  sessionId: string,
  response: string,
) {
  const headers = { Authorization: `Bearer ${token}` };
  for (let i = 0; i < 48; i += 1) {
    const view = await request.get(`${API}/sessions/${sessionId}`, { headers });
    expect(view.ok()).toBeTruthy();
    const body = await view.json();
    const action = body.action;
    if (action.type === "end_session" || action.type === "checkpoint_score") {
      return body;
    }
    const eventType = action.type === "predict" ? "predict_response" : action.type === "nudge" ? "continue" : "answer";
    const payload =
      eventType === "predict_response"
        ? { response: "yes" }
        : eventType === "continue"
          ? {}
          : { response };
    const posted = await request.post(`${API}/sessions/${sessionId}/events`, {
      headers,
      data: {
        client_event_id: crypto.randomUUID(),
        event_type: eventType === "answer" && (action.type === "worked_example" || action.type === "feedback" || action.type === "reveal_solution" || action.type === "explain_back_result")
          ? "continue"
          : eventType,
        item_id: action.item_id || null,
        payload:
          action.type === "worked_example" || action.type === "feedback" || action.type === "reveal_solution" || action.type === "explain_back_result"
            ? {}
            : payload,
      },
    });
    expect(posted.ok()).toBeTruthy();
  }
  throw new Error(`session ${sessionId} did not end`);
}

test("diagnostic, practice with hint, then checkpoint", async ({ page, request }) => {
  test.setTimeout(180_000);
  const enrol = await request.post(`${API}/admin/pilot/enrol`, {
    headers: { "X-Pilot-Key": process.env.NEXT_PUBLIC_PILOT_KEY || "dev-pilot" },
    data: {
      first_name: "Smoke",
      grade: 9,
      board: "bhutan",
      paper_ref: "e2e-paper",
      scopes: ["tutoring", "research_pseudonymised"],
    },
  });
  expect(enrol.ok()).toBeTruthy();
  const card = await enrol.json();

  await page.goto("/login");
  await page.getByLabel(/family code/i).fill(card.family_code);
  await page.getByLabel(/^pin$/i).fill(card.pin);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.getByRole("heading", { name: /today/i })).toBeVisible();

  await page.getByRole("button", { name: /start diagnostic/i }).click();
  await expect(page).toHaveURL(/\/session\//);
  await expect(page.getByRole("button", { name: /i don't know/i })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByRole("button", { name: /^hint$/i })).toHaveCount(0);

  const token = await authToken(page);
  await drainSession(request, token, await sessionIdFromUrl(page), "i don't know");
  await page.goto("/today");
  await expect(page.getByRole("heading", { name: /today/i })).toBeVisible();

  await page.getByRole("button", { name: /start practice/i }).click();
  await expect(page).toHaveURL(/\/session\//);
  await expect(page.getByText(/practice/i).first()).toBeVisible();

  const yes = page.getByRole("button", { name: /^yes$/i });
  if (await yes.isVisible({ timeout: 8_000 }).catch(() => false)) {
    await tapEvent(page, yes);
  }

  for (let i = 0; i < 12; i += 1) {
    await dismissNudge(page);
    if (await page.getByPlaceholder(/type your answer/i).isVisible().catch(() => false)) {
      break;
    }
    if (await page.locator("main .stem").isVisible().catch(() => false) && await page.locator("main button.secondary").first().isVisible().catch(() => false)) {
      break;
    }
    const next = page.getByRole("button", { name: /show next step/i });
    if (await next.isVisible().catch(() => false)) {
      await next.click({ force: true });
      continue;
    }
    const cont = page.getByRole("button", { name: /^continue$/i });
    if (await cont.isVisible().catch(() => false)) {
      await tapEvent(page, cont);
    }
  }

  await submitWrong(page, "0");
  await expect(page.locator(".banner")).toBeVisible({ timeout: 10_000 });
  await submitWrong(page, "1");

  const reveal = page.getByRole("button", { name: /show the solution/i });
  await expect(reveal).toBeVisible({ timeout: 10_000 });
  await tapEvent(page, reveal);
  await expect(page.getByRole("heading", { name: /show the solution/i })).toBeVisible({ timeout: 10_000 });

  await page.goto("/today");
  await page.getByRole("button", { name: /start checkpoint/i }).click();
  await expect(page).toHaveURL(/\/session\//);
  await expect(page.getByRole("button", { name: /^hint$/i })).toHaveCount(0);
  await drainSession(request, token, await sessionIdFromUrl(page), "1");
  await page.reload();
  await expect(page.getByRole("heading", { name: /done for now/i })).toBeVisible({ timeout: 20_000 });
});
