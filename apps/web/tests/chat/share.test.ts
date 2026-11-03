import { describe, expect, it, vi } from "vitest";
import { MAX_TOPIC_CHARS, lessonLink, shareLesson, topicFromSearch } from "@/lib/chat/share";

describe("topicFromSearch", () => {
  it("reads the question from the address, tidying the spaces", () => {
    expect(topicFromSearch("?topic=what%20is%20quantum%20tunnelling%3F")).toBe("what is quantum tunnelling?");
    expect(topicFromSearch("?topic=  a   b  ")).toBe("a b");
    expect(topicFromSearch("?x=1&topic=slope")).toBe("slope");
  });

  it("returns null when there is nothing worth starting a lesson on", () => {
    for (const search of ["", "?", "?topic=", "?topic=%20%20", "?topic=a", "?other=1"]) {
      expect(topicFromSearch(search), search).toBeNull();
    }
  });

  it("never returns more than the cap", () => {
    expect(topicFromSearch("?topic=" + "x".repeat(2000))!.length).toBe(MAX_TOPIC_CHARS);
  });

  it("reads a question that looks like markup as plain text, unchanged", () => {
    expect(topicFromSearch("?topic=" + encodeURIComponent("<script>alert(1)</script>"))).toBe("<script>alert(1)</script>");
  });
});

describe("lessonLink", () => {
  it("builds an address that round-trips the question and carries nothing else", () => {
    const link = lessonLink("https://brownie.example", "why is the sky blue? (class 8)");
    const url = new URL(link);
    expect(url.origin + url.pathname).toBe("https://brownie.example/brownie-chat");
    expect([...url.searchParams.keys()]).toEqual(["topic"]);
    expect(topicFromSearch(url.search)).toBe("why is the sky blue? (class 8)");
  });

  it("caps a long question so the link stays short", () => {
    const link = lessonLink("https://x.test", "y".repeat(5000));
    expect(topicFromSearch(new URL(link).search)!.length).toBe(MAX_TOPIC_CHARS);
  });
});

describe("shareLesson", () => {
  const origin = "https://brownie.example";

  it("uses the device share sheet when there is one, with the link", async () => {
    const share = vi.fn().mockResolvedValue(undefined);
    const writeText = vi.fn();
    expect(await shareLesson("slope", "A lesson on slope", { origin, share, writeText })).toBe("shared");
    expect(share).toHaveBeenCalledWith({ title: "A lesson on slope", text: "A lesson on slope", url: lessonLink(origin, "slope") });
    expect(writeText).not.toHaveBeenCalled();
  });

  it("treats backing out of the share sheet as nothing, not as a failure", async () => {
    const share = vi.fn().mockRejectedValue(new DOMException("closed", "AbortError"));
    const writeText = vi.fn();
    expect(await shareLesson("slope", "t", { origin, share, writeText })).toBe("cancelled");
    expect(writeText).not.toHaveBeenCalled();
  });

  it("copies the link when there is no share sheet, or when it breaks", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    expect(await shareLesson("slope", "t", { origin, writeText })).toBe("copied");
    expect(writeText).toHaveBeenCalledWith(lessonLink(origin, "slope"));

    const broken = vi.fn().mockRejectedValue(new Error("not allowed"));
    const again = vi.fn().mockResolvedValue(undefined);
    expect(await shareLesson("slope", "t", { origin, share: broken, writeText: again })).toBe("copied");
  });

  it("says it failed when it can neither share nor copy", async () => {
    expect(await shareLesson("slope", "t", { origin })).toBe("failed");
    expect(await shareLesson("slope", "t", { origin, writeText: vi.fn().mockRejectedValue(new Error("no")) })).toBe("failed");
  });
});
