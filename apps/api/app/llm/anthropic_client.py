"""Claude text calls through the official Anthropic SDK.

The one place the app talks to Anthropic's Messages API for the tutor chat and the lessons. The SDK
does the HTTP, the headers, the retries (connection errors, 408/409/429 and 5xx, including 529
"overloaded", with back-off that honours retry-after) and the stream parsing.

Rules this module keeps:
- No `temperature`, `top_p`, `top_k` or assistant prefill (the current models reject them).
- `stop_reason == "refusal"` is a refusal, never an empty answer shown as a reply: `complete`
  returns "" and `stream_text` raises ProviderError("refusal"), so the callers' existing
  "unavailable" handling applies.
- Every failure becomes `ProviderError` carrying only the exception's class name: no request,
  reply text or key is ever put in a message or a log.
- The SDK is imported when a client is first built, so an app that never calls Claude (and the
  tests, which pass a fake client) does not need it installed.
"""

from __future__ import annotations

import functools
from collections.abc import Generator, Sequence
from dataclasses import dataclass
from typing import Any

from app.llm.provider import ProviderError

# One retry after a failure, as the hand-written calls did (two attempts in all).
MAX_RETRIES = 1


@dataclass(frozen=True)
class Reply:
    text: str
    tokens_in: int = 0
    tokens_out: int = 0


@functools.lru_cache(maxsize=4)
def _client(api_key: str, timeout_s: float) -> Any:
    """A reusable SDK client (it keeps its connections open between calls)."""
    try:
        import anthropic
    except ImportError as exc:  # the SDK is in requirements.txt; this is a broken install
        raise ProviderError("sdk_missing") from exc
    return anthropic.Anthropic(api_key=api_key, timeout=timeout_s, max_retries=MAX_RETRIES)


def _request(
    system: str,
    turns: Sequence[dict[str, str]],
    model: str,
    max_tokens: int,
    thinking_off: bool,
) -> dict[str, Any]:
    request: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": list(turns),
    }
    if thinking_off:
        request["thinking"] = {"type": "disabled"}
    return request


def complete(
    system: str,
    turns: Sequence[dict[str, str]],
    model: str,
    api_key: str,
    *,
    max_tokens: int,
    timeout_s: float,
    thinking_off: bool = False,
) -> Reply:
    """One call: the reply's text (text blocks only) and the tokens used. `model` has no provider
    prefix ("claude-haiku-5-5"). A refusal is an empty reply."""
    request = _request(system, turns, model, max_tokens, thinking_off)
    try:
        message = _client(api_key, timeout_s).messages.create(**request)
    except ProviderError:
        raise
    except Exception as exc:  # noqa: BLE001  any SDK or network failure becomes "unavailable"
        raise ProviderError(type(exc).__name__) from exc
    usage = getattr(message, "usage", None)
    tokens_in = int(getattr(usage, "input_tokens", 0) or 0)
    tokens_out = int(getattr(usage, "output_tokens", 0) or 0)
    if message.stop_reason == "refusal":
        return Reply("", tokens_in, tokens_out)
    text = "".join(str(block.text) for block in message.content if block.type == "text")
    return Reply(text, tokens_in, tokens_out)


def stream_text(
    system: str,
    turns: Sequence[dict[str, str]],
    model: str,
    api_key: str,
    *,
    max_tokens: int,
    timeout_s: float,
) -> Generator[str, None, None]:
    """One streamed call: yields the reply's text as it arrives. Raises ProviderError.

    There is no retry once text may have been shown. The caller closes the generator to stop
    reading, which closes the connection.
    """
    request = _request(system, turns, model, max_tokens, False)
    try:
        with _client(api_key, timeout_s).messages.stream(**request) as stream:
            yield from stream.text_stream
            final = stream.get_final_message()
    except ProviderError:
        raise
    except Exception as exc:  # noqa: BLE001  GeneratorExit is not an Exception: closing is clean
        raise ProviderError(type(exc).__name__) from exc
    if final.stop_reason == "refusal":
        raise ProviderError("refusal")
