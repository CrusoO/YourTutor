import { RULE_COPY } from "./copy.en";
import type { Solution, Step } from "./types";

/** One step as a sentence of authored copy plus the state it reaches. */
export function renderStep(step: Step): string {
  const words = RULE_COPY[step.rule]({ ...step.args });
  return step.after && step.after !== step.before ? `${words} ${step.after}` : words;
}

export function renderSteps(steps: readonly Step[]): string[] {
  return steps.map(renderStep);
}

/** The state after step `n` (zero based), or null. Used for the level 3 lead-in. */
export function stateAfter(steps: readonly Step[], n: number): string | null {
  const s = steps[n];
  return s && s.after ? s.after : null;
}

export function describeAnswer(sol: Solution, letters: string): string {
  const a = sol.answer;
  const [x, y] = [letters[0] ?? "x", letters[1] ?? "y"];
  switch (a.kind) {
    case "values":
      return sol.exact.length === 1 && letters === "" ? a.values[0] : a.values.map((v) => `${letters || "x"} = ${v}`).join(" or ");
    case "surd":
      return [...a.values, ...a.surds].map((v) => `${letters || "x"} = ${v}`).join(" or ");
    case "expr":
      return a.value;
    case "pair":
      return `${x} = ${a.x}, ${y} = ${a.y}`;
    default:
      return "";
  }
}
