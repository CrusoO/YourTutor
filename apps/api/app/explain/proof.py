"""A signed video source: only text that /explain wrote for this student can become a video.

Without it the video endpoint would voice and render whatever a caller posts. The signature covers
the student, an expiry and the exact text; nothing is stored. The key is EXPLAIN_SIGNING_KEY, or a
random key made when the process starts (a proof then lasts only until a restart).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
import uuid
from typing import Any

from app.config import settings

TTL_SECONDS = 600
TITLE_MAX = 120
HEADING_MAX = 120
BODY_MAX = 2400
_PROCESS_KEY = secrets.token_bytes(32)


def _key() -> bytes:
    return (
        settings.explain_signing_key.encode("utf-8")
        if settings.explain_signing_key
        else _PROCESS_KEY
    )


def canon(value: Any) -> Any:
    """The value with whole floats as ints: JSON sent through a browser turns 1.0 into 1."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, dict):
        return {k: canon(v) for k, v in value.items()}
    if isinstance(value, list):
        return [canon(v) for v in value]
    return value


def _digest(student_id: uuid.UUID, expires: int, source: dict[str, Any]) -> str:
    text = json.dumps(canon(source), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    message = f"{student_id}|{expires}|{text}".encode()
    return hmac.new(_key(), message, hashlib.sha256).hexdigest()


def video_source(title: str, sections: list[dict[str, str]]) -> dict[str, Any]:
    """The engine's source shape, trimmed to its limits."""
    return {
        "title": (title.strip() or "Explanation")[:TITLE_MAX].ljust(3, "."),
        "sections": [
            {"heading": s["heading"].strip()[:HEADING_MAX], "body": s["body"].strip()[:BODY_MAX]}
            for s in sections
            if s["heading"].strip() and s["body"].strip()
        ][:10],
    }


def sign(student_id: uuid.UUID, source: dict[str, Any], now: float | None = None) -> str:
    expires = int((time.time() if now is None else now) + TTL_SECONDS)
    return f"{expires}.{_digest(student_id, expires, source)}"


def verify(
    student_id: uuid.UUID, source: dict[str, Any], proof: str, now: float | None = None
) -> bool:
    stamp, _, signature = proof.partition(".")
    if not stamp.isdigit() or not signature:
        return False
    expires = int(stamp)
    if expires < (time.time() if now is None else now):
        return False
    return hmac.compare_digest(signature, _digest(student_id, expires, source))
