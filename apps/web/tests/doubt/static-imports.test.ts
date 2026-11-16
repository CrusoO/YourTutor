import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const DIR = join(process.cwd(), "lib", "doubt");
const files = readdirSync(DIR).filter((f) => f.endsWith(".ts"));

describe("lib/doubt imports nothing that can reach the network", () => {
  it("has the files the design names", () => {
    for (const f of ["frac", "poly", "parse", "detect", "rules", "types", "solve", "steps", "ladder", "leak", "attempt", "guard", "pushback", "copy.en"]) {
      expect(files).toContain(`${f}.ts`);
    }
  });
  it("only imports its own siblings", () => {
    for (const f of files) {
      const src = readFileSync(join(DIR, f), "utf8");
      for (const m of src.matchAll(/(?:from|import)\s*\(?\s*["']([^"']+)["']/g)) {
        expect(m[1], `${f} imports ${m[1]}`).toMatch(/^\.\/[a-z.]+$/);
      }
      expect(src, f).not.toMatch(/\bimport\s*\(/);
      expect(src, f).not.toMatch(/\brequire\s*\(/);
    }
  });
  it("never imports lib/api, config, auth or any network module", () => {
    for (const f of files) {
      const src = readFileSync(join(DIR, f), "utf8");
      expect(src, f).not.toMatch(/lib\/api|\/api["']|agreements-api|useStudent|dev-auth|next\/|axios|\bky["']/);
    }
  });
  it("never mentions a network, storage, logging or dynamic-code API", () => {
    const forbidden = /\b(fetch|XMLHttpRequest|sendBeacon|WebSocket|EventSource|localStorage|sessionStorage|indexedDB|document\.cookie|navigator\.|console\.|process\.env|eval\s*\(|new Function|Function\s*\()/;
    for (const f of files) {
      const code = readFileSync(join(DIR, f), "utf8")
        .replace(/\/\*[\s\S]*?\*\//g, "")
        .replace(/^\s*\/\/.*$/gm, "");
      expect(code, f).not.toMatch(forbidden);
    }
  });
  it("never uses the label reserved for kernel-verified results", () => {
    for (const f of files) {
      expect(readFileSync(join(DIR, f), "utf8"), f).not.toMatch(/checked by code/i);
    }
  });
  it("the on-device label is the honest one", async () => {
    const { LABEL_DEVICE } = await import("@/lib/doubt/copy.en");
    expect(LABEL_DEVICE).toBe("Worked out on your device");
  });
});
