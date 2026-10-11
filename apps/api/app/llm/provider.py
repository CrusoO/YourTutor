"""Model providers behind one small interface. LiteLLM is an optional dependency; tests and the
offline evals use `FakeProvider`, so nothing here needs a network or an API key to be tested."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.config import settings
from app.llm.prompt import Prompt

REQUEST_TIMEOUT_S = 20
MAX_TOKENS = 220


class ProviderError(RuntimeError):
    """The provider failed (network, quota, timeout, bad response). Never shown to students."""


@dataclass(frozen=True)
class ProviderResult:
    text: str
    tokens_in: int = 0
    tokens_out: int = 0


class Provider(Protocol):
    def complete(self, prompt: Prompt, model: str) -> ProviderResult: ...


@dataclass
class FakeProvider:
    """Replays scripted replies in order; an exception in the script is raised as the reply."""

    replies: list[str | Exception]
    calls: list[Prompt] = field(default_factory=list)
    models: list[str] = field(default_factory=list)

    def complete(self, prompt: Prompt, model: str) -> ProviderResult:
        self.calls.append(prompt)
        self.models.append(model)
        if not self.replies:
            raise ProviderError("no scripted reply left")
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return ProviderResult(
            text=reply, tokens_in=len(prompt.user.split()), tokens_out=len(reply.split())
        )


class LiteLLMProvider:
    """Calls the model through LiteLLM. Imported lazily so the package stays optional."""

    def complete(self, prompt: Prompt, model: str) -> ProviderResult:
        try:
            import litellm  # type: ignore[import-not-found,unused-ignore]
        except ImportError as exc:
            raise ProviderError("litellm is not installed") from exc
        try:
            response = litellm.completion(
                model=model,
                api_key=settings.llm_api_key,
                messages=[
                    {"role": "system", "content": prompt.system},
                    {"role": "user", "content": prompt.user},
                ],
                max_tokens=MAX_TOKENS,
                timeout=REQUEST_TIMEOUT_S,
            )
            usage = getattr(response, "usage", None)
            return ProviderResult(
                text=str(response.choices[0].message.content or ""),
                tokens_in=int(getattr(usage, "prompt_tokens", 0) or 0),
                tokens_out=int(getattr(usage, "completion_tokens", 0) or 0),
            )
        except Exception as exc:  # noqa: BLE001  any provider failure falls back to authored text
            raise ProviderError(type(exc).__name__) from exc
