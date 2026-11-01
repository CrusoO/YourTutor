"""The in-depth explanation: a typed question taught from first principles (one model call).

The question is cleaned and screened with the same lists as Study Mode Ask before any model is
called, personal details are removed, and the question text is never stored or logged here. Without
a key, a model name or consent the caller gets `unavailable` and nothing is sent anywhere.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from app.ask.config import load_safety, message
from app.ask.guard import clean_question, screen
from app.config import key_for_model, settings
from app.explain.mathtext import plain_math
from app.llm.prompt import STUDENT_TAG, Prompt
from app.llm.provider import ProviderError, ProviderResult
from app.llm.rules import default_rules

PROMPT_FILE = Path(__file__).parent / "prompts" / "v1.md"
MAX_QUESTION_CHARS = 300
PROMPT_VERSION = "explain/v1"
MAX_TOKENS = 6000
REQUEST_TIMEOUT_S = 90
MAX_HTTP_ATTEMPTS = 3
MIN_SECTIONS = 3
LANGUAGES = ("en", "hi")

HEADINGS: dict[str, tuple[str, ...]] = {
    "en": (
        "The idea in one line",
        "Start from first principles",
        "Build it up, step by step",
        "A worked example",
        "Common mistakes",
        "Check yourself",
        "In short",
    ),
    "hi": (
        "एक पंक्ति में विचार",
        "बुनियादी सिद्धांतों से शुरुआत",
        "चरण-दर-चरण आगे बढ़ें",
        "एक हल किया हुआ उदाहरण",
        "आम गलतियाँ",
        "खुद जाँचें",
        "संक्षेप में",
    ),
}
OUT_OF_SCOPE = "OUT_OF_SCOPE"
MAX_ATTEMPTS = (
    2  # the model sometimes returns an unusable reply: one more try, as the shared gateway does
)

# Anyone not signed in may ask about any topic worth learning; only harm is refused.
# A signed-in student stays inside the school syllabus, as the rest of the app does.
OPEN_SCOPE = (
    "Explain any topic a curious student might want to learn about, in any subject, "
    "simplified for a student in classes 6 to 12. Refuse only requests that are harmful, "
    "sexual, hateful, ask for personal advice or help with a crime: for those reply with "
    "exactly {out_of_scope} and nothing else."
)
SYLLABUS_SCOPE = (
    "Teach only topics from a school syllabus (classes 6 to 12) and the ideas they are "
    "built on. If the question is not about that, reply with exactly {out_of_scope} "
    "and nothing else."
)


class Completer(Protocol):
    def complete(self, prompt: Prompt, model: str) -> ProviderResult: ...


# The model setting is "<provider>/<model>", e.g. "openrouter/anthropic/claude-haiku-5.5".
# "anthropic" speaks the native Messages API; the rest speak the OpenAI chat format.
ENDPOINTS: dict[str, str] = {
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    "anthropic": "https://api.anthropic.com/v1/messages",
}


class ExplainProvider:
    """One HTTPS call to the configured provider; a failure carries no reply text.

    `json_mode` asks for a JSON object (dropped if the provider refuses it). A rate-limit answer
    (429) or a server error is retried after a short wait, as the provider asks."""

    def __init__(
        self, json_mode: bool = False, max_tokens: int = MAX_TOKENS, api_key: str | None = None
    ) -> None:
        self.json_mode = json_mode
        self.max_tokens = max_tokens
        self.api_key = api_key

    def complete(self, prompt: Prompt, model: str) -> ProviderResult:
        provider, _, name = model.partition("/")
        url = ENDPOINTS.get(provider)
        if url is None or not name:
            raise ProviderError("unknown provider")
        api_key = self.api_key or key_for_model(model)
        is_anthropic = provider == "anthropic"

        if is_anthropic:
            # Native Anthropic Messages API — different body shape, different headers, no json_mode.
            body: dict[str, Any] = {
                "model": name,
                "max_tokens": self.max_tokens,
                "system": prompt.system,
                "messages": [{"role": "user", "content": prompt.user}],
            }
            req_headers: dict[str, str] = {
                "Content-Type": "application/json",
                "User-Agent": "yourtutor-api/0.1",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            }
        else:
            body = {
                "model": name,
                "messages": [
                    {"role": "system", "content": prompt.system},
                    {"role": "user", "content": prompt.user},
                ],
                "max_tokens": self.max_tokens,
            }
            if provider == "groq":
                body["reasoning_effort"] = "low"  # reasoning tokens share the answer's budget
            req_headers = {
                "Content-Type": "application/json",
                "User-Agent": "yourtutor-api/0.1",
                "Authorization": f"Bearer {api_key}",
            }

        # Anthropic has no response_format; its prompts already ask for JSON by text.
        use_json = self.json_mode and not is_anthropic
        retry_codes = (429, 500, 502, 503, 504, 529) if is_anthropic else (429, 500, 502, 503, 504)
        last: Exception | None = None
        for attempt in range(MAX_HTTP_ATTEMPTS):
            payload = dict(body)
            if use_json:
                payload["response_format"] = {"type": "json_object"}
            request = urllib.request.Request(  # noqa: S310  https URLs from the table above only
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=req_headers,
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S) as response:  # noqa: S310
                    data = json.loads(response.read().decode("utf-8"))
                usage = data.get("usage") or {}
                if is_anthropic:
                    # content may have a leading "thinking" block — find the first "text" block.
                    content_blocks = data.get("content") or []
                    text_block: dict[str, Any] = next(
                        (b for b in content_blocks if b.get("type") == "text"), {}
                    )
                    text = str(text_block.get("text") or "")
                    tokens_in = int(usage.get("input_tokens") or 0)
                    tokens_out = int(usage.get("output_tokens") or 0)
                else:
                    text = str(data["choices"][0]["message"].get("content") or "")
                    tokens_in = int(usage.get("prompt_tokens") or 0)
                    tokens_out = int(usage.get("completion_tokens") or 0)
                return ProviderResult(text=text, tokens_in=tokens_in, tokens_out=tokens_out)
            except urllib.error.HTTPError as exc:
                last = exc
                if exc.code == 400 and use_json:
                    use_json = False  # this model does not take a JSON mode: ask in words only
                    continue
                if exc.code not in retry_codes or attempt == MAX_HTTP_ATTEMPTS - 1:
                    break
                wait = exc.headers.get("retry-after") if exc.headers else None
                try:
                    seconds = float(wait) if wait else 15.0 * (attempt + 1)
                except ValueError:
                    seconds = 15.0 * (attempt + 1)
                time.sleep(min(max(seconds, 1.0), 60.0))
            except Exception as exc:  # noqa: BLE001  any provider failure becomes "unavailable"
                last = exc
                break
        raise ProviderError(type(last).__name__ if last else "ProviderError") from last


OUT_OF_SCOPE_MESSAGE = {
    "en": "I cannot help with that one. Try asking about something you would like to learn.",
    "hi": "इसमें मैं मदद नहीं कर सकता। कुछ ऐसा पूछें जिसे आप सीखना चाहते हैं।",
}
HEADING_LINE = re.compile(r"^\s{0,3}#{1,3}\s+(.*?)\s*#*\s*$")


def build_prompt(text: str, language: str, restricted: bool = False) -> Prompt:
    headings = HEADINGS[language]
    spoken = "Hindi, in Devanagari script" if language == "hi" else "simple English"
    outline = "\n".join(f"## {h}" for h in headings)
    system = (
        PROMPT_FILE.read_text(encoding="utf-8")
        .strip()
        .format(
            spoken=spoken,
            outline=outline,
            scope_rule=(SYLLABUS_SCOPE if restricted else OPEN_SCOPE).format(
                out_of_scope=OUT_OF_SCOPE
            ),
        )
    )
    cleaned = STUDENT_TAG.sub("", text)
    user = f"<student_text>\n{cleaned}\n</student_text>\n\nExplain this idea in depth."
    return Prompt(system=system, user=user, version=PROMPT_VERSION, max_words=650)


def parse_sections(text: str) -> tuple[str, list[dict[str, str]]]:
    """A title and the sections of a markdown answer."""
    title = ""
    sections: list[dict[str, str]] = []
    heading: str | None = None
    body: list[str] = []

    def flush() -> None:
        content = "\n".join(body).strip()
        if heading is not None and content:
            sections.append({"heading": heading, "body": content})

    for line in text.splitlines():
        match = HEADING_LINE.match(line)
        if match and line.lstrip().startswith("##"):
            flush()
            heading, body = match.group(1).strip(), []
        elif match and not title and not sections and heading is None:
            title = match.group(1).strip()
        else:
            body.append(line)
    flush()
    return title, sections


@dataclass(frozen=True)
class Gate:
    enabled: bool
    allowed: bool  # consent, or the owner's guests switch


def unavailable(reason: str) -> dict[str, Any]:
    return {"kind": "unavailable", "reason": reason}


def precheck(
    question: str,
    language: str,
    gate: Gate,
    provider: Completer | None = None,
    model: str | None = None,
) -> tuple[dict[str, Any] | None, str, str]:
    """What must hold before any model is called: the feature is on, the question is clean and
    safe, there is consent, a key and a model. Returns an answer to give at once (or None), the
    cleaned question and the model to use."""
    if not gate.enabled:
        return unavailable("off"), "", ""
    cleaned = clean_question(question, MAX_QUESTION_CHARS)
    if cleaned.empty:
        return {"kind": "empty"}, "", ""
    if cleaned.too_long:
        refusal = {
            "kind": "refused",
            "reason": "too_long",
            "message": message("too_long", language),
        }
        return refusal, "", ""
    verdict = screen(cleaned.text, load_safety(language))
    if verdict.kind == "distress":
        return {"kind": "distress", "message": message("distress", language)}, "", ""
    if verdict.kind != "ok":
        refusal = {
            "kind": "refused",
            "reason": verdict.kind,
            "message": message("refused", language),
        }
        return refusal, "", ""
    if not gate.allowed:
        return unavailable("consent"), "", ""
    chosen = model if model is not None else settings.llm_model_strong
    if provider is None and not (chosen and key_for_model(chosen)):
        return unavailable("no_key"), "", ""
    return None, cleaned.text, chosen


def explain(
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
    pii_removed = text_in != " ".join(question.split())
    outcome = unavailable("provider_error")
    for _ in range(MAX_ATTEMPTS):
        try:
            reply = (provider or ExplainProvider()).complete(
                build_prompt(text_in, language, restricted), chosen
            )
        except ProviderError:
            outcome = unavailable("provider_error")
            continue
        text = reply.text.strip()
        if text.upper().startswith(OUT_OF_SCOPE):
            return {"kind": "out_of_scope", "message": OUT_OF_SCOPE_MESSAGE[language]}
        lowered = text.lower()
        terms = default_rules().blocked_terms
        if any(re.search(rf"\b{re.escape(term)}\b", lowered) for term in terms):
            outcome = unavailable("checks")
            continue
        title, sections = parse_sections(plain_math(text))
        if len(sections) < MIN_SECTIONS:
            outcome = unavailable("checks")
            continue
        break
    else:
        return outcome
    return {
        "kind": "explanation",
        "title": title,
        "sections": sections,
        "pii_removed": pii_removed,
    }
