"""Interactive lesson blocks: a student question compiled into structured JSON blocks.

One model call. The LLM produces a JSON object with `level`, `objectives` and `blocks`.
Each block is one of: hook, predict, widget, explain, check, transfer, recap.
The same safety screen, consent gate and scope rules as service.py apply.
The output is safe-cleaned before it leaves this module.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.config import settings
from app.explain.service import Completer, ExplainProvider, Gate, precheck, unavailable
from app.explain.story import extract_json
from app.llm.prompt import STUDENT_TAG, Prompt
from app.llm.provider import ProviderError
from app.llm.rules import default_rules

PROMPT_FILE = Path(__file__).parent / "prompts" / "lesson.v1.md"
PROMPT_VERSION = "lesson/v1"
MAX_TOKENS = 4000
MAX_QUESTION_CHARS = 300
LANGUAGES = ("en", "hi")
MAX_ATTEMPTS = 2
MIN_BLOCKS = 4
MAX_BLOCKS = 9

OPEN_SCOPE = (
    "Build a lesson on any topic a curious student might want to learn, in any subject. "
    "Refuse only requests that are harmful, sexual, hateful, ask for personal advice or help "
    'with a crime: for those output exactly {"refuse": true} and nothing else.'
)
SYLLABUS_SCOPE = (
    "Build lessons only on topics from a school syllabus (classes 6 to 12) and the ideas "
    "they are built on. If the request is not about that, output exactly "
    '{"refuse": true} and nothing else.'
)

VALID_BLOCK_KINDS = {"hook", "predict", "widget", "explain", "check", "transfer", "recap"}
VALID_WIDGET_KINDS = {"slider_sim", "step_through", "drag_sort", "graph_explore", "toggle_compare"}
VALID_COLORS = {"blue", "red", "green", "orange", "purple"}
FENCE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")


def _words(value: Any, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:limit]


def _str(value: Any, limit: int = 400) -> str:
    return _words(value, limit) if isinstance(value, str) else ""


def _int_or(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _num(value: Any) -> float | int | None:
    if isinstance(value, (int, float)):
        return value
    return None


# ── per-block cleaners ────────────────────────────────────────────────────────


def _clean_hook(raw: dict[str, Any]) -> dict[str, Any] | None:
    text = _str(raw.get("text"), 500)
    question = _str(raw.get("question"), 200)
    if not text or not question:
        return None
    return {"kind": "hook", "text": text, "question": question}


def _clean_predict(raw: dict[str, Any]) -> dict[str, Any] | None:
    prompt = _str(raw.get("prompt"), 300)
    if not prompt:
        return None
    free_text = bool(raw.get("free_text"))
    if free_text:
        reveal = _str(raw.get("reveal_after"), 400)
        return {
            "kind": "predict",
            "prompt": prompt,
            "free_text": True,
            "correct": None,
            "reveal_after": reveal,
        }
    options = raw.get("options")
    if not isinstance(options, list) or not (2 <= len(options) <= 4):
        return None
    options = [_str(o, 200) for o in options if isinstance(o, str)]
    if len(options) < 2:
        return None
    correct = _int_or(raw.get("correct"), -1)
    if not (0 <= correct < len(options)):
        correct = 0
    reveal = _str(raw.get("reveal_after"), 400)
    return {
        "kind": "predict",
        "prompt": prompt,
        "free_text": False,
        "options": options,
        "correct": correct,
        "reveal_after": reveal,
    }


def _clean_controls(raw_controls: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_controls, list):
        return []
    out: list[dict[str, Any]] = []
    for c in raw_controls[:3]:
        if not isinstance(c, dict):
            continue
        label = _str(c.get("label"), 60)
        var = re.sub(r"[^A-Za-z0-9_]", "", str(c.get("var", "")))[:32]
        mn = _num(c.get("min"))
        mx = _num(c.get("max"))
        step = _num(c.get("step"))
        if label and var and mn is not None and mx is not None:
            out.append(
                {
                    "label": label,
                    "var": var,
                    "min": mn,
                    "max": mx,
                    "step": step if step is not None else 1,
                }
            )
    return out


def _clean_widget_spec(kind: str, spec: Any) -> dict[str, Any] | None:
    if not isinstance(spec, dict):
        return None
    if kind == "slider_sim":
        variable = re.sub(r"[^A-Za-z0-9_]", "", str(spec.get("variable", "")))[:32]
        formula = _str(spec.get("formula"), 200)
        out_label = _str(spec.get("output_label"), 80)
        if not variable or not formula or not out_label:
            return None
        return {
            "variable": variable,
            "unit": _str(spec.get("unit"), 20),
            "min": _num(spec.get("min")) if _num(spec.get("min")) is not None else 0,
            "max": _num(spec.get("max")) if _num(spec.get("max")) is not None else 10,
            "step": _num(spec.get("step")) if _num(spec.get("step")) is not None else 1,
            "formula": formula,
            "output_label": out_label,
            "output_unit": _str(spec.get("output_unit"), 20),
        }
    if kind == "step_through":
        steps = spec.get("steps")
        if not isinstance(steps, list) or not (2 <= len(steps) <= 6):
            return None
        cleaned = [
            {"label": _str(s.get("label"), 80), "description": _str(s.get("description"), 300)}
            for s in steps
            if isinstance(s, dict)
        ]
        cleaned = [s for s in cleaned if s["label"]]
        return {"steps": cleaned} if len(cleaned) >= 2 else None
    if kind == "drag_sort":
        items = spec.get("items")
        order = spec.get("correct_order")
        if not isinstance(items, list) or not (3 <= len(items) <= 6):
            return None
        if not isinstance(order, list) or len(order) != len(items):
            order = list(range(len(items)))
        items = [_str(i, 100) for i in items]
        order = [_int_or(x, i) for i, x in enumerate(order)]
        return {"items": items, "correct_order": order}
    if kind == "graph_explore":
        series = spec.get("series")
        if not isinstance(series, list) or not series:
            return None
        cleaned_series = []
        for s in series[:2]:
            if not isinstance(s, dict):
                continue
            color = s.get("color", "blue")
            cleaned_series.append(
                {
                    "name": _str(s.get("name"), 60),
                    "formula": _str(s.get("formula"), 200),
                    "color": color if color in VALID_COLORS else "blue",
                }
            )
        if not cleaned_series:
            return None
        return {
            "x_label": _str(spec.get("x_label"), 60),
            "x_unit": _str(spec.get("x_unit"), 20),
            "y_label": _str(spec.get("y_label"), 60),
            "y_unit": _str(spec.get("y_unit"), 20),
            "x_min": _num(spec.get("x_min")) if _num(spec.get("x_min")) is not None else 0,
            "x_max": _num(spec.get("x_max")) if _num(spec.get("x_max")) is not None else 10,
            "x_step": _num(spec.get("x_step")) if _num(spec.get("x_step")) is not None else 1,
            "series": cleaned_series,
        }
    if kind == "toggle_compare":
        la, da = _str(spec.get("label_a"), 60), _str(spec.get("description_a"), 400)
        lb, db = _str(spec.get("label_b"), 60), _str(spec.get("description_b"), 400)
        if not la or not lb:
            return None
        return {"label_a": la, "description_a": da, "label_b": lb, "description_b": db}
    return None


def _clean_widget(raw: dict[str, Any]) -> dict[str, Any] | None:
    # The LLM may use "kind" as the widget subtype directly (e.g. "graph_explore")
    # or wrap it as kind:"widget" with "widget_kind" for the subtype.
    wkind = str(raw.get("widget_kind") or "")
    if wkind not in VALID_WIDGET_KINDS:
        # fall back: maybe kind IS the widget subtype
        wkind = str(raw.get("kind") or "")
        if wkind not in VALID_WIDGET_KINDS:
            return None
    spec = _clean_widget_spec(wkind, raw.get("spec"))
    if spec is None:
        return None
    controls = _clean_controls(raw.get("controls"))
    notice = _str(raw.get("what_to_notice"), 200)
    return {
        "kind": "widget",
        "widget_kind": wkind,
        "spec": spec,
        "controls": controls,
        "what_to_notice": notice,
    }


def _clean_explain(raw: dict[str, Any]) -> dict[str, Any] | None:
    text = _str(raw.get("text"), 600)
    if not text:
        return None
    out: dict[str, Any] = {"kind": "explain", "text": text}
    analogy = _str(raw.get("analogy"), 250)
    if analogy:
        out["analogy"] = analogy
    return out


def _clean_check(raw: dict[str, Any]) -> dict[str, Any] | None:
    question = _str(raw.get("question"), 300)
    options = raw.get("options")
    if not question or not isinstance(options, list) or len(options) != 4:
        return None
    options = [_str(o, 200) for o in options]
    correct = _int_or(raw.get("correct"), 0)
    if not (0 <= correct < 4):
        correct = 0
    feedback = raw.get("feedback_per_option")
    if not isinstance(feedback, list) or len(feedback) != 4:
        feedback = [""] * 4
    feedback = [_str(f, 300) for f in feedback]
    hints = raw.get("hint_ladder")
    if not isinstance(hints, list) or len(hints) < 3:
        hints = ["Think about the core idea.", "What happens when you apply it here?", ""]
    hints = [_str(h, 300) for h in hints[:3]]
    return {
        "kind": "check",
        "question": question,
        "options": options,
        "correct": correct,
        "feedback_per_option": feedback,
        "hint_ladder": hints,
    }


def _clean_transfer(raw: dict[str, Any]) -> dict[str, Any] | None:
    scenario = _str(raw.get("scenario"), 500)
    question = _str(raw.get("question"), 300)
    answer = _str(raw.get("model_answer"), 500)
    if not scenario or not question:
        return None
    return {"kind": "transfer", "scenario": scenario, "question": question, "model_answer": answer}


def _clean_recap(raw: dict[str, Any]) -> dict[str, Any] | None:
    bullets = raw.get("three_bullets")
    if not isinstance(bullets, list) or len(bullets) < 2:
        return None
    bullets = [_str(b, 200) for b in bullets[:3]]
    bullets = [b for b in bullets if b]
    if len(bullets) < 2:
        return None
    review = _str(raw.get("spaced_review_question"), 300)
    return {"kind": "recap", "three_bullets": bullets, "spaced_review_question": review}


_CLEANERS = {
    "hook": _clean_hook,
    "predict": _clean_predict,
    "widget": _clean_widget,
    "explain": _clean_explain,
    "check": _clean_check,
    "transfer": _clean_transfer,
    "recap": _clean_recap,
}


def clean_lesson(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Validate and sanitise raw LLM output. Returns None if the structure is unusable."""
    if not isinstance(data, dict):
        return None
    blocks_raw = data.get("blocks")
    if not isinstance(blocks_raw, list):
        return None

    blocks: list[dict[str, Any]] = []
    for raw in blocks_raw[:MAX_BLOCKS]:
        if not isinstance(raw, dict):
            continue
        kind = str(raw.get("kind", ""))
        if kind in VALID_WIDGET_KINDS:
            # LLM put the widget subtype directly in "kind"
            cleaned = _clean_widget(raw)
        else:
            cleaner = _CLEANERS.get(kind)
            if cleaner is None:
                continue
            cleaned = cleaner(raw)
        if cleaned is not None:
            blocks.append(cleaned)

    if len(blocks) < MIN_BLOCKS:
        return None

    level = _str(data.get("level"), 80) or "school"
    objectives_raw = data.get("objectives")
    objectives: list[str] = []
    if isinstance(objectives_raw, list):
        objectives = [_str(o, 200) for o in objectives_raw[:3] if isinstance(o, str)]

    return {"level": level, "objectives": objectives, "blocks": blocks}


