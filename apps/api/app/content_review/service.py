"""Review state for content items: who decided what on which content hash.

Pure rules, no HTTP. An item is approved by review when at least `REQUIRED_APPROVALS` distinct
reviewers approved its CURRENT content hash and nobody rejected it or asked for a fix on that hash.
Editing the item changes the hash, so earlier decisions stop counting (they stay in the table).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.content.locale import is_missing_translation
from app.content.review import reviewer_allowlist
from app.content.schema import ContentStatus, Item
from app.content.signatures import item_content_hash
from app.content.stem_solve import check_item_stem_answer
from app.content.validator import load_bundle
from app.db.models import ContentReviewRow

REQUIRED_APPROVALS = 2


def reviewer_allowed(label: str) -> bool:
    """May this account label review?

    The allowlist (`REVIEWER_ALLOWLIST`, e.g. `curriculum.lead,teacher.demo`) is by label. A staff
    account's label is its email address; the part before the `@` also counts. The allowlist is
    enforced only when it is set explicitly: its built-in default names demo accounts, which would
    lock every real teacher out. With it unset, any teacher or admin account may review.
    """
    if not settings.reviewer_allowlist.strip():
        return True
    allowed = reviewer_allowlist()
    return label in allowed or label.split("@", 1)[0] in allowed


def reviews_for(db: Session, item_id: str, content_hash: str) -> list[ContentReviewRow]:
    return list(
        db.scalars(
            select(ContentReviewRow)
            .where(
                ContentReviewRow.item_id == item_id,
                ContentReviewRow.content_hash == content_hash,
            )
            .order_by(ContentReviewRow.created_at, ContentReviewRow.id)
        )
    )


@dataclass(frozen=True)
class Tally:
    approvals: int
    blocked: bool  # a reject or fix stands on this hash

    @property
    def ready(self) -> bool:
        return self.approvals >= REQUIRED_APPROVALS and not self.blocked


def tally(rows: list[ContentReviewRow]) -> Tally:
    return Tally(
        approvals=len({r.reviewer_id for r in rows if r.decision == "approve"}),
        blocked=any(r.decision in ("reject", "fix") for r in rows),
    )


def record_decision(
    db: Session,
    *,
    item_id: str,
    content_hash: str,
    reviewer_id: uuid.UUID,
    reviewer_label: str,
    decision: str,
    note: str | None,
    now: datetime,
) -> ContentReviewRow:
    """Insert, or replace this reviewer's earlier decision on the same hash."""
    row = db.scalar(
        select(ContentReviewRow).where(
            ContentReviewRow.item_id == item_id,
            ContentReviewRow.content_hash == content_hash,
            ContentReviewRow.reviewer_id == reviewer_id,
        )
    )
    if row is None:
        row = ContentReviewRow(
            id=uuid.uuid4(),
            item_id=item_id,
            content_hash=content_hash,
            reviewer_id=reviewer_id,
        )
        db.add(row)
    row.reviewer_label = reviewer_label
    row.decision = decision
    row.note = note
    row.created_at = now
    db.flush()
    return row


def hindi_texts(root: Path, item_id: str) -> dict[str, Any]:
    """The Hindi (`hi`) strings an item's YAML carries, if any. The Item schema has no `hi` field,
    so they are read from the file; empty when absent or still a placeholder."""
    for path in (root / "items").rglob("*.yaml"):
        raw = path.read_text(encoding="utf-8")
        if f"id: {item_id}" not in raw:
            continue
        data = yaml.safe_load(raw)
        if not isinstance(data, dict) or data.get("id") != item_id:
            continue

        def pick(node: Any) -> str | None:
            value = node.get("hi") if isinstance(node, dict) else None
            return None if is_missing_translation(value) else str(value)

        options = {
            str(o.get("id")): pick(o) for o in data.get("options") or [] if isinstance(o, dict)
        }
        return {
            "stem": pick(data.get("stem")),
            "options": {k: v for k, v in options.items() if v},
        }
    return {"stem": None, "options": {}}


def verification(item: Item) -> dict[str, str]:
    """Is the authored answer confirmed by solving the item? Never raises."""
    try:
        outcome = check_item_stem_answer(item)
    except Exception as exc:  # noqa: BLE001 - a broken spec must show on the card, not 500
        return {"state": "mismatch", "detail": f"could not check: {exc}"}
    if outcome is None:
        return {"state": "verified", "detail": "the solver reaches this answer"}
    if outcome in ("teacher", "manual"):
        return {"state": "unchecked", "detail": "not machine-checkable: read it carefully"}
    return {"state": "mismatch", "detail": outcome}


def _wrong_options(item: Item, labels: dict[str, str]) -> list[dict[str, Any]]:
    named: dict[str, list[str]] = {}
    for rule in item.misconception_rules:
        for answer in rule.when_answer_equals:
            named.setdefault(answer, []).append(labels.get(rule.id, rule.id))
    if item.options:
        wrong = [(o.id, o.en) for o in item.options if o.id != item.answer.sympy]
    else:
        wrong = [(answer, answer) for answer in named if answer != item.answer.sympy]
    return [
        {"answer": ident, "text": text, "misconceptions": named.get(ident, [])}
        for ident, text in wrong
    ]


def load_items(root: Path) -> tuple[list[Item], dict[str, str]]:
    """Items in id order and misconception id to English title. Reads only: `validate_path`
    would rewrite stale files, and the API must never write the repo."""
    bundle = load_bundle(root)
    labels = {m.id: m.title.en for m in bundle.misconceptions}
    return sorted(bundle.items, key=lambda i: i.id), labels


def card(
    db: Session, root: Path, item: Item, labels: dict[str, str], me: uuid.UUID
) -> dict[str, Any]:
    digest = item_content_hash(item)
    rows = reviews_for(db, item.id, digest)
    counted = tally(rows)
    mine = next((r for r in rows if r.reviewer_id == me), None)
    return {
        "id": item.id,
        "skill_ids": item.skill_ids,
        "type": item.type.value,
        "pool": item.pool.value,
        "status": item.status.value,
        "content_hash": digest,
        "stem": item.stem.en,
        "answer": item.answer.sympy,
        "answer_text": next((o.en for o in item.options if o.id == item.answer.sympy), None),
        "verification": verification(item),
        "wrong_options": _wrong_options(item, labels),
        "solution_steps": [s.en for s in item.solution_steps],
        "hints": [h.en for h in sorted(item.hints, key=lambda h: h.level)],
        "hindi": hindi_texts(root, item.id),
        "approvals": counted.approvals,
        "approvals_needed": REQUIRED_APPROVALS,
        "blocked": counted.blocked,
        "notes": [
            {"reviewer": r.reviewer_label, "decision": r.decision, "note": r.note}
            for r in rows
            if r.note
        ],
        "my_decision": (
            {"decision": mine.decision, "note": mine.note} if mine is not None else None
        ),
    }


def is_draft(item: Item) -> bool:
    return item.status == ContentStatus.draft
