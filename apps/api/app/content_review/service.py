"""Review state for content items: who decided what on which content hash.

Pure rules, no HTTP. An item is approved by review when at least `REQUIRED_APPROVALS` distinct
reviewers approved its CURRENT content hash and nobody rejected it or asked for a fix on that hash.
Editing the item changes the hash, so earlier decisions stop counting (they stay in the table).
"""

from __future__ import annotations

import hashlib
import os
import re
import threading
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.security import now_utc
from app.auth.service import issue_signin_code
from app.config import settings
from app.content.locale import is_missing_translation
from app.content.review import reviewer_allowlist
from app.content.schema import ContentStatus, Item
from app.content.signatures import item_content_hash
from app.content.stem_solve import check_item_stem_answer
from app.content.validator import load_bundle
from app.content_review import snapshot
from app.db.models import ContentReviewRow, ReviewerCodeIssueRow, UserRow

REQUIRED_APPROVALS = 2
MIN_NOTE_CHARS = 8  # non-space characters, for a fix note or a general note
# three yes / needs-a-fix questions; rows stored before this change hold five and are only read
CHECK_COUNT = 3
MAX_ACTIVE_SECONDS = 7200
SEVERITIES = ("blocker", "must_fix", "nice_to_fix")
REASON_CODES = tuple("123456")  # old rows may hold "0" to "9"; they are read, never rewritten


def desk_enabled() -> bool:
    return settings.reviewer_desk_enabled


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


def reviews_for_items(
    db: Session, pairs: Sequence[tuple[str, str]]
) -> dict[tuple[str, str], list[ContentReviewRow]]:
    """`reviews_for` for many (item id, content hash) pairs in a few queries, not one each. Every
    pair is a key of the result (an empty list when nobody has reviewed it)."""
    out: dict[tuple[str, str], list[ContentReviewRow]] = {pair: [] for pair in pairs}
    ids = sorted({item_id for item_id, _ in pairs})
    for start in range(0, len(ids), 500):
        rows = db.scalars(
            select(ContentReviewRow)
            .where(ContentReviewRow.item_id.in_(ids[start : start + 500]))
            .order_by(ContentReviewRow.created_at, ContentReviewRow.id)
        )
        for row in rows:
            bucket = out.get((row.item_id, row.content_hash))
            if bucket is not None:
                bucket.append(row)
    return out


def standing(rows: Sequence[ContentReviewRow]) -> dict[uuid.UUID, ContentReviewRow]:
    """Each reviewer's current decision: their latest row (rows come oldest first) that is not a
    skip. A skip is kept in the history but does not stand in for, or withdraw, a decision. A
    `withdraw` row removes the reviewer's standing decision (the rows before it stay in the
    history): until they decide again they count as an approval or a block for nobody."""
    current: dict[uuid.UUID, ContentReviewRow] = {}
    for row in rows:
        if row.decision == "skip":
            continue
        if row.decision == "withdraw":
            current.pop(row.reviewer_id, None)
        else:
            current[row.reviewer_id] = row
    return current


def changed_after_seeing(rows: Sequence[ContentReviewRow]) -> set[uuid.UUID]:
    """Ids of the rows that are a reviewer's second (or later) real decision on this hash, made
    after they had already decided or withdrawn, so after they could have read the other
    reviewers' notes. Worked out from the history, so it needs no stored flag and cannot be
    skipped. A first decision, a skip, and a withdraw itself are never flagged."""
    seen: set[uuid.UUID] = set()
    flagged: set[uuid.UUID] = set()
    for row in rows:
        if row.decision == "skip":
            continue
        if row.decision != "withdraw" and row.reviewer_id in seen:
            flagged.add(row.id)
        seen.add(row.reviewer_id)
    return flagged


def tally(rows: list[ContentReviewRow]) -> Tally:
    current = standing(rows).values()
    return Tally(
        approvals=sum(1 for r in current if r.decision == "approve"),
        blocked=any(r.decision in ("reject", "fix") for r in current),
    )


@dataclass(frozen=True)
class FieldError:
    field: str
    message: str


def _enough(text: str | None) -> bool:
    return len(re.sub(r"\s", "", text or "")) >= MIN_NOTE_CHARS


