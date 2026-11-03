"""The learning card a signed-in learner chose to keep: what they showed in each lesson.

Only the shape the device already keeps (`yt.learning-map.v1`): per lesson a topic, a time and the
first-try result of each question. Everything is cleaned here, because the page is not trusted.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

MAX_LESSONS = 20  # the device keeps the latest 20, so the account does too
MAX_ITEMS = 12
TOPIC_CHARS = 80
IDEA_CHARS = 80
ID_CHARS = 8
KINDS = ("predict", "check")
CONFIDENCE = ("sure", "unsure")


def clean_item(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict) or raw.get("kind") not in KINDS:
        return None
    ident = str(raw.get("id") or "").strip()[:ID_CHARS]
    if not ident or not isinstance(raw.get("right"), bool):
        return None
    right = raw["right"]
    idea = raw.get("idea")
    idea = idea.strip()[:IDEA_CHARS] if isinstance(idea, str) and not right else None
    confidence = raw.get("confidence")
    return {
        "id": ident,
        "kind": raw["kind"],
        "right": right,
        "confidence": confidence if confidence in CONFIDENCE else None,
        "idea": idea or None,
    }


def clean_record(raw: Any) -> tuple[str, datetime, list[dict[str, Any]]] | None:
    """(topic, taken_at, items) or None when this lesson has nothing usable."""
    if not isinstance(raw, dict):
        return None
    topic = " ".join(str(raw.get("topic") or "").split())[:TOPIC_CHARS]
    try:
        taken_at = datetime.fromisoformat(str(raw.get("at")).replace("Z", "+00:00"))
    except ValueError:
        return None
    if taken_at.tzinfo is None or not topic:
        return None
    rows = raw.get("items")
    seen: set[str] = set()
    items: list[dict[str, Any]] = []
    for row in (rows if isinstance(rows, list) else [])[:MAX_ITEMS]:
        item = clean_item(row)
        if item is not None and item["id"] not in seen:
            seen.add(item["id"])
            items.append(item)
    return (topic, taken_at, items) if items else None
