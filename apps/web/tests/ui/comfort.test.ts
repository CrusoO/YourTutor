import { afterEach, describe, expect, it } from "vitest";
import { applyComfort, COMFORT_INIT_SCRIPT, COMFORT_KEY, DEFAULT_COMFORT, deviceWantsReducedEffects, parseComfort, readComfort, resetComfortStore, saveComfort, updateComfort } from "../../lib/comfort";

afterEach(() => {
  resetComfortStore();
  window.localStorage.clear();
  document.head.querySelectorAll('link[rel="preload"]').forEach((l) => l.remove());
  document.documentElement.lang = "";
  for (const a of ["data-theme", "data-text", "data-spacing", "data-motion", "data-paper", "data-effects"]) document.documentElement.removeAttribute(a);
});

describe("comfort settings", () => {
  it("defaults to Auto theme, medium text, normal spacing, device motion and plain board paper", () => {
    expect(parseComfort(null)).toEqual(DEFAULT_COMFORT);
    expect(DEFAULT_COMFORT.theme).toBe("auto");
    expect(DEFAULT_COMFORT.paper).toBe("plain");
  });

  it("ignores damaged or unknown stored values field by field", () => {
    expect(parseComfort("{not json")).toEqual(DEFAULT_COMFORT);
    expect(parseComfort(JSON.stringify({ theme: "purple", text: "l", spacing: 3 }))).toEqual({ ...DEFAULT_COMFORT, text: "l" });
  });

  it("applies and clears the data attributes without a reload", () => {
    applyComfort({ theme: "dark", text: "l", spacing: "relaxed", motion: "reduce", paper: "grid", effects: "auto" });
    const root = document.documentElement;
    expect([root.dataset.theme, root.dataset.text, root.dataset.spacing, root.dataset.motion, root.dataset.paper]).toEqual(["dark", "l", "relaxed", "reduce", "grid"]);
    applyComfort(DEFAULT_COMFORT);
    expect(root.hasAttribute("data-theme")).toBe(false);
    expect(root.hasAttribute("data-text")).toBe(false);
    expect(root.hasAttribute("data-paper")).toBe(false);
  });

  it("persists on the device and reads back", () => {
    saveComfort({ theme: "light", text: "s", spacing: "normal", motion: "auto", paper: "grid", effects: "reduce" });
    expect(readComfort()).toEqual({ theme: "light", text: "s", spacing: "normal", motion: "auto", paper: "grid", effects: "reduce" });
  });

  it("the pre-paint script sets the saved values on <html> and survives bad storage", () => {
    window.localStorage.setItem(COMFORT_KEY, JSON.stringify({ theme: "dark", text: "l", spacing: "relaxed", motion: "reduce", paper: "grid", effects: "auto" }));
    new Function(COMFORT_INIT_SCRIPT)();
    const root = document.documentElement;
    expect([root.dataset.theme, root.dataset.text, root.dataset.spacing, root.dataset.motion, root.dataset.paper]).toEqual(["dark", "l", "relaxed", "reduce", "grid"]);
    window.localStorage.setItem(COMFORT_KEY, "{broken");
    expect(() => new Function(COMFORT_INIT_SCRIPT)()).not.toThrow();
  });

  it("Reduce effects is on when chosen and on its own for data-saver or very low memory hints", () => {
    applyComfort({ ...DEFAULT_COMFORT, effects: "reduce" });
    expect(document.documentElement.dataset.effects).toBe("reduce");
    applyComfort(DEFAULT_COMFORT);
    expect(document.documentElement.hasAttribute("data-effects")).toBe(false);
    expect(deviceWantsReducedEffects({ connection: { saveData: true } })).toBe(true);
    expect(deviceWantsReducedEffects({ deviceMemory: 1 })).toBe(true);
    expect(deviceWantsReducedEffects({ deviceMemory: 8, connection: { saveData: false } })).toBe(false);
    expect(deviceWantsReducedEffects(undefined)).toBe(false);
  });

  it("the pre-paint script sets the document language and preloads Latin fonts only for English", () => {
    window.localStorage.setItem("yt_locale", "hi");
    new Function(COMFORT_INIT_SCRIPT)();
    expect(document.documentElement.lang).toBe("hi");
    expect(document.head.querySelectorAll('link[rel="preload"]').length).toBe(0);
    window.localStorage.setItem("yt_locale", "en");
    new Function(COMFORT_INIT_SCRIPT)();
    expect(document.head.querySelectorAll('link[rel="preload"][as="font"]').length).toBe(3);
    document.head.querySelectorAll('link[rel="preload"]').forEach((l) => l.remove());
    document.documentElement.lang = "";
  });

  it("changing one setting never undoes another (the Settings dialog bug)", () => {
    updateComfort({ text: "l" });
    updateComfort({ spacing: "relaxed" });
    updateComfort({ theme: "dark" });
    expect(readComfort()).toEqual({ theme: "dark", text: "l", spacing: "relaxed", motion: "auto", paper: "plain", effects: "auto" });
    expect(document.documentElement.dataset.text).toBe("l");
  });
});