def check_desk_decision(
    *,
    decision: str,
    severity: str | None,
    reason_code: str | None,
    checks: Sequence[bool | None] | None,
    fix_notes: Sequence[tuple[int, str]],
    note: str | None,
) -> list[FieldError]:
    """The reviewer desk's rules for one decision. An empty list means it may be recorded.

    fix / reject: a severity, a reason code, and every question marked "needs a fix" carries a fix
    note of at least 8 non-space characters; with no question marked, the general note must have
    them. approve: all three answers yes, nothing else attached. skip: no unfinished required note.
    """
    errors: list[FieldError] = []
    marked = [i for i, c in enumerate(checks or ()) if c is False]
    written = {i: text for i, text in fix_notes}
    for index in written:
        if not 0 <= index < CHECK_COUNT:
            errors.append(FieldError("fix_notes", f"question {index + 1} does not exist"))
        elif index not in marked:
            errors.append(
                FieldError("fix_notes", f"question {index + 1} is not marked as needing a fix")
            )
    unfinished = [i for i in marked if not _enough(written.get(i))]
    if decision == "approve":
        if checks is None or len(checks) != CHECK_COUNT or any(c is not True for c in checks):
            errors.append(FieldError("checks", "to approve, answer yes to all three questions"))
        if severity is not None:
            errors.append(FieldError("severity", "an approval has no severity"))
        if reason_code is not None:
            errors.append(FieldError("reason_code", "an approval has no reason"))
        return errors
    if decision == "withdraw":
        if severity is not None or reason_code is not None or checks is not None or fix_notes:
            errors.append(FieldError("severity", "a withdraw carries no severity or answers"))
        return errors
    if decision == "skip":
        if severity is not None or reason_code is not None:
            errors.append(FieldError("severity", "a skip has no severity or reason"))
        for i in unfinished:
            errors.append(FieldError("fix_notes", f"question {i + 1}: finish what to fix first"))
        return errors
    # fix or reject
    if severity is None:
        errors.append(FieldError("severity", "pick how serious it is"))
    if reason_code is None:
        errors.append(FieldError("reason_code", "pick the main reason (1 to 6)"))
    if marked:
        for i in unfinished:
            errors.append(
                FieldError(
                    "fix_notes",
                    f"question {i + 1}: say what to fix (at least {MIN_NOTE_CHARS} characters)",
                )
            )
    elif not _enough(note):
        errors.append(
            FieldError(
                "note",
                "mark the question that needs a fix and say what to change, "
                f"or write at least {MIN_NOTE_CHARS} characters in the note",
            )
        )
    return errors


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
    severity: str | None = None,
    reason_code: str | None = None,
    checks: list[bool | None] | None = None,
    fix_notes: list[dict[str, Any]] | None = None,
    active_seconds: int | None = None,
) -> ContentReviewRow:
    """Desk off: insert, or replace this reviewer's earlier decision on the same hash.
    Desk on: always insert a new row; the earlier rows stay as history."""
    row = None
    if not desk_enabled():
        row = db.scalars(
            select(ContentReviewRow)
            .where(
                ContentReviewRow.item_id == item_id,
                ContentReviewRow.content_hash == content_hash,
                ContentReviewRow.reviewer_id == reviewer_id,
            )
            .order_by(ContentReviewRow.created_at.desc(), ContentReviewRow.id.desc())
        ).first()
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
    if desk_enabled():
        row.severity = severity
        row.reason_code = reason_code
        row.checks = checks
        row.fix_notes = fix_notes
        row.active_seconds = active_seconds
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


_CACHE_MAX_ROOTS = 2  # the live content folder; a second only so a test or a swap does not thrash
_cache: dict[str, tuple[str, snapshot.ReviewData]] = {}
_raw_cache: dict[str, tuple[tuple[int, int], dict[str, Any]]] = {}
_snapshot_cache: dict[str, tuple[tuple[int, int], snapshot.ReviewData]] = {}
_match_cache: dict[str, tuple[str, str, bool]] = {}
_cache_lock = threading.Lock()


def clear_items_cache() -> None:
    with _cache_lock:
        _cache.clear()
        _raw_cache.clear()
        _snapshot_cache.clear()
        _match_cache.clear()


