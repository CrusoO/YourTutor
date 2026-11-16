import { describe, expect, it } from "vitest";
import { answerSetFor } from "@/lib/doubt/leak";
import { detectPushback, finalReply, resolvePushback } from "@/lib/doubt/pushback";
import { solved } from "./helpers";

describe("detectPushback", () => {
  it("recognises pushback and pulls out the claimed value", () => {
    expect(detectPushback("that's wrong, my book says 3")).toEqual({ pushback: true, claim: "3" });
    expect(detectPushback("teacher said x = 4")).toEqual({ pushback: true, claim: "4" });
    expect(detectPushback("galat hai, answer is 5")).toEqual({ pushback: true, claim: "5" });
    expect(detectPushback("you are wrong").claim).toBeNull();
  });
  it("ignores ordinary text", () => {
    expect(detectPushback("2x + 3 = 7")).toEqual({ pushback: false, claim: null });
    expect(detectPushback("hello there")).toEqual({ pushback: false, claim: null });
  });
});

describe("resolvePushback (deterministic substitution)", () => {
  it("a wrong claim contradicts the key and is shown with the exact substitution", () => {
    const { c, s } = solved("2x + 3 = 7");
    const r = resolvePushback(c, s, "3");
    expect(r.verdict).toBe("claim_fails");
    expect(r.contradictsKey).toBe(true);
    expect(r.text).toContain("left side is 9");
    expect(r.text).toContain("right side is 7");
  });
  it("a right claim is confirmed by substitution, not argued", () => {
    const { c, s } = solved("2x + 3 = 7");
    const r = resolvePushback(c, s, "2");
    expect(r.verdict).toBe("claim_works");
    expect(r.contradictsKey).toBe(false);
  });
  it("a second root the student found is also confirmed", () => {
    const { c, s } = solved("x^2 - 5x + 6 = 0");
    expect(resolvePushback(c, s, "3").verdict).toBe("claim_works");
  });
  it("is unreadable without a claim", () => {
    const { c, s } = solved("2x + 3 = 7");
    expect(resolvePushback(c, s, null).verdict).toBe("unreadable");
  });
});

describe("a contradicts_key result outranks any chat reply", () => {
  const { c, s } = solved("2x + 3 = 7");
  const answers = answerSetFor(c, s);
  it("keeps the deterministic text when the claim fails, whatever the model says", () => {
    const det = resolvePushback(c, s, "3");
    const out = finalReply(det, "You are right, x = 3 is correct!", answers);
    expect(out.source).toBe("deterministic");
    expect(out.text).toBe(det.text);
  });
  it("replaces a model reply that states a wrong value", () => {
    const det = resolvePushback(c, s, "2");
    const out = finalReply(det, "Sure, so x = 5.", answers);
    expect(out.source).toBe("deterministic");
  });
  it("lets a harmless chat reply through", () => {
    const det = resolvePushback(c, s, "2");
    const out = finalReply(det, "Good checking! Putting it back is a great habit.", answers);
    expect(out.source).toBe("chat");
  });
});
