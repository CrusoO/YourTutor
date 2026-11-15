import { afterEach, describe, expect, it, vi } from "vitest";

async function extensions(env: Record<string, string>) {
  vi.resetModules();
  for (const [k, v] of Object.entries(env)) vi.stubEnv(k, v);
  const mod = await import("../../next.config");
  return (mod.default.pageExtensions ?? []) as string[];
}

describe("the /dev preview pages (page.dev.tsx) are routes only when dev tools are on", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("a production build without the flag does not include them", async () => {
    expect(await extensions({ NODE_ENV: "production", NEXT_PUBLIC_DEV_TOOLS: "false" })).not.toContain("dev.tsx");
  });
  it("a production build with NEXT_PUBLIC_DEV_TOOLS=true includes them", async () => {
    expect(await extensions({ NODE_ENV: "production", NEXT_PUBLIC_DEV_TOOLS: "true" })).toContain("dev.tsx");
  });
  it("next dev (not a production build) includes them, so local preview tooling keeps working", async () => {
    expect(await extensions({ NODE_ENV: "development", NEXT_PUBLIC_DEV_TOOLS: "false" })).toContain("dev.tsx");
  });
});
