import { defineConfig } from "@playwright/test";

const webPort = process.env.PLAYWRIGHT_WEB_PORT || "3001";

export default defineConfig({
  testDir: "./e2e",
  // Screens go to test-results/screens/; keep artifacts apart so a new run does not wipe them.
  outputDir: "test-results/artifacts",
  timeout: 240_000,
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || `http://127.0.0.1:${webPort}`,
    viewport: { width: 360, height: 740 },
  },
  webServer: process.env.PLAYWRIGHT_NO_WEB
    ? undefined
    : {
        command: `npm run dev -- --port ${webPort}`,
        url: `http://127.0.0.1:${webPort}/api/health`,
        reuseExistingServer: process.env.PLAYWRIGHT_REUSE_SERVER === "true",
        timeout: 120_000,
        env: {
          ...process.env,
          NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000",
          NEXT_PUBLIC_DEV_TOOLS: process.env.NEXT_PUBLIC_DEV_TOOLS || "true",
          // Previews and tests show the draft Hindi strings; production shows Hindi only once locales/hi.json is reviewed.
          NEXT_PUBLIC_SHOW_DRAFT_LOCALES: process.env.NEXT_PUBLIC_SHOW_DRAFT_LOCALES || "true",
          NEXT_PUBLIC_IDLE_NUDGE_MS: process.env.NEXT_PUBLIC_IDLE_NUDGE_MS || "2500",
          NEXT_PUBLIC_HINT_DELAY_MS: process.env.NEXT_PUBLIC_HINT_DELAY_MS || "60000",
        },
      },
});
