import type { ChatChoice, ChatScenario, Note } from "./landing-extras";

/** Where a visitor is in one scripted example: nothing picked, a guess made, then the ways they asked to be taught. */
export type DemoState = { picked: string | null; asked: ReadonlyArray<"first" | "second"> };

export const START: DemoState = { picked: null, asked: [] };

/** Make a guess. Only the first guess counts; the example does not let it be changed. */
export function guess(state: DemoState, choiceId: string): DemoState {
  return state.picked === null ? { ...state, picked: choiceId } : state;
}

/** Ask for an explanation. Each way can be asked once, and only after a guess. */
export function ask(state: DemoState, id: "first" | "second"): DemoState {
  if (state.picked === null || state.asked.includes(id)) return state;
  return { ...state, asked: [...state.asked, id] };
}

export function pickedChoice(scenario: ScenarioLike, state: DemoState): ChatChoice | null {
  return scenario.diagnostic.choices.find((c) => c.id === state.picked) ?? null;
}

type ScenarioLike = Pick<ChatScenario, "diagnostic" | "preferenceNote">;

/**
 * What Brownie has written down so far: one note about the idea the question tested, and, once the visitor
 * has asked to be taught, one about how they like it explained (the latest way they asked).
 */
export function notesFor(scenario: ScenarioLike, state: DemoState): Note[] {
  const notes: Note[] = [];
  const choice = pickedChoice(scenario, state);
  if (choice) notes.push(choice.note);
  const latest = state.asked[state.asked.length - 1];
  if (latest) notes.push(scenario.preferenceNote[latest]);
  return notes;
}

/** The ways of being taught that have not been asked for yet. */
export function remaining(scenario: Pick<ChatScenario, "explanations">, state: DemoState) {
  return scenario.explanations.filter((e) => !state.asked.includes(e.id));
}
