"""Model providers behind one small interface. Claude (Anthropic) is the only real provider; tests
and the offline evals use `FakeProvider`, so nothing here needs a network or an API key."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.config import ANTHROPIC_PREFIX, key_for_model
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


def claude_model_name(model: str) -> str:
    """The Claude model id inside "anthropic/<model>". Any other name is a configuration error:
    Claude is the only provider, so nothing is routed anywhere else."""
    if not model.startswith(ANTHROPIC_PREFIX) or not model[len(ANTHROPIC_PREFIX) :]:
        raise ProviderError("model_must_be_anthropic")
    return model[len(ANTHROPIC_PREFIX) :]


class AnthropicProvider:
    """Calls Claude through the official SDK (`app.llm.anthropic_client`)."""

    def complete(self, prompt: Prompt, model: str) -> ProviderResult:
        from app.llm import anthropic_client  # imported here: that module imports this one

        name = claude_model_name(model)
        reply = anthropic_client.complete(
            prompt.system,
            [{"role": "user", "content": prompt.user}],
            name,
            key_for_model(model),
            max_tokens=MAX_TOKENS,
            timeout_s=REQUEST_TIMEOUT_S,
        )
        return ProviderResult(
            text=reply.text, tokens_in=reply.tokens_in, tokens_out=reply.tokens_out
        )
