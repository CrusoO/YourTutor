"""Group lessons: what a participant may send back, and what the organiser may see of it.

A teacher or manager shares one fixed lesson by link. Participants may choose to send back how they
did, with no name or account. The organiser then sees where the group is stuck, but only when enough
people answered that nobody can be picked out, and never a count small enough to identify someone.

Pure functions only, so the privacy rules are easy to read and to test.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from typing import Any

# Tunable defaults, not decided values: how many answers before any result is shown, and the
# smallest count shown as a number. Below it the page says "fewer than N".
MIN_PARTICIPANTS = 5
MIN_CELL = 3
MAX_ITEMS = 12
CONFIDENCE = frozenset({"sure", "unsure"})


def new_code() -> str:
    """An unguessable short code for a group link (about 48 bits)."""
    return secrets.token_urlsafe(6)


def norm(text: str) -> str:
    return " ".join(text.split()).casefold()


def participant_key(pepper: str, group_id: uuid.UUID, student_id: uuid.UUID) -> str:
    """A keyed hash of the guest and the group. It stops one person answering twice, cannot be
    turned back into the guest, and differs between groups so nobody is followed across them."""
    return hmac.new(
        pepper.encode(), f"group:{group_id}:{student_id}".encode(), hashlib.sha256
    ).hexdigest()


def questions_of(blocks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """The judged questions of a lesson (multiple-choice predictions and checks), by normalised
    text, with the ideas their wrong options name. Free-text predictions have no right answer, so
    they are left out."""
    found: dict[str, dict[str, Any]] = {}
    for block in blocks:
        kind = block.get("kind")
        if kind == "predict" and not block.get("free_text") and block.get("options"):
            text = str(block.get("prompt") or "")
        elif kind == "check":
            text = str(block.get("question") or "")
        else:
            continue
        if not text.strip():
            continue
        ideas = {
            norm(i): i for i in (block.get("misconceptions") or []) if isinstance(i, str) and i
        }
        found[norm(text)] = {"question": text, "kind": kind, "ideas": ideas}
    return found


def accept_items(blocks: list[dict[str, Any]], items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only what matches this lesson. The page's own wording is never trusted: a question
    must be one the lesson asks, of the same kind, and an idea must be one the lesson names."""
    known = questions_of(blocks)
    accepted: dict[str, dict[str, Any]] = {}
    for item in items[:MAX_ITEMS]:
        question = known.get(norm(str(item.get("question") or "")))
        if question is None or item.get("kind") != question["kind"]:
            continue
        key = norm(question["question"])
        if key in accepted:
            continue
        right = bool(item.get("right"))
        idea = question["ideas"].get(norm(str(item.get("idea") or ""))) if not right else None
        confidence = item.get("confidence")
        accepted[key] = {
            "question": question["question"],
            "kind": question["kind"],
            "right": right,
            "confidence": confidence if confidence in CONFIDENCE else None,
            "idea": idea,
        }
    return list(accepted.values())


def _shown(count: int) -> int | None:
    """A count, or None when it is small enough to point at a person."""
    return count if count >= MIN_CELL else None


def summarise(blocks: list[dict[str, Any]], results: list[list[dict[str, Any]]]) -> dict[str, Any]:
    """Where the group is stuck. Nothing is shown until MIN_PARTICIPANTS people have sent
    results; after that a question needs as many answers, and any count under MIN_CELL is hidden.
    When a count is hidden the matching 'right' figure is never given either, so it cannot be
    worked out by subtraction."""
    people = len(results)
    base: dict[str, Any] = {"participants": people, "minimum": MIN_PARTICIPANTS, "cell": MIN_CELL}
    if people < MIN_PARTICIPANTS:
        return {**base, "ready": False, "questions": []}
    rows: list[dict[str, Any]] = []
    for question in questions_of(blocks).values():
        key = norm(question["question"])
        answers = [
            item for person in results for item in person if norm(item.get("question", "")) == key
        ]
        if len(answers) < MIN_PARTICIPANTS:
            continue
        wrong = [a for a in answers if not a.get("right")]
        sure_wrong = [a for a in wrong if a.get("confidence") == "sure"]
        shown_wrong = _shown(len(wrong))
        ideas: dict[str, int] = {}
        for answer in wrong:
            if answer.get("idea"):
                ideas[answer["idea"]] = ideas.get(answer["idea"], 0) + 1
        rows.append(
            {
                "question": question["question"],
                "kind": question["kind"],
                "answered": len(answers),
                "wrong": shown_wrong,
                # a count of confident errors is only meaningful beside a shown total
                "sure_wrong": _shown(len(sure_wrong)) if shown_wrong is not None else None,
                "ideas": sorted(
                    ({"idea": i, "count": n} for i, n in ideas.items() if n >= MIN_CELL),
                    key=lambda row: (-row["count"], row["idea"]),
                ),
            }
        )
    return {**base, "ready": True, "questions": rows}