# ── prompt + main entry point ─────────────────────────────────────────────────


def build_prompt(question: str, language: str, restricted: bool) -> Prompt:
    scope = SYLLABUS_SCOPE if restricted else OPEN_SCOPE
    system = PROMPT_FILE.read_text(encoding="utf-8").strip().replace("{scope_rule}", scope)
    cleaned = STUDENT_TAG.sub("", question)
    lang_note = "Reply in Hindi (Devanagari). " if language == "hi" else ""
    user = (
        f"<student_text>\n{cleaned}\n</student_text>\n\n"
        f"{lang_note}Build the interactive lesson now. Output the JSON object only."
    )
    return Prompt(system=system, user=user, version=PROMPT_VERSION, max_words=1200)


def build_lesson(
    question: str,
    language: str,
    gate: Gate,
    provider: Completer | None = None,
    model: str | None = None,
    restricted: bool = False,
) -> dict[str, Any]:
    language = language if language in LANGUAGES else "en"
    early, text_in, chosen = precheck(question, language, gate, provider, model)
    if early is not None:
        return early

    # lesson endpoint uses story model when set, falls back to strong model
    if not chosen:
        chosen = settings.llm_story_model or settings.llm_model_strong
    if not chosen:
        return unavailable("no_key")

    story_provider = ExplainProvider(
        json_mode=True,
        max_tokens=MAX_TOKENS,
        api_key=settings.llm_story_api_key or settings.llm_api_key or None,
    )
    actual_provider = provider or story_provider
    outcome: dict[str, Any] = unavailable("provider_error")

    for _ in range(MAX_ATTEMPTS):
        try:
            reply = actual_provider.complete(build_prompt(text_in, language, restricted), chosen)
        except ProviderError:
            outcome = unavailable("provider_error")
            continue

        text = reply.text.strip()

        # refuse signal
        if '"refuse"' in text and "true" in text:
            return {
                "kind": "out_of_scope",
                "message": "I cannot help with that one. Try asking about something you would like to learn.",  # noqa: E501
            }

        # blocked-term check (same guard as service.py)
        lowered = text.lower()
        if any(re.search(rf"{re.escape(term)}", lowered) for term in default_rules().blocked_terms):
            outcome = unavailable("checks")
            continue

        data = extract_json(text)
        lesson = clean_lesson(data)
        if lesson is None:
            outcome = unavailable("checks")
            continue

        return {"kind": "lesson", **lesson}

    return outcome
