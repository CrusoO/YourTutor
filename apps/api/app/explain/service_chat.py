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
from collections.abc import Generator
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from app.ask.config import load_safety, message
from app.ask.guard import clean_question, screen
from app.config import key_for_model, settings
from app.conversation.voice import Register, trim_to_words
from app.explain.service import (
    ENDPOINTS,
    REQUEST_TIMEOUT_S,
    Gate,
    unavailable,
)
from app.llm import anthropic_client
from app.llm.prompt import STUDENT_TAG
from app.llm.provider import ProviderError
from app.safety import detection_from_verdict, distress_reply

PROMPT_FILE = Path(__file__).parent / "prompts" / "tutor.v2.md"
PROMPT_VERSION = "tutor/v2"
MAX_TOKENS = 600
MAX_QUESTION_CHARS = 500
MAX_REPLY_CHARS = 1000
MAX_HISTORY_TURNS = 8  # keep at most the last 4 full exchanges (8 messages)
MAX_HTTP_ATTEMPTS = 2
RETRY_CODES = (429, 500, 502, 503, 504)
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


def _register_rule(register: Register | None) -> str:
    """The tone and length asked of the model, from the learner's grade band."""
    if register is None:
        return "Keep every reply short: a few sentences at most."
    tone = f"Tone for this learner: {register.style} " if register.style else ""
    return f"{tone}Keep every reply to {register.max_words} words or fewer."


def _build_system(
    restricted: bool, register: Register | None = None, extra_rule: str | None = None
) -> str:
    scope = SYLLABUS_SCOPE if restricted else OPEN_SCOPE
    text = PROMPT_FILE.read_text(encoding="utf-8").strip()
    text = text.replace("{scope_rule}", scope).replace("{register_rule}", _register_rule(register))
    return f"{text}\n\n{extra_rule}" if extra_rule else text


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


def _turns(history: list[dict[str, Any]], user_message: str) -> list[dict[str, str]]:
    """The conversation so far plus the new question, each message cut to the length limit."""
    turns = [{"role": m["role"], "content": str(m["content"])[:MAX_REPLY_CHARS]} for m in history]
    turns.append({"role": "user", "content": user_message})
    return turns


def _chat_request(
    system: str,
    history: list[dict[str, Any]],
    user_message: str,
    model: str,
    api_key: str,
    *,
    stream: bool = False,
) -> urllib.request.Request:
    """The HTTP request for one OpenAI-style chat call. Claude goes through the SDK instead
    (`app.llm.anthropic_client`). Raises ProviderError for an unknown provider."""
    provider_id, _, name = model.partition("/")
    url = ENDPOINTS.get(provider_id)
    if url is None or not name or provider_id == "anthropic":
        raise ProviderError("unknown provider")

    messages = [{"role": "system", "content": system}, *_turns(history, user_message)]
    body: dict[str, Any] = {"model": name, "messages": messages, "max_tokens": MAX_TOKENS}
    if stream:
        body["stream"] = True
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "yourtutor-api/0.1",
        "Authorization": f"Bearer {api_key}",
    }
    return urllib.request.Request(  # noqa: S310  https URLs from ENDPOINTS table only
        url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST"
    )


def _reply_text(data: dict[str, Any]) -> str:
    """The reply text in an OpenAI-style response; a missing reply is ''."""
    return str(data["choices"][0]["message"].get("content") or "")


def _stream_piece(event: dict[str, Any]) -> str:
    """The text in one OpenAI-style streamed event, or ''."""
    return str(event["choices"][0]["delta"].get("content") or "")


def can_stream(model: str) -> bool:
    """True when this module can stream from the model's provider."""
    provider_id, _, name = model.partition("/")
    return bool(name) and provider_id in ENDPOINTS


