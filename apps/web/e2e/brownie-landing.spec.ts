import { expect, test } from "@playwright/test";

test("the homepage presents the landing page and keeps the video picker after Chapter Two", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  await expect(page.getByTestId("brownie-landing")).toBeVisible();
  await expect(page.getByText("Don't understand something? You don't have to pretend you do.", { exact: false })).toBeVisible();
  await expect(page.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/login?lang=en");
  await expect(page.getByRole("link", { name: "Try asking Brownie" })).toHaveAttribute("href", "/brownie-chat");

  const heroWordmark = await page.getByTestId("landing-wordmark").boundingBox();
  const heroCopy = await page.getByTestId("landing-hero-copy").boundingBox();
  expect(heroWordmark).not.toBeNull();
  expect(heroCopy).not.toBeNull();
  expect(heroCopy!.x).toBeGreaterThan(heroWordmark!.x + heroWordmark!.width * 0.45);

  const videoFollowsChapterTwo = await page.locator("#chapter-two").evaluate((chapter) =>
    chapter.nextElementSibling?.id === "demo",
  );
  expect(videoFollowsChapterTwo).toBe(true);
  await expect(page.locator(".closing")).toHaveCount(0);
  await expect(page.getByText("Ask the question you were scared to ask.", { exact: false })).toHaveCount(0);

  const audience = page.getByTestId("audience-words");
  await expect(audience).toContainText("Students");
  await expect(audience).toContainText("Teachers");
  await expect(audience).toContainText("Professionals");
  await expect(audience).toContainText("Everyone");
  const firstAudienceIndex = await audience.getAttribute("data-active-index");
  await expect.poll(() => audience.getAttribute("data-active-index")).not.toBe(firstAudienceIndex);
});

test("Hindi and Nepali translate the complete landing, interactions, and sign-in form", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: "हिन्दी" }).click();
  await expect(page.getByTestId("brownie-landing")).toHaveAttribute("lang", "hi");
  await expect(page.getByTestId("landing-hero-copy").getByText("पहले समझता है। फिर सिखाता है।")).toBeVisible();
  await expect(page.getByText("अध्याय दो")).toBeVisible();
  await expect(page.getByText("वीडियो चुनें")).toBeVisible();
  await expect(page.getByPlaceholder("अभी सीखने में क्या मुश्किल है? किससे बात समझ आएगी?")).toBeVisible();
  await page.getByRole("link", { name: "साइन इन करें" }).click();
  await expect(page.getByRole("heading", { name: "Brownie में साइन इन करें" })).toBeVisible();
  await expect(page.getByLabel("परिवार कोड")).toBeVisible();
  await page.getByRole("button", { name: "English" }).click();
  await expect(page.getByRole("heading", { name: "Sign in to Brownie" })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Sign in to Brownie" })).toBeVisible();

  await page.goto("/");
  await page.getByRole("button", { name: "नेपाली" }).click();
  await expect(page.getByTestId("brownie-landing")).toHaveAttribute("lang", "ne");
  await expect(page.getByTestId("landing-hero-copy").getByText("पहिले बुझ्छ। त्यसपछि सिकाउँछ।")).toBeVisible();
  await expect(page.getByText("अध्याय दुई")).toBeVisible();
  await expect(page.getByText("भिडियो छान्नुहोस्")).toBeVisible();
  await expect(page.getByPlaceholder("अहिले सिक्न के गाह्रो छ? के गर्दा कुरा बुझिन्छ?")).toBeVisible();
  await page.getByRole("link", { name: "साइन इन गर्नुहोस्" }).click();
  await expect(page.getByRole("heading", { name: "Brownie मा साइन इन गर्नुहोस्" })).toBeVisible();
  await expect(page.getByLabel("परिवार कोड")).toBeVisible();

  await page.goto("/");
  await page.getByRole("button", { name: "English" }).click();
  await expect(page.getByTestId("brownie-landing")).toHaveAttribute("lang", "en");
  await expect(page.getByRole("heading", { name: /Brownie is for/ })).toBeVisible();
});

test("the chat stays available at /brownie-chat and has a direct homepage link", async ({ page }) => {
  await page.goto("/brownie-chat", { waitUntil: "domcontentloaded" });
  await expect(page.getByTestId("app-shell")).toBeVisible();
  await expect(page.getByTestId("back-home")).toHaveAttribute("href", "/");
  await expect(page.getByTestId("back-home")).toHaveAccessibleName("Back to the Brownie homepage");
});

test("the translated landing fits a mobile viewport without horizontal overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "नेपाली" }).click();

  const dimensions = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    document: document.documentElement.scrollWidth,
  }));
  expect(dimensions.document).toBeLessThanOrEqual(dimensions.viewport);
});
