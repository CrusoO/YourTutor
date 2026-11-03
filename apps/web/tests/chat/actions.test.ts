import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { decide, normalise, planAction, SCREENS, stepFor, type ActionDirective, type ActionRules, type Tier } from "@/lib/chat/actions";

const DIR = path.resolve(__dirname, "../../../../packages/shared/fixtures/actions");
const rules = JSON.parse(fs.readFileSync(path.join(DIR, "rules_en.json"), "utf-8")) as ActionRules;
const cases = JSON.parse(fs.readFileSync(path.join(DIR, "cases.json"), "utf-8")).cases as {
  text: string;
  tier: Tier;
  expect: { kind: string; name?: string; args?: Record<string, string>; risk?: string };
}[];

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

describe("the matcher agrees with the Python reference (shared cases)", () => {
  it("has the fixtures", () => {
    expect(cases.length).toBeGreaterThanOrEqual(20);
    expect(Object.keys(rules.phrases).length).toBeGreaterThan(20);
  });

  it.each(cases.map((c) => [`${c.tier}: ${JSON.stringify(c.text)}`, c] as const))("%s", (_label, c) => {
    const got = decide(c.text, rules, c.tier);
    const want = c.expect;
    expect(got.kind).toBe(want.kind);
    if (got.kind === "action") expect({ name: got.name, args: got.args, risk: got.risk }).toEqual({ name: want.name, args: want.args, risk: want.risk });
    if (got.kind === "denied") expect(got.name).toBe(want.name);
  });

  it("normalises every phrase key to itself, as Python does", () => {
    for (const key of Object.keys(rules.phrases)) expect(normalise(key, rules.fillers)).toBe(key);
  });

  it("keeps Indic combining marks", () => {
    expect(normalise("हिन्दी!", [])).toBe("हिन्दी");
  });

  it("never runs a verb or screen outside the closed list, whatever the table says", () => {
    const hostile: ActionRules = {
      ...rules,
      phrases: { oops: { name: "x", args: { screen: "/admin" } } },
      actions: { x: { client: "open_screen", risk: "safe", tiers: ["guest"], narration: "Opening." } },
    };
    const directive = decide("oops", hostile, "guest");
    expect(directive.kind).toBe("action");
    expect(planAction(directive, (c) => c === "en")).toEqual({ kind: "ignore" });
  });
});