def _content_signature(root: Path) -> str:
    """A cheap fingerprint of every YAML file under the content folder: path, size and mtime.
    Any edit, add, delete or rename changes it. Reading the files is what is slow, not this."""
    digest = hashlib.sha256()
    entries: list[str] = []
    for folder, _dirs, files in os.walk(root):
        for name in files:
            if name.endswith((".yaml", ".yml")):
                path = os.path.join(folder, name)
                try:
                    info = os.stat(path)
                except OSError:
                    continue
                entries.append(f"{path}|{info.st_size}|{info.st_mtime_ns}")
    for entry in sorted(entries):
        digest.update(entry.encode("utf-8", "surrogatepass"))
        digest.update(b"|")
    return digest.hexdigest()


def _snapshot_file() -> Path:
    override = settings.review_snapshot_path.strip()
    return Path(override) if override else snapshot.SNAPSHOT_PATH


def _load_snapshot() -> tuple[dict[str, Any], Path, tuple[int, int]] | None:
    """The build-time snapshot file as plain data, with its path and stamp. None when there is no
    usable one. Cheap (decompress and parse); validating the items is `_snapshot_data`."""
    path = _snapshot_file()
    try:
        info = path.stat()
    except OSError:
        return None
    stamp = (info.st_size, info.st_mtime_ns)
    hit = _raw_cache.get(str(path))
    if hit is not None and hit[0] == stamp:
        return hit[1], path, stamp
    data = snapshot.read(path)
    if data is None:
        return None
    _raw_cache.clear()
    _raw_cache[str(path)] = (stamp, data)
    return data, path, stamp


def _snapshot_data(data: dict[str, Any], path: Path, stamp: tuple[int, int]) -> snapshot.ReviewData:
    hit = _snapshot_cache.get(str(path))
    if hit is not None and hit[0] == stamp:
        return hit[1]
    loaded = snapshot.to_review_data(data)
    _snapshot_cache.clear()
    _snapshot_cache[str(path)] = (stamp, loaded)
    return loaded


def _snapshot_matches(root: Path, recorded: str) -> bool:
    """Does the content folder still hash to what the snapshot was built from? The content hash
    reads every file, so the answer is kept per process while the stat fingerprint is unchanged."""
    stat_sig = _content_signature(root)
    hit = _match_cache.get(str(root))
    if hit is not None and hit[0] == stat_sig and hit[1] == recorded:
        return hit[2]
    matches = snapshot.source_signature(root) == recorded
    _match_cache[str(root)] = (stat_sig, recorded, matches)
    return matches


def load_review_data(root: Path) -> snapshot.ReviewData:
    """Items, misconception titles, Hindi strings and chapters for the review routes.

    Rule for choosing the source: with the reviewer desk on, the build-time snapshot (`snapshot.py`)
    when it exists and either
    the content folder is absent (a deployed function without `content/`: the snapshot is then
    authoritative) or the folder's content signature equals the one recorded in the snapshot;
    otherwise parse the YAML (kept per process while the files are unchanged, see
    `_content_signature`). Reads only: `validate_path` would rewrite stale files. Treat the
    returned items as read-only."""
    with _cache_lock:
        snap = (
            _load_snapshot()
            if settings.reviewer_desk_enabled and settings.review_snapshot_enabled
            else None
        )
        if snap is not None and (
            not root.exists() or _snapshot_matches(root, str(snap[0]["source_signature"]))
        ):
            return _snapshot_data(*snap)
        key = str(root)
        signature = _content_signature(root)
        hit = _cache.get(key)
        if hit is not None and hit[0] == signature:
            return hit[1]
        bundle = load_bundle(root)
        labels = {m.id: m.title.en for m in bundle.misconceptions}
        items = sorted(bundle.items, key=lambda i: i.id)
        data = snapshot.from_bundle(root, items, labels, list(bundle.overlays))
        _cache.pop(key, None)
        while len(_cache) >= _CACHE_MAX_ROOTS:
            _cache.pop(next(iter(_cache)))
        _cache[key] = (signature, data)
    return data


def load_items(root: Path) -> tuple[list[Item], dict[str, str]]:
    """Items in id order and misconception id to English title (see `load_review_data`)."""
    data = load_review_data(root)
    return list(data.items), data.labels


def has_decided(rows: Sequence[ContentReviewRow], me: uuid.UUID) -> bool:
    return me in standing(rows)


