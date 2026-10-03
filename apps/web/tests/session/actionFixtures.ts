import type { ActionPayload } from "@/lib/api";

export const sampleItem = {
  id: "ITEM.FIX.1",
  type: "expression",
  stem: "Solve for x: x + 4 = 10",
  prediction: "Will x be smaller than 10?",
  options: [
    { id: "yes", label: "Yes" },
    { id: "no", label: "No" },
  ],
  steps: ["Subtract 4 from both sides.", "x = 6"],
  answer: "6",
};

export function actionFixture(type: ActionPayload["type"], extra: Partial<ActionPayload> = {}): ActionPayload {
  const base: ActionPayload = {
    type,
    item_id: sampleItem.id,
    session_type: "practice",
    allow_hint: false,
    can_request_hint: false,
    can_show_solution: false,
    dont_know_option: false,
    hint_level_shown: 0,
    item: sampleItem,
  };
  return { ...base, ...extra, type };
}

export const actionFixtures: Record<string, ActionPayload> = {
  warmup_item: actionFixture("warmup_item", {
    allow_hint: true,
    can_request_hint: true,
  }),
  predict: actionFixture("predict", { item: { ...sampleItem, stem: "" }, text: sampleItem.prediction }),
  worked_example: actionFixture("worked_example"),
  show_item: actionFixture("show_item", {
    allow_hint: true,
    can_request_hint: true,
    dont_know_option: true,
  }),
  feedback: actionFixture("feedback", { correct: false }),
  hint: actionFixture("hint", { text: "Try undoing the + 4.", hint_level: 1 }),
  reveal_solution: actionFixture("reveal_solution"),
  similar_item: actionFixture("similar_item", { allow_hint: true }),
  explain_back_prompt: actionFixture("explain_back_prompt", { text: "Explain in your own words." }),
  explain_back_result: actionFixture("explain_back_result", { text: "Thanks for explaining." }),
  nudge: actionFixture("nudge"),
  content_gap: actionFixture("content_gap"),
  end_session: actionFixture("end_session", { item: null, ended_reason: "soft_cap" }),
  checkpoint_score: actionFixture("checkpoint_score", {
    item: null,
    ended_reason: "checkpoint_complete",
    extras: { score: 1 },
  }),
};