def _chat_stream(
    system: str,
    history: list[dict[str, Any]],
    user_message: str,
    model: str,
    api_key: str,
) -> Generator[str, None, None]:
    """One streamed call: yields the reply's text as it arrives. Raises ProviderError.

    There is no retry once text may have been shown; the caller decides what to do on failure.
    The caller closes the generator to stop reading (that closes the connection).
    """
    provider_id, _, name = model.partition("/")
    if provider_id == "anthropic":
        if not name:
            raise ProviderError("unknown provider")
        yield from anthropic_client.stream_text(
            system,
            _turns(history, user_message),
            name,
            api_key,
            max_tokens=MAX_TOKENS,
            timeout_s=REQUEST_TIMEOUT_S,
        )
        return
    request = _chat_request(system, history, user_message, model, api_key, stream=True)
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S) as response:  # noqa: S310
            for raw in response:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    return
                try:
                    piece = _stream_piece(json.loads(payload))
                except (ValueError, KeyError, IndexError, TypeError, AttributeError):
                    continue
                if piece:
                    yield piece
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(type(exc).__name__) from exc


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
    if provider_id == "anthropic":
        if not name:
            raise ProviderError("unknown provider")
        return anthropic_client.complete(
            system,
            _turns(history, user_message),
            name,
            api_key,
            max_tokens=MAX_TOKENS,
            timeout_s=REQUEST_TIMEOUT_S,
        ).text
    last: Exception | None = None
    for attempt in range(MAX_HTTP_ATTEMPTS):
        request = _chat_request(system, history, user_message, model, api_key)
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S) as response:  # noqa: S310
                data = json.loads(response.read().decode("utf-8"))
            return _reply_text(data)
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code not in RETRY_CODES or attempt == MAX_HTTP_ATTEMPTS - 1:
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


@dataclass(frozen=True)
class ChatCall:
    """Everything needed to ask the model, once the student's message has passed every check."""

    system: str
    history: list[dict[str, Any]]
    user_message: str
    model: str
    api_key: str
    language: str
    register: Register | None = None

    def with_rule(self, rule: str | None) -> ChatCall:
        """The same call with one more instruction added to the system prompt."""
        return self if not rule else replace(self, system=f"{self.system}\n\n{rule}")


def prepare_chat(
    question: str,
    language: str,
    history: list[dict[str, Any]],
    gate: Gate,
    model: str | None = None,
    restricted: bool = False,
    register: Register | None = None,
    extra_rule: str | None = None,
) -> ChatCall | dict[str, Any]:
    """Screen the student's message. Returns the reply to give at once (off, empty, refused,
    distress, no consent, no key) or the `ChatCall` to send to the model. No model is called."""
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
        return distress_reply(detection_from_verdict(verdict), language)
    if verdict.kind != "ok":
        return {"kind": "refused", "reason": verdict.kind, "message": message("refused", language)}

    if not gate.allowed:
        return unavailable("consent")

    chosen = model or settings.llm_model_strong
    api_key = key_for_model(chosen) if chosen else ""
    if not chosen or not api_key:
        return unavailable("no_key")

    text_in = STUDENT_TAG.sub("", cleaned.text)
    lang_note = "Reply in Hindi (Devanagari script). " if language == "hi" else ""
    user_msg = f"<student_text>\n{text_in}\n</student_text>" + (
        f"\n\n{lang_note}" if lang_note else ""
    )
    return ChatCall(
        system=_build_system(restricted, register, extra_rule),
        history=_trim_history(history),
        user_message=user_msg,
        model=chosen,
        api_key=api_key,
        language=language,
        register=register,
    )


def finish_text(text: str, register: Register | None) -> str:
    """The reply as the student sees it: the band's word limit, cut at a sentence end, then a
    hard character cap as a last guard."""
    text = text.strip()
    if register is not None:
        text = trim_to_words(text, register.max_words)
    if len(text) > MAX_REPLY_CHARS:
        text = text[:MAX_REPLY_CHARS].rsplit(" ", 1)[0] + "…"
    return text


def complete_chat(call: ChatCall) -> dict[str, Any]:
    """Ask the model once and return the finished reply (or an `unavailable` result)."""
    try:
        text = _chat_complete(
            call.system, call.history, call.user_message, call.model, call.api_key
        )
    except ProviderError:
        return unavailable("provider_error")
    text = finish_text(text, call.register)
    if not text:
        return unavailable("checks")
    return {"kind": "reply", "text": text, "language": call.language}


def build_chat(
    question: str,
    language: str,
    history: list[dict[str, Any]],
    gate: Gate,
    model: str | None = None,
    restricted: bool = False,
    register: Register | None = None,
    extra_rule: str | None = None,
) -> dict[str, Any]:
    """Main entry: screen the student's message, call the tutor model, return the reply.

    `register` (from the learner's grade band) sets the tone asked of the model and the word limit
    the reply is cut to; without it the reply is only capped at MAX_REPLY_CHARS. `extra_rule` is one
    more instruction added to the system prompt (the answer guard uses it).
    """
    prepared = prepare_chat(
        question, language, history, gate, model, restricted, register, extra_rule
    )
    if isinstance(prepared, dict):
        return prepared
    return complete_chat(prepared)