def list_state(rows: Sequence[ContentReviewRow], me: uuid.UUID) -> str:
    """pending / ready / flagged for the list filter. With the desk on, an item this reviewer has
    not decided yet is always "pending": a filter must not tell them how others voted."""
    if desk_enabled() and not has_decided(rows, me):
        return "pending"
    counted = tally(list(rows))
    return "flagged" if counted.blocked else "ready" if counted.ready else "pending"


def pseudonyms(rows: Sequence[ContentReviewRow], me: uuid.UUID) -> dict[uuid.UUID, str]:
    """ "Reviewer 1", "Reviewer 2" for the other reviewers on this card, in the order they first
    decided. Stable: a later reviewer never renumbers an earlier one."""
    order: list[uuid.UUID] = []
    for row in rows:
        if (
            row.decision not in ("skip", "withdraw")
            and row.reviewer_id != me
            and row.reviewer_id not in order
        ):
            order.append(row.reviewer_id)
    return {rid: f"Reviewer {n}" for n, rid in enumerate(order, start=1)}


def _desk_fields(row: ContentReviewRow) -> dict[str, Any]:
    return {
        "severity": row.severity,
        "reason_code": row.reason_code,
        "checks": row.checks,
        "fix_notes": row.fix_notes or [],
    }


def _review_view(rows: list[ContentReviewRow], me: uuid.UUID) -> dict[str, Any]:
    """The review fields of a card. Desk off: exactly the original shape. Desk on: blind until
    `me` has a standing decision, then the others by pseudonym only."""
    counted = tally(rows)
    current = standing(rows)
    mine = current.get(me)
    if not desk_enabled():
        mine = next((r for r in rows if r.reviewer_id == me), None)
        return {
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
    mine_rows = [r for r in rows if r.reviewer_id == me]
    late = changed_after_seeing(rows)
    view: dict[str, Any] = {
        "approvals_needed": REQUIRED_APPROVALS,
        "my_decision": (
            {"decision": mine.decision, "note": mine.note, **_desk_fields(mine)}
            if mine is not None
            else None
        ),
        "my_history": [
            {
                "decision": r.decision,
                "severity": r.severity,
                "created_at": r.created_at.isoformat(),
                "changed_after_seeing": r.id in late,
            }
            for r in mine_rows
        ],
    }
    if mine is None:
        view.update(approvals=None, blocked=None, notes=[], others=[])
        return view
    names = pseudonyms(rows, me)
    others = [
        {
            "reviewer": names[r.reviewer_id],
            "decision": r.decision,
            "note": r.note,
            **_desk_fields(r),
        }
        for r in current.values()
        if r.reviewer_id != me
    ]
    others.sort(key=lambda o: o["reviewer"])
    view.update(
        approvals=counted.approvals,
        blocked=counted.blocked,
        notes=[
            {"reviewer": o["reviewer"], "decision": o["decision"], "note": o["note"]}
            for o in others
            if o["note"]
        ],
        others=others,
    )
    return view


def card(
    db: Session,
    root: Path,
    item: Item,
    labels: dict[str, str],
    me: uuid.UUID,
    hindi: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One review card. `hindi` is the item's Hindi strings when they are already known (from the
    snapshot); without it they are read from the item's YAML file."""
    digest = item_content_hash(item)
    rows = reviews_for(db, item.id, digest)
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
        "hindi": hindi if hindi is not None else hindi_texts(root, item.id),
        **_review_view(rows, me),
    }


def is_draft(item: Item) -> bool:
    return item.status == ContentStatus.draft


# ---- reviewer accounts (desk on) ----


def invite_reviewer(db: Session, email: str, now: datetime) -> UserRow:
    """Create an invited `reviewer` account. Never changes the role of an account that exists."""
    address = email.strip().lower()
    user = db.scalar(select(UserRow).where(UserRow.email == address))
    if user is None:
        user = UserRow(id=uuid.uuid4(), role="reviewer", email=address, locale="en", created_at=now)
        db.add(user)
        db.flush()
    return user


def set_reviewer_suspended(
    db: Session, reviewer_id: uuid.UUID, suspended: bool, now: datetime
) -> UserRow | None:
    user = db.get(UserRow, reviewer_id)
    if user is None or user.role != "reviewer":
        return None
    user.suspended_at = now if suspended else None
    db.flush()
    return user


