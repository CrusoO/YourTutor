"""Post-checks for LLM output (ARCHITECTURE section 14). Pure.

Order: schema, leak, grounding/citation, length, tone, moderation, language. The first failure
wins. The caller regenerates once and then falls back to the authored text.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.content.leak import hint_leaks_answer
from app.llm.prompt import PromptContext
from app.llm.purposes import Purpose
from app.llm.rules import LlmRules, default_rules
from app.registries.loaders import load_locales_config

GRADES = ("good", "partly", "not_yet")
GRADE_LINE = re.compile(r"^GRADE:\s*(\w+)\s*$")
NUMBER = re.compile(r"\d+(?:\.\d+)?")
CITATION = re.compile(r"\[([^\[\]]+)\]")
MARKDOWN = re.compile(r"^\s*#|\*\*|`|^\s*[-*]\s", re.MULTILINE)
URL = re.compile(r"https?://|www\.", re.IGNORECASE)
SCRIPT_PREFIX = {"Latn": "LATIN", "Deva": "DEVANAGARI", "Beng": "BENGALI"}
SCRIPT_SHARE = 0.6  # share of letters that must be in the language's script
NUMBER_WORDS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
    "seven": "7", "eight": "8", "nine": "9", "ten": "10", "eleven": "11", "twelve": "12",
    "thirteen": "13", "fourteen": "14", "fifteen": "15", "sixteen": "16", "seventeen": "17",
    "eighteen": "18", "nineteen": "19", "twenty": "20",
}  # fmt: skip


@dataclass(frozen=True)
class Checked:
    ok: bool
    code: str | None = None
    text: str | None = None
    grade: str | None = None


def _fail(code: str) -> Checked:
    return Checked(False, code)


def _parse(ctx: PromptContext, raw: str) -> tuple[str | None, str | None, str | None]:
    """(text, grade, error code)."""
    body = raw.strip()
    if not body:
        return None, None, "schema.empty"
    grade = None
    if ctx.purpose is Purpose.grade_explain_back:
        first, _, rest = body.partition("\n")
        match = GRADE_LINE.match(first.strip())
        if not match or match.group(1) not in GRADES:
            return None, None, "schema.grade"
        grade, body = match.group(1), rest.strip()
        if not body:
            return None, None, "schema.empty"
    if MARKDOWN.search(body) or URL.search(body) or re.search(r"\n\s*\n", body):
        return None, None, "schema.format"
    return body, grade, None


def _spelled_out(text: str) -> str:
    """Replace spelled-out small numbers with digits so 'six' is caught as 6."""
    return re.sub(
        r"\b(" + "|".join(NUMBER_WORDS) + r")\b",
        lambda m: NUMBER_WORDS[m.group(1).lower()],
        text,
        flags=re.IGNORECASE,
    )


def _allowed_text(ctx: PromptContext) -> str:
    parts = [ctx.source, *ctx.glossary.values()]
    parts += [v for k, v in ctx.fields.items() if k != "passage_ids"]
    return " ".join(parts)


def _grounded(ctx: PromptContext, text: str) -> str | None:
    passage_ids = {p.strip() for p in ctx.fields.get("passage_ids", "").split(",") if p.strip()}
    if passage_ids:
        cited = CITATION.findall(text)
        if not cited or any(c.strip() not in passage_ids for c in cited):
            return "grounding.citation"
    allowed = set(NUMBER.findall(_allowed_text(ctx)))
    if any(n not in allowed for n in NUMBER.findall(CITATION.sub("", text))):
        return "grounding.number"
    return None


def _in_script(text: str, language: str) -> bool:
    spec = load_locales_config()[1].get(language)
    prefix = SCRIPT_PREFIX.get(spec.script) if spec else None
    if prefix is None:
        return True  # no script rule for this language
    letters = [c for c in text if unicodedata.category(c)[0] in "LM"]
    if not letters:
        return True
    ours = sum(1 for c in letters if unicodedata.name(c, "").startswith(prefix))
    return ours / len(letters) >= SCRIPT_SHARE


def run_checks(ctx: PromptContext, raw: str, rules: LlmRules | None = None) -> Checked:
    from app.content.copy import BANNED_PRAISE_WORDS  # lazy: copy imports the orchestrator

    rules = rules or default_rules()
    text, grade, error = _parse(ctx, raw)
    if error or text is None:
        return _fail(error or "schema.empty")
    if ctx.forbidden_answer and (
        hint_leaks_answer(text, ctx.forbidden_answer)
        or hint_leaks_answer(_spelled_out(text), ctx.forbidden_answer)
    ):
        return _fail("leak")
    grounding = _grounded(ctx, text)
    if grounding:
        return _fail(grounding)
    if len(text.split()) > ctx.band.max_words:
        return _fail("length")
    lowered = text.lower()
    if any(word in lowered for word in BANNED_PRAISE_WORDS):
        return _fail("tone.praise")
    if any(phrase in lowered for phrase in rules.shaming_phrases):
        return _fail("tone.shaming")
    if any(re.search(rf"\b{re.escape(term)}\b", lowered) for term in rules.blocked_terms):
        return _fail("moderation")
    if not _in_script(text, ctx.language):
        return _fail("language")
    return Checked(True, None, text, grade)
