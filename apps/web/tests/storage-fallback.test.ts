import { afterEach, describe, expect, it, vi } from "vitest";
import { clearStudent, hasStudentToken, isEmailUnavailable, apiError, setToken, storageMode } from "../lib/api";

function breakStorage(kind: "localStorage" | "sessionStorage") {
  vi.spyOn(window, kind, "get").mockImplementation(() => {
    throw new DOMException("denied", "SecurityError");
  });
}

describe("safeStorage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    clearStudent();
  });

  it("uses the device store when it works", () => {
    expect(storageMode()).toBe("device");
  });

  it("falls back to sessionStorage when localStorage throws", () => {
    breakStorage("localStorage");
    expect(storageMode()).toBe("tab");
    setToken("abc");
    expect(hasStudentToken()).toBe(true);
  });

  it("falls back to memory when both throw, and never throws", () => {
    breakStorage("localStorage");
    breakStorage("sessionStorage");
    expect(storageMode()).toBe("memory");
    expect(() => setToken("abc")).not.toThrow();
    expect(hasStudentToken()).toBe(true);
    expect(() => clearStudent()).not.toThrow();
    expect(hasStudentToken()).toBe(false);
  });

  it("falls back when writes throw (quota or Safari private mode)", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("full", "QuotaExceededError");
    });
    expect(storageMode()).toBe("memory");
    expect(() => setToken("abc")).not.toThrow();
    expect(hasStudentToken()).toBe(true);
  });
});

describe("email_unavailable", () => {
  it("is recognised from the API's 503 body", async () => {
    const body = JSON.stringify({ detail: { code: "email_unavailable", message: "x" } });
    const error = await apiError(new Response(body, { status: 503 }));
    expect(isEmailUnavailable(error)).toBe(true);
    expect(isEmailUnavailable(await apiError(new Response("nope", { status: 500 })))).toBe(false);
  });
});