class SignInCodeRefused(Exception):  # noqa: N818
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


SIGNIN_CODES_PER_HOUR = 5


def issue_reviewer_signin_code(
    db: Session, reviewer_id: uuid.UUID, admin_id: uuid.UUID
) -> tuple[str, datetime] | None:
    """An admin hands a reviewer a one-time sign-in code (no email). None: not a reviewer account.
    Raises SignInCodeRefused for a suspended reviewer (409) or more than five codes in an hour
    (429). The audit row keeps who, for whom and when, never the code."""
    user = db.get(UserRow, reviewer_id)
    if user is None or user.role != "reviewer" or user.email is None:
        return None
    if user.suspended_at is not None:
        raise SignInCodeRefused(409, "that reviewer is suspended")
    now = now_utc()
    recent = db.scalar(
        select(func.count(ReviewerCodeIssueRow.id)).where(
            ReviewerCodeIssueRow.reviewer_id == reviewer_id,
            ReviewerCodeIssueRow.issued_at > now - timedelta(hours=1),
        )
    )
    if (recent or 0) >= SIGNIN_CODES_PER_HOUR:
        raise SignInCodeRefused(429, "too many codes for this reviewer; try again later")
    code, expires = issue_signin_code(db, user.email, settings.reviewer_signin_code_ttl_seconds)
    db.add(
        ReviewerCodeIssueRow(
            id=uuid.uuid4(),
            reviewer_id=reviewer_id,
            issued_by=admin_id,
            issued_at=now,
            expires_at=expires,
        )
    )
    db.flush()
    return code, expires


# ---- pay statement export (read-only, no learner data) ----


def reviewer_label(reviewer_id: uuid.UUID) -> str:
    """A pseudonymous label that is the same on every statement, and is not an email address."""
    return "R-" + hashlib.sha256(reviewer_id.bytes).hexdigest()[:8]


def reviewer_export(db: Session, start: date, end: date) -> list[dict[str, Any]]:
    """Per reviewer, for decisions made from `start` to `end` (both days included, UTC): how many
    of each decision and the total active seconds. Ids and pseudonymous labels only."""
    lo = datetime.combine(start, time.min, tzinfo=UTC)
    hi = datetime.combine(end + timedelta(days=1), time.min, tzinfo=UTC)
    rows = list(
        db.scalars(
            select(ContentReviewRow).where(
                ContentReviewRow.created_at >= lo, ContentReviewRow.created_at < hi
            )
        )
    )
    # "late" is judged on the whole history of each item and hash, not only on this date range
    late = _late_row_ids(db, {(r.item_id, r.content_hash) for r in rows})
    out: dict[uuid.UUID, dict[str, Any]] = {}
    for row in rows:
        entry = out.setdefault(
            row.reviewer_id,
            {
                "reviewer_id": str(row.reviewer_id),
                "label": reviewer_label(row.reviewer_id),
                "decisions": {"approve": 0, "fix": 0, "reject": 0, "skip": 0, "withdraw": 0},
                "changed_after_seeing": 0,
                "active_seconds": 0,
            },
        )
        entry["decisions"][row.decision] = entry["decisions"].get(row.decision, 0) + 1
        entry["active_seconds"] += row.active_seconds or 0
        if row.id in late:
            entry["changed_after_seeing"] += 1
    return sorted(out.values(), key=lambda e: e["label"])


def _late_row_ids(db: Session, pairs: set[tuple[str, str]]) -> set[uuid.UUID]:
    late: set[uuid.UUID] = set()
    for history in reviews_for_items(db, sorted(pairs)).values():
        late |= changed_after_seeing(history)
    return late


# ---- reviewer list and time today (desk on) ----


def list_reviewers(db: Session) -> list[dict[str, Any]]:
    """Every invited `reviewer` account with its decision count and last decision time. Account
    and activity facts only: no learner data, and nothing about how anyone voted."""
    users = list(
        db.scalars(select(UserRow).where(UserRow.role == "reviewer").order_by(UserRow.created_at))
    )
    stats = {
        rid: (count, last)
        for rid, count, last in db.execute(
            select(
                ContentReviewRow.reviewer_id,
                func.count(ContentReviewRow.id),
                func.max(ContentReviewRow.created_at),
            ).group_by(ContentReviewRow.reviewer_id)
        )
    }
    out = []
    for user in users:
        count, last = stats.get(user.id, (0, None))
        out.append(
            {
                "id": str(user.id),
                "email": user.email,
                "suspended": user.suspended_at is not None,
                "invited_at": user.created_at.isoformat(),
                "last_decision_at": last.isoformat() if last is not None else None,
                "decision_count": count,
            }
        )
    return out


