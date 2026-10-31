"""Lesson, scene-script and widget schemas (ARCHITECTURE §16). Source of truth for the JSON
Schemas in packages/shared/schemas/ and for the TypeScript validator, which runs the same fixtures.

`validate_lesson_dict` returns stable error codes: "schema.invalid" for any structural problem,
then specific rule codes (e.g. "lesson.first_beat_not_predict") that the TS validator reproduces.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from app.content.schema import ContentStatus, LocalizedText

Color = Literal["ink", "muted", "red", "blue", "green"]
SCENE_CANVAS_DEFAULT = (340, 290)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


# ---------------------------------------------------------------- scene script


class WriteText(_Strict):
    kind: Literal["write_text"]
    x: float
    y: float
    size: float = Field(gt=0)
    text: str = Field(min_length=1)
    color: Color | None = None


class DrawShape(_Strict):
    kind: Literal["draw_shape"]
    shape: Literal["rect", "circle", "line"]
    x: float | None = None
    y: float | None = None
    w: float | None = None
    h: float | None = None
    cx: float | None = None
    cy: float | None = None
    r: float | None = None
    x1: float | None = None
    y1: float | None = None
    x2: float | None = None
    y2: float | None = None
    color: Color | None = None


class DrawArrow(_Strict):
    kind: Literal["draw_arrow"]
    x1: float
    y1: float
    x2: float
    y2: float
    color: Color | None = None


class Highlight(_Strict):
    kind: Literal["highlight"]
    x: float
    y: float
    w: float = Field(gt=0)
    h: float = Field(gt=0)


class AskOption(_Strict):
    text: LocalizedText
    correct: bool
    feedback: LocalizedText | None = None


class PauseAndAsk(_Strict):
    kind: Literal["pause_and_ask"]
    question: LocalizedText
    options: list[AskOption] = Field(min_length=2)


SceneAction = Annotated[
    WriteText | DrawShape | DrawArrow | Highlight | PauseAndAsk, Field(discriminator="kind")
]


class SceneStep(_Strict):
    caption: LocalizedText
    actions: list[SceneAction] = Field(min_length=1)


class Canvas(_Strict):
    width: int = Field(default=SCENE_CANVAS_DEFAULT[0], gt=0)
    height: int = Field(default=SCENE_CANVAS_DEFAULT[1], gt=0)


class Scene(_Strict):
    id: str = Field(min_length=1)
    skill_id: str = Field(min_length=1)
    source_ref: str  # blank is a rule error so authors get a clear code
    canvas: Canvas = Field(default_factory=Canvas)
    alt: LocalizedText
    steps: list[SceneStep] = Field(min_length=1)


# ---------------------------------------------------------------- widgets


class BalanceScaleParams(_Strict):
    left_boxes: int = Field(ge=0)
    left_weights: int = Field(ge=0)
    right_boxes: int = Field(ge=0)
    right_weights: int = Field(ge=0)
    box_weight: int = Field(ge=1)  # hidden weight x of one box


class FunctionGraphParams(_Strict):
    slope: float
    intercept: float
    target_y: float
    x_min: float
    x_max: float
    step: float = Field(default=0.1, gt=0)
    label: str | None = None  # drawn next to the line, e.g. "y = 2x + 3"
    x_label: LocalizedText | None = None  # name of the horizontal axis
    target_label: LocalizedText | None = None  # name of the dashed target line


class _WidgetBase(_Strict):
    widget_id: str = Field(min_length=1)
    prompt: LocalizedText
    success: LocalizedText
    hint: LocalizedText | None = None


class BalanceScaleWidget(_WidgetBase):
    type: Literal["balance_scale"]
    params: BalanceScaleParams


class FunctionGraphWidget(_WidgetBase):
    type: Literal["function_graph"]
    params: FunctionGraphParams


WidgetSpec = Annotated[BalanceScaleWidget | FunctionGraphWidget, Field(discriminator="type")]


# ---------------------------------------------------------------- lesson


class PredictChoice(_Strict):
    value: str = Field(min_length=1)
    text: LocalizedText


class PredictBeat(_Strict):
    kind: Literal["predict"]
    prompt: LocalizedText
    figure: BalanceScaleParams | None = None
    choices: list[PredictChoice] = Field(min_length=2)
    reveal: LocalizedText | None = None


class ExploreBeat(_Strict):
    kind: Literal["explore"]
    title: LocalizedText
    intro: LocalizedText | None = None
    widget: WidgetSpec


class ExplainSceneBeat(_Strict):
    kind: Literal["explain_scene"]
    title: LocalizedText
    scene: Scene
    final_caption: LocalizedText


class WorkedExampleBeat(_Strict):
    kind: Literal["worked_example"]
    title: LocalizedText
    problem: LocalizedText
    steps: list[LocalizedText] = Field(min_length=2)


class FadedExampleBeat(_Strict):
    """A worked example with its last step left to the student; checked by the server, formative."""

    kind: Literal["faded_example"]
    title: LocalizedText
    problem: LocalizedText
    steps: list[LocalizedText] = Field(min_length=1)  # the steps still shown
    blank_prompt: LocalizedText  # asks for the missing last step or value
    answer: str  # blank is a rule error so authors get a clear code
    accept: list[str] = Field(default_factory=list)
    hint: LocalizedText | None = None
    success: LocalizedText


class CheckBeat(_Strict):
    kind: Literal["check"]
    prompt: LocalizedText


Beat = Annotated[
    PredictBeat | ExploreBeat | ExplainSceneBeat | WorkedExampleBeat | FadedExampleBeat | CheckBeat,
    Field(discriminator="kind"),
]


class Lesson(_Strict):
    id: str = Field(min_length=1)
    skill_id: str = Field(min_length=1)
    title: LocalizedText
    source_ref: str = Field(min_length=1)
    status: ContentStatus = ContentStatus.draft
    reviewed_by: str | None = None  # set with the approval, together with content_hash
    content_hash: str | None = None
    beats: list[Beat] = Field(min_length=3)

    def scenes(self) -> list[Scene]:
        return [beat.scene for beat in self.beats if isinstance(beat, ExplainSceneBeat)]

    def faded_examples(self) -> list[FadedExampleBeat]:
        return [beat for beat in self.beats if isinstance(beat, FadedExampleBeat)]

    def widgets(self) -> list[BalanceScaleWidget | FunctionGraphWidget]:
        return [beat.widget for beat in self.beats if isinstance(beat, ExploreBeat)]


# ---------------------------------------------------------------- rules


def scene_rule_errors(scene: Scene, skill_id: str) -> list[str]:
    errors: list[str] = []
    if scene.skill_id != skill_id:
        errors.append("scene.skill_mismatch")
    if not scene.source_ref.strip():
        errors.append("scene.source_ref_blank")
    asks = [a for step in scene.steps for a in step.actions if isinstance(a, PauseAndAsk)]
    if not asks:
        errors.append("scene.no_pause_and_ask")
    if any(sum(opt.correct for opt in ask.options) != 1 for ask in asks):
        errors.append("ask.correct_count")
    for step in scene.steps:
        for action in step.actions:
            if isinstance(action, DrawShape) and not _shape_fields_ok(action):
                errors.append("scene.shape_fields")
                break
    return list(dict.fromkeys(errors))


def _shape_fields_ok(shape: DrawShape) -> bool:
    needed = {
        "rect": (shape.x, shape.y, shape.w, shape.h),
        "circle": (shape.cx, shape.cy, shape.r),
        "line": (shape.x1, shape.y1, shape.x2, shape.y2),
    }[shape.shape]
    return all(value is not None for value in needed)


def widget_rule_errors(widget: BalanceScaleWidget | FunctionGraphWidget) -> list[str]:
    if isinstance(widget, BalanceScaleWidget):
        p = widget.params
        errors: list[str] = []
        if p.left_boxes < 1 or p.right_boxes != 0:
            errors.append("widget.balance_shape")
        if p.left_boxes * p.box_weight + p.left_weights != (
            p.right_boxes * p.box_weight + p.right_weights
        ):
            errors.append("widget.balance_not_balanced")
        return errors
    g = widget.params
    if g.x_min >= g.x_max:
        return ["widget.graph_range"]
    if g.slope == 0:
        return ["widget.graph_slope_zero"]
    x_star = (g.target_y - g.intercept) / g.slope
    if not (g.x_min - 1e-9 <= x_star <= g.x_max + 1e-9):
        return ["widget.graph_goal_unreachable"]
    k = round((x_star - g.x_min) / g.step)
    if abs(g.x_min + k * g.step - x_star) > 1e-9:
        return ["widget.graph_goal_unreachable"]
    return []


def lesson_rule_errors(lesson: Lesson) -> list[str]:
    errors: list[str] = []
    kinds = [beat.kind for beat in lesson.beats]
    if kinds[0] != "predict":
        errors.append("lesson.first_beat_not_predict")
    if kinds[-1] != "check":
        errors.append("lesson.last_beat_not_check")
    elif kinds.count("check") > 1:
        errors.append("lesson.check_count")
    if kinds.count("predict") != 1:
        errors.append("lesson.predict_count")
    if "explain_scene" not in kinds:
        errors.append("lesson.no_explain_scene")
    if "faded_example" in kinds and (
        "worked_example" not in kinds
        or kinds.index("faded_example") < kinds.index("worked_example")
    ):
        errors.append("lesson.faded_before_worked_example")
    if any(not beat.answer.strip() for beat in lesson.faded_examples()):
        errors.append("faded.answer_blank")
    widget_ids = [w.widget_id for w in lesson.widgets()]
    if len(set(widget_ids)) != len(widget_ids):
        errors.append("lesson.duplicate_widget_id")
    for scene in lesson.scenes():
        errors.extend(scene_rule_errors(scene, lesson.skill_id))
    for widget in lesson.widgets():
        errors.extend(widget_rule_errors(widget))
    return list(dict.fromkeys(errors))


def validate_lesson_dict(data: Any) -> list[str]:
    try:
        lesson = Lesson.model_validate(data)
    except ValidationError:
        return ["schema.invalid"]
    return lesson_rule_errors(lesson)


def lesson_json_schemas() -> dict[str, dict[str, Any]]:
    return {
        "lesson.schema.json": Lesson.model_json_schema(),
        "scene.schema.json": Scene.model_json_schema(),
        "widget.schema.json": TypeAdapter(WidgetSpec).json_schema(),  # type: ignore[arg-type]
    }
