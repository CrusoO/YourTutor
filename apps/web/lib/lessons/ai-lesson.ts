/**
 * The interactive lesson the API builds from a typed question (POST /explain/lesson).
 *
 * The shapes mirror apps/api/app/explain/service_lesson.py, which has already cleaned and capped them.
 * Everything here still treats the data as untrusted: a widget whose formula does not parse, or does
 * not stay finite across its range, is dropped and the rest of the lesson is kept.
 */

import { compileFormula, finiteOver, type Formula } from "./formula";

export type AiControl = { label: string; var: string; min: number; max: number; step: number };

export type AiSliderSpec = {
  variable: string;
  unit: string;
  min: number;
  max: number;
  step: number;
  formula: string;
  output_label: string;
  output_unit: string;
};
export type AiStepSpec = { steps: { label: string; description: string }[] };
export type AiSortSpec = { items: string[]; correct_order: number[] };
export type AiSeries = { name: string; formula: string; color: "blue" | "red" | "green" | "orange" | "purple" };
export type AiGraphSpec = {
  x_label: string;
  x_unit: string;
  y_label: string;
  y_unit: string;
  x_min: number;
  x_max: number;
  x_step: number;
  series: AiSeries[];
};
export type AiToggleSpec = { label_a: string; description_a: string; label_b: string; description_b: string };

type WidgetBase = { kind: "widget"; controls: AiControl[]; what_to_notice: string };
export type AiWidget =
  | (WidgetBase & { widget_kind: "slider_sim"; spec: AiSliderSpec })
  | (WidgetBase & { widget_kind: "step_through"; spec: AiStepSpec })
  | (WidgetBase & { widget_kind: "drag_sort"; spec: AiSortSpec })
  | (WidgetBase & { widget_kind: "graph_explore"; spec: AiGraphSpec })
  | (WidgetBase & { widget_kind: "toggle_compare"; spec: AiToggleSpec });

export type AiHook = { kind: "hook"; text: string; question: string };
export type AiPredict = {
  kind: "predict";
  prompt: string;
  free_text: boolean;
  options?: string[];
  correct: number | null;
  reveal_after: string;
  /** A short name for the idea behind each wrong option (null for the right one); may be empty. */
  misconceptions?: (string | null)[];
};
export type AiExplain = { kind: "explain"; text: string; analogy?: string };
export type AiCheck = {
  kind: "check";
  question: string;
  options: string[];
  correct: number;
  feedback_per_option: string[];
  hint_ladder: string[];
  misconceptions?: (string | null)[];
};
export type AiTransfer = { kind: "transfer"; scenario: string; question: string; model_answer: string };
export type AiRecap = { kind: "recap"; three_bullets: string[]; spaced_review_question: string };

export type AiBlock = AiHook | AiPredict | AiWidget | AiExplain | AiCheck | AiTransfer | AiRecap;
export type AiLesson = { kind: "lesson"; level: string; objectives: string[]; blocks: AiBlock[] };

type LessonNotice =
  | { kind: "unavailable"; reason: string }
  | { kind: "refused" | "distress" | "out_of_scope"; message: string; reason?: string }
  | { kind: "empty" };

export type LessonResult = AiLesson | LessonNotice;

/** The first two blocks (a hook and a prediction), which arrive fast so the student can start. */
export type LessonOpeningResult =
  | { kind: "opening"; level: string; objectives: string[]; blocks: AiBlock[] }
  | LessonNotice;

/** The remaining blocks, written to follow the opening the student has already seen. */
export type LessonRestResult = { kind: "rest"; blocks: AiBlock[] } | LessonNotice;

/** A widget that is safe to draw, with its formulas already compiled. */
export type RunnableWidget =
  | { widget: Extract<AiWidget, { widget_kind: "slider_sim" }>; formula: Formula; controlVars: string[] }
  | { widget: Extract<AiWidget, { widget_kind: "graph_explore" }>; series: { series: AiSeries; formula: Formula }[] }
  | { widget: Extract<AiWidget, { widget_kind: "step_through" | "drag_sort" | "toggle_compare" }> };

const isPermutation = (order: number[], n: number): boolean =>
  order.length === n && new Set(order).size === n && order.every((i) => Number.isInteger(i) && i >= 0 && i < n);

/** Midpoints of the extra controls: the values the main variable is swept against. */
export function controlDefaults(controls: AiControl[]): Record<string, number> {
  return Object.fromEntries(controls.map((c) => [c.var, (c.min + c.max) / 2]));
}

/** Compile a widget, or return null when it cannot be drawn safely. */
export function runWidget(widget: AiWidget): RunnableWidget | null {
  switch (widget.widget_kind) {
    case "slider_sim": {
      const { spec } = widget;
      const controlVars = widget.controls.map((c) => c.var);
      if (!(spec.max > spec.min) || !(spec.step > 0)) return null;
      const formula = compileFormula(spec.formula, [spec.variable, ...controlVars]);
      if (!formula) return null;
      if (!finiteOver(formula, spec.variable, spec.min, spec.max, controlDefaults(widget.controls))) return null;
      return { widget, formula, controlVars };
    }
    case "graph_explore": {
      const { spec } = widget;
      if (!(spec.x_max > spec.x_min)) return null;
      const series = spec.series.flatMap((s) => {
        const formula = compileFormula(s.formula, ["x"]);
        return formula && finiteOver(formula, "x", spec.x_min, spec.x_max) ? [{ series: s, formula }] : [];
      });
      return series.length > 0 ? { widget, series } : null;
    }
    case "drag_sort":
      return isPermutation(widget.spec.correct_order, widget.spec.items.length) ? { widget } : null;
    case "step_through":
    case "toggle_compare":
      return { widget };
    default:
      return null;
  }
}

export type UsableBlock = { block: Exclude<AiBlock, AiWidget> } | { block: AiWidget; run: RunnableWidget };

function toUsable(blocks: AiBlock[]): UsableBlock[] {
  const out: UsableBlock[] = [];
  for (const block of blocks) {
    if (block.kind === "widget") {
      const run = runWidget(block);
      if (run) out.push({ block, run });
    } else {
      out.push({ block });
    }
  }
  return out;
}

/** The opening is exactly a hook then a prediction; anything else is not an opening. */
export function usableOpening(opening: { blocks: AiBlock[] }): UsableBlock[] | null {
  const kinds = opening.blocks.map((b) => b.kind).join(",");
  return kinds === "hook,predict" ? toUsable(opening.blocks) : null;
}

/** The blocks after the opening: at least three that can be drawn safely, ending with something to answer. */
export function usableRest(blocks: AiBlock[]): UsableBlock[] | null {
  const usable = toUsable(blocks.filter((b) => b.kind !== "hook"));
  return usable.length >= 3 && usable.some((u) => u.block.kind === "check") ? usable : null;
}

/**
 * The blocks a student will see, in order. A widget that cannot be drawn safely is removed; if what is
 * left no longer has enough to teach with (fewer than 3 blocks), the whole lesson is rejected so the
 * caller falls back to the written explanation.
 */
export function usableBlocks(lesson: AiLesson): UsableBlock[] | null {
  const out = toUsable(lesson.blocks);
  return out.length >= 3 ? out : null;
}
