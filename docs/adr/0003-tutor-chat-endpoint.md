# ADR 0003: Socratic Tutor Chat — /explain/chat

**Status:** accepted (2026-10-26)  
**Prompt version:** `tutor/v1`  
**Route:** `POST /explain/chat`

---

## Context

`POST /explain/lesson` generates a structured set of interactive blocks once.  
Students working through those blocks will have follow-up questions: "Why?", "What if…?", "I don't understand the widget."

A separate single-turn Q&A endpoint cannot maintain the thread of a conversation. The experience requires a multi-turn tutor that knows what has been said before, responds briefly, and guides rather than tells.

---

## Decision

Add `POST /explain/chat` — a stateless, multi-turn Socratic tutor backed by a single LLM call.

### Request

```json
{
  "prompt": "why does binding energy per nucleon peak at iron?",
  "language": "en",
  "history": [
    {"role": "user",      "content": "what is nuclear fission"},
    {"role": "assistant", "content": "Let's start from what holds a nucleus together…"}
  ]
}
```

- `history`: at most 20 messages (validated by Pydantic). The server further trims to the last 8 (4 full exchanges) before the call.
- `prompt`: the current student message, max 500 chars.

### Response

```json
{"kind": "reply", "text": "…", "language": "en"}
```

Or a gate/safety signal: `unavailable`, `refused`, `distress`, `empty`.

### Stateless design

The server holds no session state. The client accumulates and sends the full history each request. This matches the existing pattern for `/explain` and `/explain/lesson` (no DB writes per request) and avoids session storage complexity.

### Prompt — `tutor.v1.md`

Owner-written. Instructs the model to:
1. Use the Socratic method — ask one question per reply rather than giving the answer
2. Keep replies to 1–4 sentences
3. Acknowledge partial understanding without confirming errors
4. Redirect prompt-injection attempts with a single sentence

The `{scope_rule}` placeholder is replaced with either the open-scope or syllabus-scope rule via `.replace()`.

### Model

Uses `llm_model_strong` and `llm_api_key`. No story-model override — the strong model is more appropriate for a pedagogic dialogue than a flash model.

### Gate

Same `Gate(enabled, allowed)` as `/explain` and `/explain/lesson`.

---

## Consequences

- Each request re-sends the full history: at 8 messages × ~200 chars each ≈ 1 600 chars extra tokens per call. At `MAX_HISTORY_TURNS = 8` this is bounded and cheap.
- A student who refreshes the page loses history. The frontend must persist it (e.g. `sessionStorage`). The server offers no recovery.
- Replies are capped at 1 000 chars; the model is instructed to stay under 4 sentences. If the model exceeds the cap, the reply is hard-truncated at the last word boundary before 1 000 chars.
- No streaming in this version — response arrives as one JSON object. Adequate for 1–4 sentence replies.

---

## Files changed

| File | Change |
|---|---|
| `app/explain/prompts/tutor.v1.md` | New prompt file |
| `app/explain/service_chat.py` | New service: `build_chat`, `_chat_complete`, `_trim_history` |
| `app/explain/router.py` | `ChatMessage` + `ChatIn` schemas; new endpoint `POST /explain/chat` |
