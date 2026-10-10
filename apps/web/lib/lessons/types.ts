/** Lesson, scene and widget types. Mirrors apps/api/app/lessons/schema.py (the source of truth). */

export type L10n = { en: string; ne?: string | null; as?: string | null };
export type Color = "ink" | "muted" | "red" | "blue" | "green";

export type WriteText = {
  kind: "write_text";
  x: number;
  y: number;
  size: number;
  text: string;
  color?: Color | null;
};
export type DrawShape = {
  kind: "draw_shape";
  shape: "rect" | "circle" | "line";
  x?: number | null;
  y?: number | null;
  w?: number | null;
  h?: number | null;
  cx?: number | null;
  cy?: number | null;
  r?: number | null;
  x1?: number | null;
  y1?: number | null;
  x2?: number | null;
  y2?: number | null;
  color?: Color | null;
};
export type DrawArrow = {
  kind: "draw_arrow";
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  color?: Color | null;
};
export type Highlight = { kind: "highlight"; x: number; y: number; w: number; h: number };
export type AskOption = { text: L10n; correct: boolean; feedback?: L10n | null };
export type PauseAndAsk = { kind: "pause_and_ask"; question: L10n; options: AskOption[] };
export type SceneAction = WriteText | DrawShape | DrawArrow | Highlight | PauseAndAsk;
export type SceneStep = { caption: L10n; actions: SceneAction[] };
export type Scene = {
  id: string;
  skill_id: string;
  source_ref: string;
  canvas?: { width: number; height: number };
  alt: L10n;
  steps: SceneStep[];
};

export type BalanceScaleParams = {
  left_boxes: number;
  left_weights: number;
  right_boxes: number;
  right_weights: number;
  box_weight: number;
};
export type FunctionGraphParams = {
  slope: number;
  intercept: number;
  target_y: number;
  x_min: number;
  x_max: number;
  step?: number;
  label?: string | null;
  x_label?: L10n | null;
  target_label?: L10n | null;
};
type WidgetBase = { widget_id: string; prompt: L10n; success: L10n; hint?: L10n | null };
export type BalanceScaleWidget = WidgetBase & { type: "balance_scale"; params: BalanceScaleParams };
export type FunctionGraphWidget = WidgetBase & { type: "function_graph"; params: FunctionGraphParams };
export type WidgetSpec = BalanceScaleWidget | FunctionGraphWidget;

export type PredictBeat = {
  kind: "predict";
  prompt: L10n;
  figure?: BalanceScaleParams | null;
  choices: { value: string; text: L10n }[];
  reveal?: L10n | null;
};
export type ExploreBeat = { kind: "explore"; title: L10n; intro?: L10n | null; widget: WidgetSpec };
export type ExplainSceneBeat = {
  kind: "explain_scene";
  title: L10n;
  scene: Scene;
  final_caption: L10n;
};
export type WorkedExampleBeat = {
  kind: "worked_example";
  title: L10n;
  problem: L10n;
  steps: L10n[];
};
export type FadedExampleBeat = {
  kind: "faded_example";
  title: L10n;
  problem: L10n;
  steps: L10n[];
  blank_prompt: L10n;
  answer: string;
  accept?: string[];
  hint?: L10n | null;
  success: L10n;
};
export type CheckBeat = { kind: "check"; prompt: L10n };
export type Beat =
  | PredictBeat
  | ExploreBeat
  | ExplainSceneBeat
  | WorkedExampleBeat
  | FadedExampleBeat
  | CheckBeat;

export type Lesson = {
  id: string;
  skill_id: string;
  title: L10n;
  source_ref: string;
  status?: "draft" | "approved" | "retired";
  beats: Beat[];
};

/** Pick the string for a locale, falling back to English (never an empty string). */
export function pick(text: L10n | null | undefined, locale: string): string {
  if (!text) return "";
  const own = locale === "ne" ? text.ne : locale === "as" ? text.as : text.en;
  return own && own.trim() ? own : text.en;
}
