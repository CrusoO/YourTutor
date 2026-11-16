"""Switch an item off (telemetry, an audit finding or a person) and back on.

`suspended_at` makes the gate refuse the item whatever its tier or status. The event goes in the
hash-chained ledger so it survives a content reload (the loader re-applies ledger suspensions).
Un-suspending needs a person or a re-certification: it is never automatic.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.content.ledger import Ledger
from app.db.models import ItemRow


def suspend_item(session: Session, item_id: str, reason: str, ledger: Ledger | None = None) -> bool:
    row = session.get(ItemRow, item_id)
    if row is None:
        return False
    now = datetime.now(UTC)
    row.suspended_at = now
    row.suspension_reason = reason[:200]
    if ledger is not None:
        ledger.append(
            "suspended",
            item_id,
            row.content_hash or "",
            {"reason": reason[:200]},
            ts=now.isoformat(),
        )
    session.flush()
    return True


def unsuspend_item(
    session: Session, item_id: str, reason: str, ledger: Ledger | None = None
) -> bool:
    row = session.get(ItemRow, item_id)
    if row is None or row.suspended_at is None:
        return False
    row.suspended_at = None
    row.suspension_reason = None
    if ledger is not None:
        ledger.append(
            "unsuspended",
            item_id,
            row.content_hash or "",
            {"reason": reason[:200]},
            ts=datetime.now(UTC).isoformat(),
        )
    session.flush()
    return True