def seconds_today(db: Session, reviewer_id: uuid.UUID, now: datetime) -> int:
    """The caller's total active seconds on decisions made today (UTC)."""
    lo = datetime.combine(now.astimezone(UTC).date(), time.min, tzinfo=UTC)
    total = db.scalar(
        select(func.coalesce(func.sum(ContentReviewRow.active_seconds), 0)).where(
            ContentReviewRow.reviewer_id == reviewer_id,
            ContentReviewRow.created_at >= lo,
            ContentReviewRow.created_at < lo + timedelta(days=1),
        )
    )
    return int(total or 0)


# ---- class / subject / chapter groups (desk on) ----


def in_group(
    data: snapshot.ReviewData,
    item: Item,
    grade: int | None,
    subject: str | None,
    chapter: str | None,
) -> bool:
    """Does the item belong to the asked class, subject and chapter? Unset filters match all."""
    chapter_id = data.item_chapter.get(item.id, snapshot.UNMAPPED_ID)
    found = data.chapters.get(chapter_id)
    if chapter is not None and chapter_id != chapter:
        return False
    if grade is not None and (found is None or found.grade != grade):
        return False
    return subject is None or (found is not None and found.subject == subject)


def chapter_groups(
    db: Session, data: snapshot.ReviewData, me: uuid.UUID
) -> tuple[list[dict[str, Any]], list[str]]:
    """The class / subject / chapter groups that have draft items, with the item count and how
    many are still pending for `me` (the same rule as the list filter, so a count never shows how
    others voted on an item `me` has not decided). Also the chapter ids with no curriculum entry
    (their metadata comes from the overlay), including the `unmapped` group if an item has no
    chapter at all."""
    drafts = [item for item in data.items if is_draft(item)]
    pairs = {item.id: (item.id, item_content_hash(item)) for item in drafts}
    reviews = reviews_for_items(db, list(pairs.values()))
    totals: dict[str, list[int]] = {}
    for item in drafts:
        chapter_id = data.item_chapter.get(item.id, snapshot.UNMAPPED_ID)
        entry = totals.setdefault(chapter_id, [0, 0])
        entry[0] += 1
        if list_state(reviews[pairs[item.id]], me) == "pending":
            entry[1] += 1
    groups = []
    gaps = []
    for chapter_id, (total, pending) in totals.items():
        chapter = data.chapters.get(chapter_id) or snapshot.Chapter(
            chapter_id, None, None, chapter_id, False
        )
        if not chapter.in_curriculum:
            gaps.append(chapter_id)
        groups.append(
            {
                "class": chapter.grade,
                "subject": chapter.subject,
                "chapter": chapter_id,
                "title": chapter.title,
                "in_curriculum": chapter.in_curriculum,
                "total": total,
                "pending": pending,
            }
        )
    groups.sort(
        key=lambda g: (
            g["class"] is None,
            g["class"] or 0,
            g["subject"] or "",
            g["title"],
            g["chapter"],
        )
    )
    return groups, sorted(gaps)


# ---- pay statement (admin only, read-only) ----

PAID_DECISIONS = ("approve", "fix", "reject")


def _new_tally() -> dict[str, Any]:
    return {
        "decisions": {"approve": 0, "fix": 0, "reject": 0},
        "in_range": 0,
        "in_month": 0,
        "prior_in_month": 0,
        "active_seconds": 0,
        "changed_after_seeing": 0,
    }


