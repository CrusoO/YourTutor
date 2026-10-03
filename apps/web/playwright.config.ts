import { defineConfig } from "@playwright/test";

const webPort = process.env.PLAYWRIGHT_WEB_PORT || "3001";

export default defineConfig({
  testDir: "./e2e",
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
          NEXT_PUBLIC_IDLE_NUDGE_MS: process.env.NEXT_PUBLIC_IDLE_NUDGE_MS || "2500",
          NEXT_PUBLIC_HINT_DELAY_MS: process.env.NEXT_PUBLIC_HINT_DELAY_MS || "60000",
        },
      },
});
