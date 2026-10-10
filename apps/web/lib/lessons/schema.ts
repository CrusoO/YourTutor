/**
 * Runtime validator for lessons served by the API. Mirrors `validate_lesson_dict` in
 * apps/api/app/lessons/schema.py: the same fixtures (packages/shared/fixtures/lessons) must give
 * the same codes in both languages. Unknown keys are tolerated here (Python rejects them at load).
 */
import type { Lesson } from "./types";

type Obj = Record<string, unknown>;
const isObj = (v: unknown): v is Obj => typeof v === "object" && v !== null && !Array.isArray(v);
const isStr = (v: unknown): v is string => typeof v === "string";
const isNum = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const isArr = (v: unknown): v is unknown[] => Array.isArray(v);
const optional = (v: unknown, check: (x: unknown) => boolean) => v === undefined || v === null || check(v);

const COLORS = ["ink", "muted", "red", "blue", "green"];
const STATUSES = ["draft", "approved", "retired"];

const l10n = (v: unknown): boolean => isObj(v) && isStr(v.en) && v.en.length > 0 && optional(v.ne, isStr) && optional(v.as, isStr);
const color = (v: unknown) => optional(v, (c) => isStr(c) && COLORS.includes(c));
const nums = (o: Obj, keys: string[]) => keys.every((k) => optional(o[k], isNum));
const posInt = (v: unknown, min: number) => isNum(v) && Number.isInteger(v) && v >= min;

function action(v: unknown): boolean {
  if (!isObj(v)) return false;
  switch (v.kind) {
    case "write_text":
      return isNum(v.x) && isNum(v.y) && isNum(v.size) && v.size > 0 && isStr(v.text) && v.text.length > 0 && color(v.color);
    case "draw_shape":
      return (
        isStr(v.shape) &&
        ["rect", "circle", "line"].includes(v.shape) &&
        nums(v, ["x", "y", "w", "h", "cx", "cy", "r", "x1", "y1", "x2", "y2"]) &&
        color(v.color)
      );
    case "draw_arrow":
      return isNum(v.x1) && isNum(v.y1) && isNum(v.x2) && isNum(v.y2) && color(v.color);
    case "highlight":
      return isNum(v.x) && isNum(v.y) && isNum(v.w) && v.w > 0 && isNum(v.h) && v.h > 0;
    case "pause_and_ask":
      return (
        l10n(v.question) &&
        isArr(v.options) &&
        v.options.length >= 2 &&
        v.options.every((o) => isObj(o) && l10n(o.text) && typeof o.correct === "boolean" && optional(o.feedback, l10n))
      );
    default:
      return false;
  }
}

function scene(v: unknown): boolean {
  if (!isObj(v)) return false;
  const canvas = v.canvas;
  return (
    isStr(v.id) && v.id.length > 0 && isStr(v.skill_id) && v.skill_id.length > 0 && isStr(v.source_ref) &&
    optional(canvas, (c) => isObj(c) && posInt(c.width, 1) && posInt(c.height, 1)) &&
    l10n(v.alt) && isArr(v.steps) && v.steps.length > 0 &&
    v.steps.every((s) => isObj(s) && l10n(s.caption) && isArr(s.actions) && s.actions.length > 0 && s.actions.every(action))
  );
}

function balanceParams(v: unknown): boolean {
  return (
    isObj(v) && posInt(v.left_boxes, 0) && posInt(v.left_weights, 0) && posInt(v.right_boxes, 0) &&
    posInt(v.right_weights, 0) && posInt(v.box_weight, 1)
  );
}

function widget(v: unknown): boolean {
  if (!isObj(v) || !isStr(v.widget_id) || v.widget_id.length === 0) return false;
  if (!l10n(v.prompt) || !l10n(v.success) || !optional(v.hint, l10n)) return false;
  if (v.type === "balance_scale") return balanceParams(v.params);
  if (v.type === "function_graph") {
    const p = v.params;
    return (
      isObj(p) && isNum(p.slope) && isNum(p.intercept) && isNum(p.target_y) && isNum(p.x_min) && isNum(p.x_max) &&
      optional(p.step, (s) => isNum(s) && s > 0) && optional(p.label, isStr) &&
      optional(p.x_label, l10n) && optional(p.target_label, l10n)
    );
  }
  return false;
}

function beat(v: unknown): boolean {
  if (!isObj(v)) return false;
  switch (v.kind) {
    case "predict":
      return (
        l10n(v.prompt) && optional(v.figure, balanceParams) && isArr(v.choices) && v.choices.length >= 2 &&
        v.choices.every((c) => isObj(c) && isStr(c.value) && c.value.length > 0 && l10n(c.text)) && optional(v.reveal, l10n)
      );
    case "explore":
      return l10n(v.title) && optional(v.intro, l10n) && widget(v.widget);
    case "explain_scene":
      return l10n(v.title) && scene(v.scene) && l10n(v.final_caption);
    case "worked_example":
      return l10n(v.title) && l10n(v.problem) && isArr(v.steps) && v.steps.length >= 2 && v.steps.every(l10n);
    case "faded_example":
      return (
        l10n(v.title) && l10n(v.problem) && isArr(v.steps) && v.steps.length >= 1 && v.steps.every(l10n) &&
        l10n(v.blank_prompt) && isStr(v.answer) && optional(v.accept, (a) => isArr(a) && a.every(isStr)) &&
        optional(v.hint, l10n) && l10n(v.success)
      );
    case "check":
      return l10n(v.prompt);
    default:
      return false;
  }
}

