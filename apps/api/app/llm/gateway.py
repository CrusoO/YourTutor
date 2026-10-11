"""The LLM gateway (ARCHITECTURE section 14).

Gate, build the prompt, call the provider, post-check, regenerate once, then fall back to the
authored text. It never raises for a provider or content problem: the student always gets an
authored reply at worst. No calls in diagnostic or checkpoint sessions, without the
`ai_processing` consent, or without an API key.
"""

from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import LlmCallRow
from app.llm.checks import run_checks
from app.llm.prompt import Prompt, PromptContext, build_prompt
from app.llm.provider import LiteLLMProvider, Provider, ProviderError
from app.llm.purposes import Purpose

NO_LLM_SESSIONS = frozenset({"diagnostic", "checkpoint"})
FAST_PURPOSES = frozenset({Purpose.personalise_hint, Purpose.encourage})
MAX_ATTEMPTS = 2  # one call, then one regeneration


@dataclass(frozen=True)
class Gate:
    session_type: str
    has_ai_processing: bool
    has_api_key: bool


def skip_reason(gate: Gate) -> str | None:
    if gate.session_type in NO_LLM_SESSIONS:
        return "mode"
    if not gate.has_ai_processing:
        return "consent"
    if not gate.has_api_key:
        return "no_key"
    return None


@dataclass
class LlmResult:
    text: str
    source: str  # "llm" or "authored"
    outcome: str  # llm | fallback | skipped
    prompt_version: str
    grade: str | None = None
    llm_called: bool = False
    attempts: int = 0
    failure_codes: list[str] = field(default_factory=list)
    skip_reason: str | None = None
    model: str = ""
    latency_ms: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    sampled: bool = False


class Gateway:
    def __init__(
        self,
        provider: Provider | None = None,
        *,
        sample_rate: float | None = None,
        rng: random.Random | None = None,
        models: dict[str, str] | None = None,
    ) -> None:
        self.provider: Provider = provider or LiteLLMProvider()
        self.sample_rate = settings.llm_review_sample_rate if sample_rate is None else sample_rate
        self.rng = rng or random.Random()
        self.models = models or {
            "fast": settings.llm_model_fast,
            "strong": settings.llm_model_strong,
        }

    def _model(self, purpose: Purpose) -> str:
        return self.models["fast" if purpose in FAST_PURPOSES else "strong"]

    def generate(self, ctx: PromptContext, *, fallback: str, gate: Gate) -> LlmResult:
        prompt = build_prompt(ctx)
        reason = skip_reason(gate)
        if reason:
            return LlmResult(
                text=fallback,
                source="authored",
                outcome="skipped",
                prompt_version=prompt.version,
                skip_reason=reason,
            )
        model = self._model(ctx.purpose)
        out = LlmResult(
            text=fallback,
            source="authored",
            outcome="fallback",
            prompt_version=prompt.version,
            llm_called=True,
            model=model,
        )
        current: Prompt = prompt
        started = time.perf_counter()
        for _ in range(MAX_ATTEMPTS):
            out.attempts += 1
            try:
                reply = self.provider.complete(current, model)
            except ProviderError:
                out.failure_codes.append("provider_error")
                current = _retry(prompt, "provider_error")
                continue
            out.tokens_in += reply.tokens_in
            out.tokens_out += reply.tokens_out
            checked = run_checks(ctx, reply.text)
            if checked.ok and checked.text is not None:
                out.text, out.source, out.outcome = checked.text, "llm", "llm"
                out.grade = checked.grade
                break
            out.failure_codes.append(checked.code or "unknown")
            current = _retry(prompt, checked.code or "unknown")
        out.latency_ms = int((time.perf_counter() - started) * 1000)
        out.sampled = self.rng.random() < self.sample_rate
        return out


def _retry(prompt: Prompt, code: str) -> Prompt:
    """The same prompt plus the rule that failed (never the failed text, which may leak)."""
    note = f"Your previous reply broke a rule: {code}. Write a new reply that follows every rule."
    return Prompt(
        system=prompt.system,
        user=f"{prompt.user}\n\n{note}",
        version=prompt.version,
        max_words=prompt.max_words,
    )


def record_call(
    db: Session, result: LlmResult, ctx: PromptContext, *, session_id: uuid.UUID | None
) -> LlmCallRow:
    """Log the call. No student text: the reply is kept only when sampled for review."""
    keep = result.sampled and result.source == "llm"
    row = LlmCallRow(
        id=uuid.uuid4(),
        created_at=datetime.now(UTC),
        session_id=session_id,
        purpose=ctx.purpose.value,
        prompt_version=result.prompt_version,
        model=result.model,
        band_id=ctx.band.id,
        language=ctx.language,
        outcome=result.outcome,
        skip_reason=result.skip_reason,
        attempts=result.attempts,
        failure_codes=list(result.failure_codes),
        latency_ms=result.latency_ms,
        tokens_in=result.tokens_in,
        tokens_out=result.tokens_out,
        sampled=result.sampled,
        output_text=result.text if keep else None,
        review_status="pending" if keep else None,
    )
    db.add(row)
    return row
