"""Stream a tutor chat reply to the student one sentence at a time.

Why sentence by sentence: a sentence is shown only after it has been checked. The student never sees
half a number or a sentence that gives away the answer, and the reply is cut at the grade band's
word limit while it is being read, so the text on screen is the text that ends up final.

What is NOT streamed: anything decided before a model is called (distress, refusals, a paused chat,
no consent, no key) is one `final` event, built by the same code as the plain route. The caller
also does not stream when the output safety classifier is on, because that check needs the whole
reply first.

This module never touches the database, so it is safe to run inside a streaming response.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

from app.conversation.voice import SENTENCE_END
from app.explain import service_chat
from app.explain.answer_guard import WITHHOLD_RULE, ActiveItem, enforce_no_leak, leaks
from app.explain.service import unavailable
from app.explain.service_chat import MAX_REPLY_CHARS, ChatCall, finish_text
from app.llm.provider import ProviderError

Event = dict[str, Any]
_BLANKS = re.compile(r"\s+")


def delta(text: str) -> Event:
    return {"type": "delta", "text": text}


def final(result: dict[str, Any]) -> Event:
    return {"type": "final", "result": result}


def stream_reply(call: ChatCall, active: ActiveItem | None) -> Iterator[Event]:
    """Yield `delta` events with finished sentences, then one `final` event.

    The `final` result is the one to keep: the client replaces what it has shown with its text.
    It equals the shown text unless the guard had to step in (a leak, a provider failure).
    """
    withhold = active is not None and not active.may_reveal
    first = call.with_rule(WITHHOLD_RULE) if withhold else call
    limit = call.register.max_words if call.register is not None else 0

    released: list[str] = []
    words = 0
    chars = 0
    leaked: str | None = None
    failed = False
    buffer = ""

    def release(sentence: str) -> tuple[bool, Event | None]:
        """Decide one finished sentence. Returns (keep reading, event to send)."""
        nonlocal words, chars, leaked
        sentence = _BLANKS.sub(" ", sentence).strip()
        if not sentence:
            return True, None
        count = len(sentence.split())
        if (limit and words + count > limit) or chars + len(sentence) + 1 > MAX_REPLY_CHARS:
            return False, None  # the reply is long enough: stop reading, keep what is shown
        if withhold and active is not None and leaks(" ".join([*released, sentence]), active):
            leaked = " ".join([*released, sentence])
            return False, None
        text = sentence if not released else f" {sentence}"
        released.append(sentence)
        words += count
        chars += len(text)
        return True, delta(text)

    stream = service_chat._chat_stream(
        first.system, first.history, first.user_message, first.model, first.api_key
    )
    try:
        reading = True
        for piece in stream:
            buffer += piece
            *complete, buffer = SENTENCE_END.split(buffer)
            for sentence in complete:
                reading, event = release(sentence)
                if event is not None:
                    yield event
                if not reading:
                    break
            if not reading:
                break
        if reading and buffer.strip():
            _, event = release(buffer)
            if event is not None:
                yield event
    except ProviderError:
        failed = True
    finally:
        stream.close()  # stop reading: this also closes the connection to the provider

    if leaked is not None:
        text = leaked
    elif failed and not released:
        yield final(unavailable("provider_error"))
        return
    else:
        text = finish_text(" ".join(released), call.register)
    if not text:
        yield final(unavailable("checks"))
        return

    streamed = {"kind": "reply", "text": text, "language": call.language}
    pending = [streamed]

    def ask(rule: str | None) -> dict[str, Any]:
        # The first answer is the one just streamed; any later one is a fresh, unstreamed call.
        return pending.pop() if pending else service_chat.complete_chat(call.with_rule(rule))

    yield final(enforce_no_leak(ask, active, call.language))
