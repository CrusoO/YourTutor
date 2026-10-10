"""Lesson beat events (`interactive_result`, `scene_answer`, `faded_answer`): server-checked.

These events never reach the policy and never touch BKT or FSRS; they are only recorded. A widget
result is re-checked with the same Python predicate the client mirrors, so a forged "solved" state
is rejected and flagged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.lessons.loader import lesson_for_skill, servable
from app.lessons.schema import Lesson, PauseAndAsk
from app.lessons.widgets import verify_widget_result
from app.orchestrator.types import SessionState
from app.verifier.check import verify_response

LESSON_EVENTS = frozenset({"interactive_result", "scene_answer", "faded_answer"})
LESSON_PHASES = frozenset({"predict", "worked_example"})


@dataclass(frozen=True)
class LessonVerdict:
    ok: bool
    code: str | None
    correct: bool | None  # what the event row stores as `correct`


def lesson_for_state(state: SessionState) -> Lesson | None:
    if state.phase not in LESSON_PHASES or not state.current_skill:
        return None
    lesson = lesson_for_skill(state.current_skill)
    return lesson if lesson is not None and servable(lesson) else None


def check_lesson_event(
    state: SessionState, event_type: str, payload: dict[str, Any]
) -> LessonVerdict:
    lesson = lesson_for_state(state)
    if lesson is None:
        return LessonVerdict(False, "lesson_event_out_of_phase", False)
    if event_type == "interactive_result":
        return _check_widget(lesson, payload)
    if event_type == "faded_answer":
        return _check_faded(lesson, payload)
    return _check_scene_answer(lesson, payload)


def _check_widget(lesson: Lesson, payload: dict[str, Any]) -> LessonVerdict:
    widget = next((w for w in lesson.widgets() if w.widget_id == payload.get("widget_id")), None)
    if widget is None:
        return LessonVerdict(False, "widget_unknown", False)
    ok, code = verify_widget_result(widget, payload)
    return LessonVerdict(ok, code, ok)


def _check_faded(lesson: Lesson, payload: dict[str, Any]) -> LessonVerdict:
    """Formative: a wrong answer is recorded as incorrect, not rejected. Client flags ignored."""
    faded = lesson.faded_examples()
    index, response = payload.get("faded"), payload.get("response")
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(faded):
        return LessonVerdict(False, "faded_unknown", False)
    if not isinstance(response, str):
        return LessonVerdict(False, "faded_answer_malformed", False)
    beat = faded[index]
    correct = verify_response(response, answer_sympy=beat.answer, accept=beat.accept)
    return LessonVerdict(True, None, correct)


def _check_scene_answer(lesson: Lesson, payload: dict[str, Any]) -> LessonVerdict:
    scene = next((s for s in lesson.scenes() if s.id == payload.get("scene_id")), None)
    if scene is None:
        return LessonVerdict(False, "scene_unknown", False)
    step, choice = payload.get("step"), payload.get("choice")
    if not isinstance(step, int) or isinstance(step, bool) or not 0 <= step < len(scene.steps):
        return LessonVerdict(False, "scene_answer_malformed", False)
    ask = next((a for a in scene.steps[step].actions if isinstance(a, PauseAndAsk)), None)
    if ask is None or not isinstance(choice, int) or isinstance(choice, bool):
        return LessonVerdict(False, "scene_answer_malformed", False)
    if not 0 <= choice < len(ask.options):
        return LessonVerdict(False, "scene_answer_malformed", False)
    # formative: a wrong answer is recorded as incorrect but is not a rejection
    return LessonVerdict(True, None, ask.options[choice].correct)
