"""Tutor chat: a student asks follow-up questions; the tutor replies with Socratic guidance.

Stateless on the server — the client sends the full message history each time.
History is trimmed to MAX_HISTORY_TURNS (most recent) before the call.
The same gate, safety screen and model selection as /explain apply.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from app.ask.config import load_safety, message
from app.ask.guard import clean_question, screen
from app.config import settings
from app.explain.service import (
    ENDPOINTS,
    REQUEST_TIMEOUT_S,
    Gate,
    unavailable,
)
from app.llm.prompt import STUDENT_TAG
from app.llm.provider import ProviderError

PROMPT_FILE = Path(__file__).parent / "prompts" / "tutor.v1.md"
PROMPT_VERSION = "tutor/v1"
MAX_TOKENS = 600
MAX_QUESTION_CHARS = 500
MAX_REPLY_CHARS = 1000
MAX_HISTORY_TURNS = 8  # keep at most the last 4 full exchanges (8 messages)
MAX_HTTP_ATTEMPTS = 2
LANGUAGES = ("en", "hi")

OPEN_SCOPE = (
    "Help students learn about any topic a curious learner might want to understand. "
    "Refuse only messages that are harmful, sexual, hateful, ask for personal advice or "
    "help with a crime: for those say exactly one sentence: 'I can only help with learning topics.'"
)
SYLLABUS_SCOPE = (
    "Help students understand topics from a school syllabus (classes 6 to 12) and the ideas "
    "they are built on. If a message is not about that, say exactly one sentence: "
    "'I can only help with school subjects.'"
)


def _build_system(restricted: bool) -> str:
    scope = SYLLABUS_SCOPE if restricted else OPEN_SCOPE
    return PROMPT_FILE.read_text(encoding="utf-8").strip().replace("{scope_rule}", scope)


def _trim_history(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only the last MAX_HISTORY_TURNS messages, preserving role alternation."""
    valid = [
        m
        for m in history
        if isinstance(m, dict)
        and m.get("role") in ("user", "assistant")
        and isinstance(m.get("content"), str)
    ]
    return valid[-MAX_HISTORY_TURNS:]


def _chat_complete(
    system: str,
    history: list[dict[str, Any]],
    user_message: str,
    model: str,
    api_key: str,
) -> str:
    """One multi-turn HTTP call to the provider.

    Returns the assistant's text or raises ProviderError.
    """
    provider_id, _, name = model.partition("/")
    url = ENDPOINTS.get(provider_id)
    if url is None or not name:
        raise ProviderError("unknown provider")

    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    for m in history:
        messages.append({"role": m["role"], "content": str(m["content"])[:MAX_REPLY_CHARS]})
    messages.append({"role": "user", "content": user_message})

    body: dict[str, Any] = {
        "model": name,
        "messages": messages,
        "max_tokens": MAX_TOKENS,
    }
    last: Exception | None = None
    for attempt in range(MAX_HTTP_ATTEMPTS):
        request = urllib.request.Request(  # noqa: S310  https URLs from ENDPOINTS table only
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "yourtutor-api/0.1",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S) as response:  # noqa: S310
                data = json.loads(response.read().decode("utf-8"))
            return str(data["choices"][0]["message"].get("content") or "")
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code not in (429, 500, 502, 503, 504) or attempt == MAX_HTTP_ATTEMPTS - 1:
                break
            wait = exc.headers.get("retry-after") if exc.headers else None
            try:
                seconds = float(wait) if wait else 3.0 * (attempt + 1)
            except ValueError:
                seconds = 3.0 * (attempt + 1)
            time.sleep(min(max(seconds, 1.0), 30.0))
        except Exception as exc:  # noqa: BLE001
            last = exc
            break
    raise ProviderError(type(last).__name__ if last else "ProviderError") from last


def build_chat(
    question: str,
    language: str,
    history: list[dict[str, Any]],
    gate: Gate,
    model: str | None = None,
    restricted: bool = False,
) -> dict[str, Any]:
    """Main entry: screen the student's message, call the tutor model, return the reply."""
    language = language if language in LANGUAGES else "en"

    if not gate.enabled:
        return unavailable("off")

    cleaned = clean_question(question, MAX_QUESTION_CHARS)
    if cleaned.empty:
        return {"kind": "empty"}
    if cleaned.too_long:
        return {"kind": "refused", "reason": "too_long", "message": message("too_long", language)}

    verdict = screen(cleaned.text, load_safety(language))
    if verdict.kind == "distress":
        return {"kind": "distress", "message": message("distress", language)}
    if verdict.kind != "ok":
        return {"kind": "refused", "reason": verdict.kind, "message": message("refused", language)}

    if not gate.allowed:
        return unavailable("consent")

    chosen = model or settings.llm_model_strong
    api_key = settings.llm_api_key
    if not chosen or not api_key:
        return unavailable("no_key")

    text_in = STUDENT_TAG.sub("", cleaned.text)
    lang_note = "Reply in Hindi (Devanagari script). " if language == "hi" else ""
    user_msg = f"<student_text>\n{text_in}\n</student_text>" + (
        f"\n\n{lang_note}" if lang_note else ""
    )

    system = _build_system(restricted)
    trimmed_history = _trim_history(history)

    try:
        text = _chat_complete(system, trimmed_history, user_msg, chosen, api_key)
    except ProviderError:
        return unavailable("provider_error")

    text = text.strip()
    if not text:
        return unavailable("checks")

    # truncate to a safe length
    if len(text) > MAX_REPLY_CHARS:
        text = text[:MAX_REPLY_CHARS].rsplit(" ", 1)[0] + "…"

    return {"kind": "reply", "text": text, "language": language}