function isStructurallyValid(data: unknown): data is Lesson {
  return (
    isObj(data) && isStr(data.id) && data.id.length > 0 && isStr(data.skill_id) && data.skill_id.length > 0 &&
    l10n(data.title) && isStr(data.source_ref) && data.source_ref.length > 0 &&
    optional(data.status, (s) => isStr(s) && STATUSES.includes(s)) &&
    isArr(data.beats) && data.beats.length >= 3 && data.beats.every(beat)
  );
}

function widgetRuleErrors(w: Lesson["beats"][number] & { kind: "explore" }): string[] {
  const widgetSpec = w.widget;
  if (widgetSpec.type === "balance_scale") {
    const p = widgetSpec.params;
    const errors: string[] = [];
    if (p.left_boxes < 1 || p.right_boxes !== 0) errors.push("widget.balance_shape");
    if (p.left_boxes * p.box_weight + p.left_weights !== p.right_boxes * p.box_weight + p.right_weights) {
      errors.push("widget.balance_not_balanced");
    }
    return errors;
  }
  const g = widgetSpec.params;
  const step = g.step ?? 0.1;
  if (g.x_min >= g.x_max) return ["widget.graph_range"];
  if (g.slope === 0) return ["widget.graph_slope_zero"];
  const xStar = (g.target_y - g.intercept) / g.slope;
  if (!(g.x_min - 1e-9 <= xStar && xStar <= g.x_max + 1e-9)) return ["widget.graph_goal_unreachable"];
  const k = Math.round((xStar - g.x_min) / step);
  if (Math.abs(g.x_min + k * step - xStar) > 1e-9) return ["widget.graph_goal_unreachable"];
  return [];
}

function shapeFieldsOk(a: { shape: string } & Record<string, unknown>): boolean {
  const needed: Record<string, string[]> = {
    rect: ["x", "y", "w", "h"],
    circle: ["cx", "cy", "r"],
    line: ["x1", "y1", "x2", "y2"],
  };
  return needed[a.shape].every((k) => a[k] !== undefined && a[k] !== null);
}

function sceneRuleErrors(s: Lesson["beats"][number] & { kind: "explain_scene" }, skillId: string): string[] {
  const sc = s.scene;
  const errors: string[] = [];
  if (sc.skill_id !== skillId) errors.push("scene.skill_mismatch");
  if (!sc.source_ref.trim()) errors.push("scene.source_ref_blank");
  const asks = sc.steps.flatMap((st) => st.actions).filter((a) => a.kind === "pause_and_ask");
  if (asks.length === 0) errors.push("scene.no_pause_and_ask");
  if (asks.some((a) => a.kind === "pause_and_ask" && a.options.filter((o) => o.correct).length !== 1)) {
    errors.push("ask.correct_count");
  }
  const badShape = sc.steps
    .flatMap((st) => st.actions)
    .some((a) => a.kind === "draw_shape" && !shapeFieldsOk(a as unknown as { shape: string } & Record<string, unknown>));
  if (badShape) errors.push("scene.shape_fields");
  return errors;
}

/** Returns [] for a valid lesson, otherwise stable error codes (same as the Python validator). */
export function validateLesson(data: unknown): string[] {
  if (!isStructurallyValid(data)) return ["schema.invalid"];
  const errors: string[] = [];
  const kinds = data.beats.map((b) => b.kind);
  if (kinds[0] !== "predict") errors.push("lesson.first_beat_not_predict");
  if (kinds[kinds.length - 1] !== "check") errors.push("lesson.last_beat_not_check");
  else if (kinds.filter((k) => k === "check").length > 1) errors.push("lesson.check_count");
  if (kinds.filter((k) => k === "predict").length !== 1) errors.push("lesson.predict_count");
  if (!kinds.includes("explain_scene")) errors.push("lesson.no_explain_scene");
  const firstFaded = kinds.indexOf("faded_example");
  if (firstFaded !== -1 && (!kinds.includes("worked_example") || firstFaded < kinds.indexOf("worked_example"))) {
    errors.push("lesson.faded_before_worked_example");
  }
  if (data.beats.some((b) => b.kind === "faded_example" && b.answer.trim() === "")) errors.push("faded.answer_blank");
  const ids = data.beats.flatMap((b) => (b.kind === "explore" ? [b.widget.widget_id] : []));
  if (new Set(ids).size !== ids.length) errors.push("lesson.duplicate_widget_id");
  for (const b of data.beats) {
    if (b.kind === "explain_scene") errors.push(...sceneRuleErrors(b, data.skill_id));
  }
  for (const b of data.beats) {
    if (b.kind === "explore") errors.push(...widgetRuleErrors(b));
  }
  return [...new Set(errors)];
}
