"""A small in-memory cache of finished lessons, so a topic asked twice costs one model call.

A lesson depends only on the question, the language, the scope and the model, never on who asks,
so it is safe to share between students. The consent gate and the safety screen run before the
cache is read, so a refused question is never served from it. Nothing is kept across a restart.
"""

from __future__ import annotations

import copy
import json
import re
import threading
import time
from collections import OrderedDict
from typing import Any

MAX_ENTRIES = 256
TTL_SECONDS = 24 * 60 * 60

_lock = threading.Lock()
_entries: OrderedDict[str, tuple[float, dict[str, Any]]] = OrderedDict()


def key_for(
    *,
    version: str,
    model: str,
    language: str,
    restricted: bool,
    part: str,
    question: str,
    opening: list[dict[str, Any]] | None,
) -> str:
    """Same topic typed with different spacing or case shares one entry."""
    topic = re.sub(r"\s+", " ", question).strip().casefold()
    shown = json.dumps(opening, sort_keys=True, ensure_ascii=False) if opening else ""
    return "\x1f".join([version, model, language, str(restricted), part, topic, shown])


def get(key: str, now: float | None = None) -> dict[str, Any] | None:
    moment = time.monotonic() if now is None else now
    with _lock:
        hit = _entries.get(key)
        if hit is None:
            return None
        stored_at, value = hit
        if moment - stored_at > TTL_SECONDS:
            del _entries[key]
            return None
        _entries.move_to_end(key)
        return copy.deepcopy(value)


def put(key: str, value: dict[str, Any], now: float | None = None) -> None:
    moment = time.monotonic() if now is None else now
    with _lock:
        _entries[key] = (moment, copy.deepcopy(value))
        _entries.move_to_end(key)
        while len(_entries) > MAX_ENTRIES:
            _entries.popitem(last=False)


def clear() -> None:
    with _lock:
        _entries.clear()
