import { afterEach, describe, expect, it, vi } from "vitest";
import hiFile from "../../locales/hi.json";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
  window.localStorage.clear();
  document.documentElement.lang = "";
});

async function load(showDraft: boolean) {
  vi.resetModules();
  if (showDraft) vi.stubEnv("NEXT_PUBLIC_SHOW_DRAFT_LOCALES", "true");
  const messages = await import("../../lib/messages");
  const locale = await import("../../lib/locale");
  return { ...messages, ...locale };
}

describe("launch languages: English and Hindi only", () => {
  it("only en and hi are live; the other registry locales are coming soon and cannot be selected", async () => {
    const { LIVE_LOCALES, isLiveLocale, setLocale, currentLocale } = await load(false);
    expect(LIVE_LOCALES).toEqual(["en", "hi"]);
    expect(isLiveLocale("ne")).toBe(false);
    setLocale("ne");
    setLocale("as");
    setLocale("bn");
    expect(currentLocale()).toBe("en");
    expect(window.localStorage.getItem("yt_locale")).toBeNull();
  });

  it("shows each live language in its own script", async () => {
    const { nativeName } = await load(false);
    expect(nativeName("en")).toBe("English");
    expect(nativeName("hi")).toBe("हिन्दी");
  });

  it("the choice is remembered on the device, applied to <html lang> and read back after a reload", async () => {
    const first = await load(false);
    first.setLocale("hi");
    expect(first.currentLocale()).toBe("hi");
    expect(document.documentElement.lang).toBe("hi");
    expect(window.localStorage.getItem("yt_locale")).toBe("hi");
    const reloaded = await load(false);
    expect(reloaded.currentLocale()).toBe("hi");
  });

  it("a damaged or unknown stored language falls back to English", async () => {
    window.localStorage.setItem("yt_locale", "klingon");
    const { currentLocale } = await load(false);
    expect(currentLocale()).toBe("en");
  });
});

describe("Hindi strings are shown only when reviewed", () => {
  it("the string file starts as a draft with no reviewer", () => {
    expect(hiFile.status).toBe("draft");
    expect(hiFile.reviewedBy).toBeNull();
  });

  it("an unreviewed Hindi file shows English for every string", async () => {
    const { t } = await load(false);
    expect(t("hi").chatSend).toBe(t("en").chatSend);
    expect(t("hi").chatSend).toBe("Send");
  });

  it("with drafts allowed (previews, tests) Hindi shows, and a missing key falls back to English string by string", async () => {
    const { t } = await load(true);
    expect(t("hi").chatSend).toBe("भेजें");
    const missing = Object.keys(t("en")).filter((key) => !(key in hiFile.strings));
    expect(missing.length).toBeGreaterThan(0);
    const key = missing[0] as keyof ReturnType<typeof t>;
    expect(t("hi")[key]).toBe(t("en")[key]);
  });

  it("every Hindi key exists in English and keeps its {placeholders}", async () => {
    const { t } = await load(true);
    const en = t("en") as unknown as Record<string, string>;
    for (const [key, value] of Object.entries(hiFile.strings)) {
      expect(en[key], `${key} is not an English key`).toBeTypeOf("string");
      const tokens = (text: string) => (text.match(/\{[a-z]+\}/g) ?? []).sort().join(",");
      expect(tokens(value), key).toBe(tokens(en[key]!));
    }
  });

  it("a locale that is coming soon shows English, not its draft strings", async () => {
    const { t } = await load(true);
    expect(t("ne").loginTitle).toBe("Student login");
    expect(t("as").loginTitle).toBe("Student login");
  });
});