def pay_statement(
    db: Session,
    start: date,
    end: date,
    *,
    rate: Decimal,
    monthly_cap: Decimal,
) -> dict[str, Any]:
    """Per reviewer, what to pay for decisions made from `start` to `end` (both included, UTC).

    Paid decision: a reviewer's STANDING decision (see `standing`) on an item and content hash,
    when that decision is approve, fix or reject. A skip or a withdraw is never paid. It is counted
    once per reviewer, item and hash, however often they withdrew and decided again, and it is dated
    by the first approve, fix or reject they recorded on that item and hash (so changing your mind
    next month does not pay again; the by-type breakdown shows the decision that stands now). A
    withdrawn decision that was not made again is not paid.

    amount = paid decisions x rate. The monthly cap applies to the calendar month of `end`: the
    decisions dated in that month (from `max(start, first of month)`) are paid at most
    `monthly_cap` together with the decisions dated earlier in the same month that fall before
    `start` (so a statement for 1-15 and then one for 16-30 never pays past the cap). Decisions in
    an earlier month of the range are not capped. `cap_applied` is set when the cap reduced the
    amount. `active_seconds` is the sum over every decision row in the range (a skip's time counts).

    No quality multiplier yet: planted checks are not built, so nobody's pay depends on a score."""
    month_start = end.replace(day=1)
    lo = datetime.combine(min(start, month_start), time.min, tzinfo=UTC)
    hi = datetime.combine(end + timedelta(days=1), time.min, tzinfo=UTC)
    range_lo = datetime.combine(start, time.min, tzinfo=UTC)
    month_lo = datetime.combine(month_start, time.min, tzinfo=UTC)
    # the whole history of every (item, hash) touched in the window, to find standing decisions
    touched = {
        (r.item_id, r.content_hash)
        for r in db.scalars(
            select(ContentReviewRow).where(
                ContentReviewRow.created_at >= lo, ContentReviewRow.created_at < hi
            )
        )
    }
    per: dict[uuid.UUID, dict[str, Any]] = {}
    for history in reviews_for_items(db, sorted(touched)).values():
        late = changed_after_seeing(history)
        for row in history:
            if range_lo <= row.created_at.astimezone(UTC) < hi:
                bucket = per.setdefault(row.reviewer_id, _new_tally())
                bucket["active_seconds"] += row.active_seconds or 0
                if row.id in late:
                    bucket["changed_after_seeing"] += 1
        for reviewer_id, row in standing(history).items():
            if row.decision not in PAID_DECISIONS:
                continue
            first = next(
                r for r in history if r.reviewer_id == reviewer_id and r.decision in PAID_DECISIONS
            )
            when = first.created_at.astimezone(UTC)
            if not lo <= when < hi:
                continue
            bucket = per.setdefault(reviewer_id, _new_tally())
            if when >= range_lo:
                bucket["in_range"] += 1
                bucket["decisions"][row.decision] += 1
                if when >= month_lo:
                    bucket["in_month"] += 1
            elif when >= month_lo:
                bucket["prior_in_month"] += 1
    users = {
        u.id: u
        for u in db.scalars(select(UserRow).where(UserRow.id.in_(list(per) or [uuid.UUID(int=0)])))
    }
    reviewers = []
    for reviewer_id, b in per.items():
        if b["in_range"] == 0 and b["active_seconds"] == 0 and b["changed_after_seeing"] == 0:
            continue
        before_cap = rate * b["in_range"]
        room = max(Decimal(0), monthly_cap - rate * b["prior_in_month"])
        amount = rate * (b["in_range"] - b["in_month"]) + min(rate * b["in_month"], room)
        user = users.get(reviewer_id)
        reviewers.append(
            {
                "reviewer_id": str(reviewer_id),
                "label": reviewer_label(reviewer_id),
                "email": user.email if user is not None else None,
                "paid_decisions": b["in_range"],
                "decisions": b["decisions"],
                "active_seconds": b["active_seconds"],
                "changed_after_seeing": b["changed_after_seeing"],
                "rate_inr": float(rate),
                "amount_before_cap_inr": float(before_cap),
                "amount_inr": float(amount),
                "cap_applied": amount < before_cap,
            }
        )
    reviewers.sort(key=lambda r: r["label"])
    return {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "rate_inr": float(rate),
        "monthly_cap_inr": float(monthly_cap),
        "cap_month": month_start.strftime("%Y-%m"),
        "quality_multiplier": None,
        "reviewers": reviewers,
        "total_paid_decisions": sum(r["paid_decisions"] for r in reviewers),
        "total_amount_inr": float(sum(Decimal(str(r["amount_inr"])) for r in reviewers)),
    }
