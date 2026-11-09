"""Keep the tutor chat from giving away the answer to the practice item the student is on.

The server, not the browser, decides what the active item is: it reads the student's own session
(`plan.current_item_id`). The answer is withheld until the student has had two hints and made an
attempt, the same rule the practice policy uses for revealing a solution. A reply that contains the
answer (or any accepted form of it) is regenerated once with a stricter instruction; if it still
does, the student gets an authored hint, or the honest "cannot answer" line when none is safe.

Nothing here stores or logs the student's words or the reply text.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.content.leak import hint_leaks_answer
from app.db.models import ItemRow, SessionRow
from app.explain.number_words import words_to_digits
from app.explain.service import unavailable

log = logging.getLogger(__name__)

HINTS_BEFORE_REVEAL = 2

WITHHOLD_RULE = (
    "The student is working on a practice problem. Never state its answer, the value of its "
    "unknown, or a final result. Guide with one question or one small step instead."
)
STRICT_RULE = (
    "Your last reply gave away the answer. Write it again without any final value, and without "
    "any number or expression that equals the answer. Ask one guiding question."
)


@dataclass(frozen=True)
class ActiveItem:
    """What the guard needs to know about the item on the student's screen."""

    item_id: str
    answers: tuple[str, ...]
    hints: tuple[tuple[int, dict[str, str]], ...]
    may_reveal: bool


def load_active_item(
    db: Session, student_id: uuid.UUID, session_id: uuid.UUID | None
) -> ActiveItem | None:
    """The item the student is on in their own open session, or None when there is none.

    A session that is not the caller's is a 404, never a hint that it exists.
    """
    if session_id is None:
        return None
    row = db.get(SessionRow, session_id)
    if row is None or row.student_id != student_id:
        raise HTTPException(status_code=404, detail="session not found")
    if row.ended_at is not None:
        return None
    plan = row.plan or {}
    item_id = plan.get("current_item_id")
    item = db.get(ItemRow, item_id) if item_id else None
    if item is None:
        return None
    answer = item.answer or {}
    answers = tuple(
        dict.fromkeys(
            value
            for value in (answer.get("sympy"), *(answer.get("accept") or ()))
            if isinstance(value, str) and value.strip()
        )
    )
    if not answers:
        return None
    hints = tuple(
        (int(h["level"]), {k: v for k, v in h.items() if isinstance(v, str)})
        for h in (item.hints or [])
        if isinstance(h, dict) and isinstance(h.get("level"), int)
    )
    reached = int(plan.get("hint_level_shown") or 0) >= HINTS_BEFORE_REVEAL
    return ActiveItem(
        item_id=item.id,
        answers=answers,
        hints=hints,
        may_reveal=reached and bool(plan.get("attempt_after_hint2")),
    )


def leaks(text: str, active: ActiveItem) -> bool:
    """True when `text` contains the answer or any accepted form of it, written in digits or as
    an English number word ("twelve")."""
    variants = (text, words_to_digits(text))
    return any(hint_leaks_answer(v, answer) for v in variants for answer in active.answers)


def _authored_hint(active: ActiveItem, language: str) -> str | None:
    """The lowest authored hint (level 1 or 2) that is written and does not leak."""
    for level, texts in sorted(active.hints):
        if level >= HINTS_BEFORE_REVEAL + 1:
            continue
        text = texts.get(language) or texts.get("en") or ""
        if text and not text.startswith("<") and not leaks(text, active):
            return text
    return None


def enforce_no_leak(
    call: Callable[[str | None], dict[str, Any]],
    active: ActiveItem | None,
    language: str,
) -> dict[str, Any]:
    """Run `call(extra_rule)` so that its reply does not give the answer away.

    `call` receives the instruction to add to the model's prompt (or None). With no active item,
    or once the answer may be revealed, the model is called once and nothing is checked.
    """
    if active is None or active.may_reveal:
        return call(None)
    result = call(WITHHOLD_RULE)
    if result.get("kind") != "reply" or not leaks(str(result.get("text", "")), active):
        return result
    log.info("chat reply held back: it contained the answer to %s", active.item_id)
    retry = call(f"{WITHHOLD_RULE} {STRICT_RULE}")
    if retry.get("kind") == "reply" and not leaks(str(retry.get("text", "")), active):
        return retry
    hint = _authored_hint(active, language)
    if hint is None:
        return unavailable("checks")
    return {"kind": "reply", "text": hint, "language": language, "source": "authored_hint"}
