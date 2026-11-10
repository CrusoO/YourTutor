"""The in-depth explanation: a typed question taught from first principles (one model call).

The question is cleaned and screened with the same lists as Study Mode Ask before any model is
called, personal details are removed, and the question text is never stored or logged here. Without
a key, a model name or consent the caller gets `unavailable` and nothing is sent anywhere.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from app.ask.config import load_safety, message
from app.ask.guard import clean_question, screen
from app.config import key_for_model, settings
from app.explain.mathtext import plain_math
from app.llm import anthropic_client
from app.llm.prompt import STUDENT_TAG, Prompt
from app.llm.provider import ProviderError, ProviderResult, claude_model_name
from app.llm.rules import default_rules
from app.safety import detection_from_verdict, distress_reply

PROMPT_FILE = Path(__file__).parent / "prompts" / "v1.md"
MAX_QUESTION_CHARS = 300
PROMPT_VERSION = "explain/v1"
MAX_TOKENS = 6000
REQUEST_TIMEOUT_S = 90
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


class ExplainProvider:
    """One call to Claude through the SDK; a failure carries no reply text.

    The model setting is "anthropic/<model>"; any other name is a ProviderError. `json_mode` is
    kept for the callers that ask for JSON: the prompts say so in words, the SDK has no switch."""

    def __init__(
        self,
        json_mode: bool = False,
        max_tokens: int = MAX_TOKENS,
        api_key: str | None = None,
        thinking_off: bool = False,
    ) -> None:
        self.json_mode = json_mode
        self.max_tokens = max_tokens
        self.api_key = api_key
        # Skips the model's hidden thinking: about twice as fast for a short, simple reply.
        self.thinking_off = thinking_off

    def complete(self, prompt: Prompt, model: str) -> ProviderResult:
        name = claude_model_name(model)
        reply = anthropic_client.complete(
            prompt.system,
            [{"role": "user", "content": prompt.user}],
            name,
            self.api_key or key_for_model(model),
            max_tokens=self.max_tokens,
            timeout_s=REQUEST_TIMEOUT_S,
            thinking_off=self.thinking_off,
        )
        return ProviderResult(
            text=reply.text, tokens_in=reply.tokens_in, tokens_out=reply.tokens_out
        )


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
        return distress_reply(detection_from_verdict(verdict), language), "", ""
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
