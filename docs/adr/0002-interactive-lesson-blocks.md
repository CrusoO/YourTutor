# ADR 0002: Interactive Lesson Blocks — /explain/lesson

**Status:** accepted (2026-10-26)  
**Prompt version:** `lesson/v1`  
**Route:** `POST /explain/lesson`

---

## Context

`POST /explain` returns a static article (title + sections).  
`POST /explain/story` returns a scene-by-scene animated story script.

Neither format supports interactivity: a student can read or watch, but cannot predict, explore, or practise within the same flow. Students who ask open-ended questions benefit most from a lesson that cycles through: hook → predict → explore → explain → check → transfer → recap.

---

## Decision

Add `POST /explain/lesson` backed by a single LLM call that returns a JSON object with:

```json
{
  "kind": "lesson",
  "level": "class 9",
  "objectives": ["…", "…", "…"],
  "blocks": [ … ]
}
```

### Block types

| Kind | Purpose |
|---|---|
| `hook` | Surprising fact + the single question this lesson answers |
| `predict` | MCQ or free-text prediction — student commits before seeing the answer |
| `widget` | Interactive: `slider_sim`, `step_through`, `drag_sort`, `graph_explore`, `toggle_compare` |
| `explain` | At most 80 words of explanation placed after a widget or predict block |
| `check` | 4-option MCQ with per-option feedback and a 3-rung hint ladder |
| `transfer` | New-context scenario using the same principle |
| `recap` | Three bullets + a spaced-review question |

Block count: minimum 4, maximum 9.

### Prompt

`app/explain/prompts/lesson.v1.md` — owner-written.  
The scope placeholder `{scope_rule}` is replaced with either the open-scope rule (guests) or the syllabus-scope rule (registered students with `ai_processing` consent), using `.replace()` not `.format()` so JSON examples in the prompt survive unescaped.

### Validator (`clean_lesson`)

All LLM output passes through `clean_lesson()` in `service_lesson.py` before leaving the module.  
Every field is type-checked and length-capped; unknown fields are silently dropped.

Widget kind dispatch handles two LLM output formats:
- `{"kind": "widget", "widget_kind": "graph_explore", "spec": {…}}` — explicit
- `{"kind": "graph_explore", "spec": {…}}` — LLM places subtype directly in `kind`

Both are normalised to `{"kind": "widget", "widget_kind": "<subtype>", …}` before returning.

### Model selection

Uses `llm_story_model` first, falls back to `llm_model_strong`.  
Uses `llm_story_api_key` first, falls back to `llm_api_key`.  
Two attempts are made before returning `{"kind": "unavailable", "reason": "…"}`.

### Gate

Same `Gate(enabled, allowed)` pattern as `/explain` and `/explain/story`:
- `explain_enabled` feature flag
- guests: `explain_guests_enabled`  
- registered students: `has_scope(db, student_id, "ai_processing")`

---

## Consequences

- The endpoint is stateless: no DB write, no job queue. One HTTP call per student request.
- Block JSON is consumed entirely client-side. The frontend is responsible for rendering each `kind`.
- `widget` blocks require frontend components; shipped without them the blocks are silently skipped or shown as raw JSON — both are acceptable for the current phase.
- `check` blocks include a `hint_ladder` that the frontend can reveal progressively.
- The `{scope_rule}` injection approach means the prompt file reads as natural text — future owners editing the prompt do not need to escape braces.

---

## Files changed

| File | Change |
|---|---|
| `app/explain/prompts/lesson.v1.md` | New prompt file |
| `app/explain/service_lesson.py` | New service: `build_lesson`, `clean_lesson`, per-block cleaners |
| `app/explain/router.py` | New endpoint `POST /explain/lesson` |
