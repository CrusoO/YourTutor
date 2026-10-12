import { afterEach, describe, expect, it } from "vitest";
import { applyComfort, COMFORT_INIT_SCRIPT, COMFORT_KEY, DEFAULT_COMFORT, parseComfort, readComfort, saveComfort } from "../../lib/comfort";

afterEach(() => {
  window.localStorage.clear();
  for (const a of ["data-theme", "data-text", "data-spacing", "data-motion"]) document.documentElement.removeAttribute(a);
});

describe("comfort settings", () => {
  it("defaults to Auto theme, medium text, normal spacing and device motion", () => {
    expect(parseComfort(null)).toEqual(DEFAULT_COMFORT);
    expect(DEFAULT_COMFORT.theme).toBe("auto");
  });

  it("ignores damaged or unknown stored values field by field", () => {
    expect(parseComfort("{not json")).toEqual(DEFAULT_COMFORT);
    expect(parseComfort(JSON.stringify({ theme: "purple", text: "l", spacing: 3 }))).toEqual({ ...DEFAULT_COMFORT, text: "l" });
  });

  it("applies and clears the data attributes without a reload", () => {
    applyComfort({ theme: "dark", text: "l", spacing: "relaxed", motion: "reduce" });
    const root = document.documentElement;
    expect([root.dataset.theme, root.dataset.text, root.dataset.spacing, root.dataset.motion]).toEqual(["dark", "l", "relaxed", "reduce"]);
    applyComfort(DEFAULT_COMFORT);
    expect(root.hasAttribute("data-theme")).toBe(false);
    expect(root.hasAttribute("data-text")).toBe(false);
  });

  it("persists on the device and reads back", () => {
    saveComfort({ theme: "light", text: "s", spacing: "normal", motion: "auto" });
    expect(readComfort()).toEqual({ theme: "light", text: "s", spacing: "normal", motion: "auto" });
  });

  it("the pre-paint script sets the saved values on <html> and survives bad storage", () => {
    window.localStorage.setItem(COMFORT_KEY, JSON.stringify({ theme: "dark", text: "l", spacing: "relaxed", motion: "reduce" }));
    new Function(COMFORT_INIT_SCRIPT)();
    const root = document.documentElement;
    expect([root.dataset.theme, root.dataset.text, root.dataset.spacing, root.dataset.motion]).toEqual(["dark", "l", "relaxed", "reduce"]);
    window.localStorage.setItem(COMFORT_KEY, "{broken");
    expect(() => new Function(COMFORT_INIT_SCRIPT)()).not.toThrow();
  });
});
