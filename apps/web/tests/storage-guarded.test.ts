import { afterEach, describe, expect, it, vi } from "vitest";
import { dismissTip, loadSetup, saveSetup, tipDismissed } from "../lib/chat/device";
import { ensureDevStudent } from "../lib/dev-auth";
import { safeStorage } from "../lib/api";

function breakStorage(kind: "localStorage" | "sessionStorage") {
  vi.spyOn(window, kind, "get").mockImplementation(() => {
    throw new DOMException("denied", "SecurityError");
  });
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
});

describe("device setup storage uses the shared safe store", () => {
  it("round-trips on a normal browser", () => {
    saveSetup({ grade: 9, board: "b", subject: "math" });
    expect(loadSetup()).toEqual({ grade: 9, board: "b", subject: "math" });
    dismissTip();
    expect(tipDismissed()).toBe(true);
    expect(safeStorage()).toBe(window.localStorage);
  });

  it("does not throw and still works (in memory) when both stores are blocked", () => {
    breakStorage("localStorage");
    breakStorage("sessionStorage");
    expect(() => saveSetup({ grade: 7 })).not.toThrow();
    expect(loadSetup()).toEqual({ grade: 7 });
    expect(() => dismissTip()).not.toThrow();
    expect(tipDismissed()).toBe(true);
  });
});

describe("dev login storage", () => {
  it("does not throw when browser storage is blocked", async () => {
    breakStorage("localStorage");
    breakStorage("sessionStorage");
    vi.stubEnv("NEXT_PUBLIC_SKIP_LOGIN", "true");
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("offline"));
    await expect(ensureDevStudent()).rejects.toThrow("offline"); // fails on the network, not on storage
  });
});
