import { describe, expect, it } from "vitest";
import { greeting, greetingPart } from "@/lib/chat/greeting";
import { t } from "@/lib/messages";

const copy = t("en");

describe("greeting", () => {
  it("picks the part of the day from the visitor's own hour", () => {
    expect(greetingPart(5)).toBe("chatGreetMorning");
    expect(greetingPart(11)).toBe("chatGreetMorning");
    expect(greetingPart(12)).toBe("chatGreetAfternoon");
    expect(greetingPart(16)).toBe("chatGreetAfternoon");
    expect(greetingPart(17)).toBe("chatGreetEvening");
    expect(greetingPart(21)).toBe("chatGreetEvening");
    expect(greetingPart(22)).toBe("chatGreetNight");
    expect(greetingPart(3)).toBe("chatGreetNight");
  });

  it("names a known student", () => {
    expect(greeting(copy, 9, "Mina")).toBe("Good morning, Mina");
  });

  it("gives guests and unknown visitors a friendly generic line", () => {
    expect(greeting(copy, 9)).toBe(copy.chatGreetGuest);
    expect(greeting(copy, 9, "  ")).toBe(copy.chatGreetGuest);
  });

  it("greets a signed-in adult with no nickname by time of day only", () => {
    expect(greeting(copy, 14, undefined, true)).toBe("Good afternoon");
  });
});
