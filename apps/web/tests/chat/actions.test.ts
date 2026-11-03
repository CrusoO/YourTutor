import { describe, expect, it } from "vitest";
import type { ActionDirective } from "@/lib/api";
import { planAction, SCREENS, stepFor } from "@/lib/chat/actions";

const live = (code: string) => code === "en" || code === "hi";

function action(over: Partial<Extract<ActionDirective, { kind: "action" }>> = {}): ActionDirective {
  return { kind: "action", name: "x", client: "start_practice", args: {}, risk: "safe", narration: "Okay.", ...over };
}

describe("stepFor", () => {
  it("maps each known verb to a step", () => {
    expect(stepFor("start_practice", {}, live)).toEqual({ verb: "start_practice" });
    expect(stepFor("new_chat", {}, live)).toEqual({ verb: "new_chat" });
    expect(stepFor("open_screen", { screen: "today" }, live)).toEqual({ verb: "open_screen", path: "/today" });
    expect(stepFor("set_language", { language: "hi" }, live)).toEqual({ verb: "set_language", code: "hi" });
  });

  it("never uses a path from the server, only a known screen key", () => {
    expect(stepFor("open_screen", { screen: "/admin" }, live)).toBeNull();
    expect(stepFor("open_screen", { screen: "https://evil.example" }, live)).toBeNull();
    expect(stepFor("open_screen", { path: "/admin" }, live)).toBeNull();
    expect(Object.values(SCREENS).every((p) => p.startsWith("/") && !p.startsWith("//"))).toBe(true);
  });

  it("refuses a language that is not live, and any verb it does not know", () => {
    expect(stepFor("set_language", { language: "fr" }, live)).toBeNull();
    expect(stepFor("set_language", {}, live)).toBeNull();
    expect(stepFor("delete_account", {}, live)).toBeNull();
    expect(stepFor("none", {}, live)).toBeNull();
  });
});

describe("planAction", () => {
  it("does nothing for no action", () => {
    expect(planAction({ kind: "none" }, live)).toEqual({ kind: "ignore" });
  });

  it("runs a safe action and shows its narration", () => {
    expect(planAction(action(), live)).toEqual({ kind: "run", text: "Okay.", step: { verb: "start_practice" } });
  });

  it("shows narration only for a narration-only action", () => {
    expect(planAction(action({ client: "none", narration: "Sign in from the menu." }), live)).toEqual({
      kind: "run",
      text: "Sign in from the menu.",
      step: null,
    });
  });

  it("says why when the server denied it", () => {
    expect(planAction({ kind: "denied", name: "sign_in_prompt", narration: "You are already signed in." }, live)).toEqual({
      kind: "say",
      text: "You are already signed in.",
    });
    expect(planAction({ kind: "denied", name: "x", narration: "" }, live)).toEqual({ kind: "ignore" });
  });

  it("asks first for a confirm-level action, and never runs it unasked", () => {
    const plan = planAction(action({ client: "new_chat", risk: "confirm", confirm: "Clear the chat?", narration: "Done." }), live);
    expect(plan).toEqual({ kind: "confirm", text: "Done.", ask: "Clear the chat?", step: { verb: "new_chat" } });
  });

  it("drops a confirm-level action that has no question or no runnable step", () => {
    expect(planAction(action({ client: "new_chat", risk: "confirm" }), live)).toEqual({ kind: "ignore" });
    expect(planAction(action({ client: "none", risk: "confirm", confirm: "Sure?" }), live)).toEqual({ kind: "ignore" });
  });

  it("does nothing for an unknown verb or a missing narration", () => {
    expect(planAction(action({ client: "launch_missiles" }), live)).toEqual({ kind: "ignore" });
    expect(planAction(action({ narration: "" }), live)).toEqual({ kind: "ignore" });
    expect(planAction(action({ client: "set_language", args: { language: "fr" } }), live)).toEqual({ kind: "ignore" });
  });
});
