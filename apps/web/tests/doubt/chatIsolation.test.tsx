import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import DoubtCard from "@/components/chat/doubt/DoubtCard";
import Keypad from "@/components/chat/doubt/Keypad";
import { readDoubt, readPushback } from "@/components/chat/doubt/pipeline";

/** Typing an equation through every ladder level and attempt makes no network, storage, beacon or console call. */
describe("the doubt card in the chat is isolated from the network, storage and logs", () => {
  const calls: string[] = [];
  const saved: Record<string, unknown> = {};
  const names = ["fetch", "XMLHttpRequest", "WebSocket", "EventSource", "indexedDB", "localStorage", "sessionStorage", "BroadcastChannel"];

  beforeEach(() => {
    calls.length = 0;
    for (const n of names) saved[n] = (globalThis as Record<string, unknown>)[n];
    const trap = (n: string) =>
      new Proxy(function () {}, {
        apply: () => {
          calls.push(n);
          throw new Error(`${n} called`);
        },
        construct: () => {
          calls.push(`new ${n}`);
          throw new Error(`new ${n}`);
        },
        get: (_t, p) => {
          calls.push(`${n}.${String(p)}`);
          throw new Error(`${n}.${String(p)}`);
        },
      });
    for (const n of names) Object.defineProperty(globalThis, n, { value: trap(n), configurable: true, writable: true });
    Object.defineProperty(globalThis.navigator, "sendBeacon", { value: () => calls.push("sendBeacon"), configurable: true });
    for (const m of ["log", "info", "warn", "error", "debug", "trace"] as const) vi.spyOn(console, m).mockImplementation(() => calls.push(`console.${m}`));
  });
  afterEach(() => {
    cleanup();
    for (const n of names) Object.defineProperty(globalThis, n, { value: saved[n], configurable: true, writable: true });
    vi.restoreAllMocks();
  });

  it("typing, confirming, every hint level, full steps, right and wrong answers, steps and pushback: zero calls", async () => {
    for (const text of ["2x + 3 = 11", "x^2 - 5x + 6 = 0", "x^2 + x - 1 = 0", "x + y = 5; x - y = 1", "2(3+4)*5", "sin x = 1/2"]) {
      const p = readDoubt(text);
      expect(p, text).not.toBeNull();
      readPushback(p!, "my book says x = 3");
      const view = render(<DoubtCard doubt={{ ...p!, pushback: readPushback(p!, "that is wrong, i got 3") ?? undefined }} onEdit={() => {}} onClose={() => {}} onExplain={() => {}} />);
      if (p!.outcome === "candidate") {
        await userEvent.click(screen.getByTestId("doubt-confirm"));
        while (screen.queryByTestId("hint-next")) await userEvent.click(screen.getByTestId("hint-next"));
        const steps = screen.queryByTestId("hint-steps");
        if (steps) await userEvent.click(steps);
        for (const attempt of ["x = 5", "x = 2", "3", "no solution", "rubbish"]) {
          const box = screen.getByTestId("doubt-tried-input");
          await userEvent.clear(box);
          await userEvent.type(box, attempt);
          await userEvent.click(screen.getByTestId("doubt-tried-check"));
        }
        const stepBtn = screen.queryByRole("button", { name: "My next step" });
        if (stepBtn) {
          await userEvent.click(stepBtn);
          for (const next of ["2x = 8", "x = 4", "2x = 9"]) {
            await userEvent.clear(screen.getByTestId("doubt-tried-input"));
            await userEvent.type(screen.getByTestId("doubt-tried-input"), next);
            await userEvent.click(screen.getByTestId("doubt-tried-check"));
          }
        }
      }
      view.unmount();
    }
    expect(calls).toEqual([]);
  }, 180_000);

  it("the keypad fills text without any call", async () => {
    const ref = { current: document.createElement("textarea") };
    document.body.appendChild(ref.current);
    render(<Keypad box={ref} onChange={() => {}} />);
    for (const b of screen.getAllByRole("button")) await userEvent.click(b);
    expect(screen.getAllByRole("button").length).toBeGreaterThan(20);
    expect(calls).toEqual([]);
  });

  it("the trap works (a fetch would be seen)", () => {
    expect(() => (globalThis as unknown as { fetch: () => void }).fetch()).toThrow();
    expect(calls).toContain("fetch");
  });
});

describe("the doubt chat code imports no network or storage module", () => {
  const dir = join(process.cwd(), "components/chat/doubt");
  const files = readdirSync(dir).filter((f) => /\.tsx?$/.test(f));

  it.each(files)("%s", (f) => {
    const src = readFileSync(join(dir, f), "utf8");
    expect(src).not.toMatch(/from\s+["']@\/lib\/(api|chat\/device|storage)/);
    expect(src).not.toMatch(/\b(fetch|XMLHttpRequest|sendBeacon|WebSocket|localStorage|sessionStorage|indexedDB|console)\b\s*[.(]/);
    expect(src).not.toMatch(/document\.cookie/);
  });

  it("the words reserved for server-verified results appear nowhere in the feature", () => {
    for (const f of files) expect(readFileSync(join(dir, f), "utf8"), f).not.toMatch(/checked by code/i);
    for (const f of ["../ChatProvider.tsx", "../Composer.tsx", "../Bubbles.tsx"]) expect(readFileSync(join(dir, f), "utf8"), f).not.toMatch(/checked by code/i);
  });

  it("every doubt component is loaded lazily from the chat files (no static import)", () => {
    for (const f of ["ChatProvider.tsx", "Composer.tsx", "Bubbles.tsx", "Thread.tsx"]) {
      const src = readFileSync(join(dir, "..", f), "utf8");
      expect(src, f).not.toMatch(/^import\s[^;]*from\s+["']\.\/doubt\/(?!types)/m);
      expect(src, f).not.toMatch(/^import\s[^;]*from\s+["']@\/lib\/doubt/m);
    }
  });
});
